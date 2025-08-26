import logging
import time
from threading import Thread, Condition
import multiprocessing as mp
from typing import Optional, Callable

from multimodalsim.optimization.state import State
from multimodalsim.simulator.event import ActionEvent, TimeSyncEvent
import multimodalsim.simulator.vehicle as vehicle_module

import multimodalsim.simulator.request as request
import \
    multimodalsim.simulator.passenger_event as passenger_event_process
import multimodalsim.simulator.vehicle_event as vehicle_event_process
from multimodalsim.state_machine.status import OptimizationStatus
import multimodalsim.simulator.event_queue as event_queue
import multimodalsim.simulator.environment as environment
import multimodalsim.optimization.optimization as optimization_module

logger = logging.getLogger(__name__)


class Optimize(ActionEvent):
    def __init__(self, time: float, queue: 'event_queue.EventQueue',
                 multiple_optimize_events: Optional[bool] = None,
                 batch: Optional[float] = None,
                 max_optimization_time: Optional[float] = None,
                 asynchronous: Optional[bool] = None) -> None:

        self.__load_parameters_from_config(queue.env.optimization,
                                           multiple_optimize_events, batch,
                                           max_optimization_time, asynchronous)

        if self.__batch is not None:
            # Round to the smallest integer greater than or equal to time that
            # is also a multiple of batch.
            time = time + (batch - (time % batch)) % batch
        super().__init__('Optimize', queue, time,
                         event_priority=self.VERY_LOW_PRIORITY,
                         state_machine=queue.env.optimization.state_machine)

    def process(self, env: 'environment.Environment') -> str:

        if self.state_machine.current_state.status \
                == OptimizationStatus.OPTIMIZING:
            with env.optimize_cv:
                env.optimize_cv.wait()
            self.add_to_queue()
            process_message = 'Optimize process is put back in the event queue'
        else:
            process_message = super().process(env)

        return process_message

    def _process(self, env: 'environment.Environment') -> str:

        stats_extractor = env.optimization.environment_statistics_extractor
        env_stats = stats_extractor.extract_environment_statistics(env)

        if env.optimization.need_to_optimize(env_stats):
            env.optimize_cv = Condition()

            env.optimization.state = env.get_new_state()

            if self.__asynchronous:
                self.__optimize_asynchronously(env)
            else:
                self.__optimize_synchronously(env)
        else:
            optimization_result = optimization_module.OptimizationResult()
            EnvironmentUpdate(optimization_result, self.queue).add_to_queue()

        return 'Optimize process is implemented'

    def add_to_queue(self) -> None:

        if self.__multiple_optimize_events or not \
                self.queue.is_event_type_in_queue(self.__class__, self.time):
            super().add_to_queue()

    def __optimize_synchronously(self, env):
        env.optimization.state.freeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        optimization_result = env.optimization.dispatch(
            env.optimization.state)

        env.optimization.state.unfreeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        EnvironmentUpdate(optimization_result, self.queue).add_to_queue()

    def __optimize_asynchronously(self, env):
        hold_cv = Condition()

        hold_event = Hold(self.queue, env.current_time
                          + env.optimization.freeze_interval, hold_cv,
                          self.__max_optimization_time)
        hold_event.add_to_queue()

        optimize_thread = Thread(target=self.__optimize_in_new_thread,
                                 args=(env, hold_cv, hold_event))
        optimize_thread.start()

    def __optimize_in_new_thread(self, env, hold_cv, hold_event):

        env.optimization.state.freeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        with mp.Manager() as manager:
            process_dict = self.__create_process_dict(env, manager)

            opt_process = self.__create_optimize_process(process_dict,
                                                         hold_event)
            opt_process.start()
            opt_process.join()

            self.__create_environment_update(process_dict, hold_event)

        env.optimization.state.unfreeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        with env.optimize_cv:
            env.optimize_cv.notify()

    def __create_process_dict(self, env, manager):

        process_dict = manager.dict()
        process_dict["state"] = env.optimization.state
        process_dict["dispatch_function"] = env.optimization.dispatch
        process_dict["optimization_result"] = None

        return process_dict

    def __create_optimize_process(self, process_dict, hold_event):
        opt_process = DispatchProcess(dispatch=Optimize.dispatch,
                                      process_dict=process_dict)
        with hold_event.cv:
            hold_event.optimization_process = opt_process

        return opt_process

    def __create_environment_update(self, process_dict, hold_event):
        with hold_event.cv:
            hold_event.cancelled = True
            optimization_result = process_dict["optimization_result"]
            EnvironmentUpdate(optimization_result,
                              self.queue).add_to_queue()
            hold_event.cv.notify()

    @staticmethod
    def dispatch(dispatch_function: Callable,
                 state: State) -> 'optimization_module.OptimizationResult':
        optimization_result = dispatch_function(state)

        return optimization_result

    def __load_parameters_from_config(self, optimization,
                                      multiple_optimize_events, batch,
                                      max_optimization_time, asynchronous):

        config = optimization.config

        self.__multiple_optimize_events = config.multiple_optimize_events \
            if multiple_optimize_events is None else multiple_optimize_events
        self.__batch = config.batch if batch is None else config.batch

        self.__asynchronous = config.asynchronous \
            if asynchronous is None else asynchronous

        max_optimization_time = config.max_optimization_time \
            if max_optimization_time is None else max_optimization_time
        self.__max_optimization_time = optimization.freeze_interval \
            if max_optimization_time is None else max_optimization_time


