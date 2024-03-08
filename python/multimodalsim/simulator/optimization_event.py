import logging
import time
from threading import Thread, Condition
import multiprocessing as mp

from multimodalsim.simulator.event import ActionEvent, Event, TimeSyncEvent
from multimodalsim.simulator.vehicle import RouteUpdate

import multimodalsim.simulator.request as request
import \
    multimodalsim.simulator.passenger_event as passenger_event_process
import multimodalsim.simulator.vehicle_event as vehicle_event_process
from multimodalsim.state_machine.status import OptimizationStatus

logger = logging.getLogger(__name__)


class Optimize(ActionEvent):
    def __init__(self, time, queue, multiple_optimize_events=None,
                 batch=None, max_optimization_time=None, asynchronous=None):

        self.__load_parameters_from_config(queue.env.optimization,
                                           multiple_optimize_events, batch,
                                           max_optimization_time, asynchronous)

        if self.__batch is not None:
            # Round to the smallest integer greater than or equal to time that
            # is also a multiple of batch.#
            time = time + (batch - (time % batch)) % batch
        super().__init__('Optimize', queue, time,
                         event_priority=self.VERY_LOW_PRIORITY,
                         state_machine=queue.env.optimization.state_machine)

    def process(self, env):

        if self.state_machine.current_state.status \
                == OptimizationStatus.OPTIMIZING:
            with env.optimize_cv:
                env.optimize_cv.wait()
            self.add_to_queue()
            process_message = 'Optimize process is put back in the event queue'
        else:
            process_message = super().process(env)

        return process_message

    def _process(self, env):

        env_stats = env.get_environment_statistics()

        if env.optimization.need_to_optimize(env_stats):
            env.optimize_cv = Condition()

            env.optimization.state = env.get_new_state()

            if self.__asynchronous:
                self.__optimize_asynchronously(env)
            else:
                self.__optimize_synchronously(env)

        return 'Optimize process is implemented'

    def add_to_queue(self):

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
    def dispatch(dispatch_function, state):
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
    def __init__(self, optimization_result, queue):
        super().__init__('EnvironmentUpdate', queue,
                         state_machine=queue.env.optimization.state_machine)
        self.__optimization_result = optimization_result

    def _process(self, env):

        for trip in self.__optimization_result.modified_requests:
            next_legs = trip.next_legs
            next_leg_assigned_vehicle = trip.next_legs[0].assigned_vehicle

            passenger_update = request.PassengerUpdate(
                next_leg_assigned_vehicle.id, trip.id, next_legs)
            passenger_event_process.PassengerAssignment(
                passenger_update, self.queue).add_to_queue()

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

            # Add the assigned_legs of route that were modified during
            # optimization.
            modified_trips_ids = [modified_trip.id for modified_trip in
                                  self.__optimization_result.modified_requests]
            modified_assigned_legs = [leg for leg in route.assigned_legs
                                      if leg.trip.id in modified_trips_ids]

            next_stops = route.next_stops
            route_update = RouteUpdate(
                veh.id, current_stop_modified_passengers_to_board, next_stops,
                current_stop_departure_time, modified_assigned_legs)
            vehicle_event_process.VehicleNotification(
                route_update, self.queue).add_to_queue()

        EnvironmentIdle(self.queue).add_to_queue()

        return 'Environment Update process is implemented'


class EnvironmentIdle(ActionEvent):
    def __init__(self, queue):
        super().__init__('EnvironmentIdle', queue,
                         state_machine=queue.env.optimization.state_machine)

    def _process(self, env):
        return 'Environment Idle process is implemented'


class Hold(TimeSyncEvent):
    def __init__(self, queue, event_time, cv, max_optimization_time):
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
    def cv(self):
        return self.__cv

    @property
    def optimization_process(self):
        return self.__optimization_process

    @optimization_process.setter
    def optimization_process(self, optimization_process):
        self.__optimization_process = optimization_process

    def _synchronize(self):
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
    def __init__(self, dispatch, process_dict):
        super().__init__()
        self.__dispatch = dispatch
        self.__process_dict = process_dict

    def run(self):
        state = self.__process_dict["state"]
        dispatch_function = self.__process_dict["dispatch_function"]

        optimization_result = self.__dispatch(dispatch_function, state)
        self.__process_dict["optimization_result"] = optimization_result