class EnvironmentUpdate(ActionEvent):
    def __init__(self,
                 optimization_result: 'optimization_module.OptimizationResult',
                 queue: 'event_queue.EventQueue') -> None:
        super().__init__('EnvironmentUpdate', queue,
                         state_machine=queue.env.optimization.state_machine)
        self.__optimization_result = optimization_result

    def _process(self, env: 'environment.Environment') -> str:

        self.__env = env

        self.__process_new_requests()

        self.__process_new_vehicles()

        self.__process_modified_requests()

        self.__process_modified_vehicles()

        EnvironmentIdle(self.queue).add_to_queue()

        return 'Environment Update process is implemented'

    def __process_new_requests(self) -> None:
        for trip in self.__optimization_result.new_requests:
            PassengerRelease(trip, self.queue).add_to_queue()

    def __process_new_vehicles(self) -> None:
        for vehicle in self.__optimization_result.new_vehicles:
            if vehicle.id \
                    in self.__optimization_result.state.route_by_vehicle_id:
                route = self.__optimization_result.state.route_by_vehicle_id[
                    vehicle.id]
            else:
                route = None

            route = self.__optimization_result.state.route_by_vehicle_id[
                vehicle.id]
            if route.current_stop is not None:
                # Copy passengers_to_board and departure time of current_stop.
                current_stop_modified_passengers_to_board = \
                    route.current_stop.passengers_to_board
                current_stop_departure_time = \
                    route.current_stop.departure_time
            else:
                current_stop_modified_passengers_to_board = None
                current_stop_departure_time = None

            next_stops = route.next_stops
            route_update = vehicle_module.RouteUpdate(
                vehicle.id, current_stop_modified_passengers_to_board,
                next_stops, current_stop_departure_time, route.assigned_legs)
            vehicle_event_process.VehicleReady(
                vehicle, route, self.queue,
                self.__env.simulation_config.update_position_time_step,
                route_update
            ).add_to_queue()


    def __process_modified_requests(self):

        for trip in self.__optimization_result.modified_requests:

            actual_trip = self.__env.get_trip_by_id(trip.id)

            next_leg_assigned_vehicle = trip.next_legs[0].assigned_vehicle
            actual_next_leg_assigned_vehicle = \
                actual_trip.next_legs[0].assigned_vehicle

            if next_leg_assigned_vehicle is None \
                    and actual_next_leg_assigned_vehicle is not None:
                # Unassign previously assigned passenger
                passenger_event_process.PassengerUnassignment(
                    actual_trip, self.queue).add_to_queue()
            else:
                assigned_vehicle_id = next_leg_assigned_vehicle.id \
                    if next_leg_assigned_vehicle is not None else None
                passenger_update = request.PassengerUpdate(
                    trip.id, assigned_vehicle_id, trip.current_leg,
                    trip.next_legs)
                passenger_event_process.PassengerAssignment(
                    trip.id, self.queue, passenger_update).add_to_queue()

    def __process_modified_vehicles(self):
        for veh in self.__optimization_result.modified_vehicles:
            route = \
                self.__optimization_result.state.route_by_vehicle_id[veh.id]
            if route.current_stop is not None:
                # Copy passengers_to_board and departure time of current_stop.
                current_stop_modified_passengers_to_board = \
                    route.current_stop.passengers_to_board
                current_stop_departure_time = \
                    route.current_stop.departure_time
            else:
                current_stop_modified_passengers_to_board = None
                current_stop_departure_time = None

            next_stops = route.next_stops
            route_update = vehicle_module.RouteUpdate(
                veh.id, current_stop_modified_passengers_to_board, next_stops,
                current_stop_departure_time, route.assigned_legs)
            vehicle_event_process.VehicleNotification(
                route_update, self.queue).add_to_queue()

class EnvironmentIdle(ActionEvent):
    def __init__(self, queue: 'event_queue.EventQueue'):
        super().__init__('EnvironmentIdle', queue,
                         state_machine=queue.env.optimization.state_machine)

    def _process(self, env: 'environment.Environment') -> str:
        return 'Environment Idle process is implemented'


class Hold(TimeSyncEvent):
    def __init__(self, queue: 'event_queue.EventQueue', event_time: float,
                 cv: Condition, max_optimization_time: float) -> None:
        super().__init__(queue, event_time,
                         max_waiting_time=max_optimization_time,
                         event_name='Hold')

        self.__cv = cv
        self.__max_optimization_time = max_optimization_time
        self.__timestamp = time.time()

        self.__optimization_process = None

        self.__termination_waiting_time = \
            queue.env.optimization.config.termination_waiting_time

    @property
    def cv(self) -> Condition:
        return self.__cv

    @property
    def optimization_process(self) -> 'DispatchProcess':
        return self.__optimization_process

    @optimization_process.setter
    def optimization_process(self, optimization_process: 'DispatchProcess'):
        self.__optimization_process = optimization_process

    def _synchronize(self) -> None:
        with self.__cv:
            if not self.cancelled:
                wait_return = self.__cv.wait(timeout=self._waiting_time)
                if not wait_return:
                    self.__terminate_process()

    def __terminate_process(self):
        if self.__optimization_process.is_alive():
            logger.warning("Terminate optimization process".format(
                self.__termination_waiting_time))
            self.__optimization_process.terminate()
            time.sleep(self.__termination_waiting_time)
            if self.__optimization_process.exitcode is None:
                self.__optimization_process.kill()
            raise RuntimeError("Optimization exceeded the time limit of {} "
                               "seconds.".format(self.__max_optimization_time))


class DispatchProcess(mp.Process):
    def __init__(self, dispatch: Callable, process_dict: dict) -> None:
        super().__init__()
        self.__dispatch = dispatch
        self.__process_dict = process_dict

    def run(self) -> None:
        state = self.__process_dict["state"]
        dispatch_function = self.__process_dict["dispatch_function"]

        optimization_result = self.__dispatch(dispatch_function, state)
        self.__process_dict["optimization_result"] = optimization_result
