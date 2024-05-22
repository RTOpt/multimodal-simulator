import logging
import time
from threading import Thread, Condition
import multiprocessing as mp

from multimodalsim.simulator.event import ActionEvent, Event
from multimodalsim.simulator.vehicle import RouteUpdate

import multimodalsim.simulator.request as request
import \
    multimodalsim.simulator.passenger_event as passenger_event_process
import multimodalsim.simulator.vehicle_event as vehicle_event_process
from multimodalsim.state_machine.status import OptimizationStatus

logger = logging.getLogger(__name__)


class Optimize(ActionEvent):
    def __init__(self, time, queue, multiple_optimize_events=None,
                 batch=None, max_optimization_time=None, asynchronous=None, bus=False, event_priority=Event.STANDARD_PRIORITY):
        self.__load_parameters_from_config(queue.env.optimization,
                                           multiple_optimize_events, batch,
                                           max_optimization_time, asynchronous)
        if self.__batch is not None:
            # Round to the smallest integer greater than or equal to time that
            # is also a multiple of batch.#
            time = time + (batch - (time % batch)) % batch
        self.__bus = bus
        super().__init__('Optimize', queue, time,
                         event_priority=event_priority,
                         state_machine=queue.env.optimization.state_machine)
        self.__bus = bus

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
        if self.bus:
            optimization_result = env.optimization.bus_dispatch(
                env.optimization.state, self.queue)
        else:
            optimization_result = env.optimization.dispatch(
                env.optimization.state)

        env.optimization.state.unfreeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        EnvironmentUpdate(optimization_result, self.queue, self.bus).add_to_queue()

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
    
    @property
    def bus(self):
        return self.__bus
    
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
    def __init__(self, optimization_result, queue, bus=False):
        super().__init__('EnvironmentUpdate', queue,
                         state_machine=queue.env.optimization.state_machine)
        self.__optimization_result = optimization_result
        self.__bus = bus

    def _process(self, env):
        if self.__bus:
            print('number of modified requests: ', len(self.__optimization_result.modified_requests))
            for trip in self.__optimization_result.modified_requests:
                env.update_trip(trip.id, trip)
            # if len(self.__optimization_result.modified_requests) > 0:
            #     for trip in env.trips:
            #         print(trip)
            #     input('environment updated trips. Press Enter to continue...')

        else: 
            for trip in self.__optimization_result.modified_requests:
                next_legs = trip.next_legs
                next_leg_assigned_vehicle_id = trip.next_legs[0].assigned_vehicle.id if trip.next_legs[0].assigned_vehicle is not None else None
                current_leg = trip.current_leg
                print('trip id is ASSIGNED: ', trip.id)
                # input('Press Enter to continue...')
                passenger_update = request.PassengerUpdate(
                    next_leg_assigned_vehicle_id, trip.id, next_legs, current_leg = current_leg)
                passenger_event_process.PassengerAssignment(
                    passenger_update, self.queue).add_to_queue()

        for veh in self.__optimization_result.modified_vehicles:
            print("Vehicle ID: ", veh.id)
            route = \
                self.__optimization_result.state.route_by_vehicle_id[veh.id]#optimized route
            if route.current_stop is not None:
                # Copy passengers_to_board and departure time of current_stop.
                current_stop_modified_passengers_to_board = \
                    route.current_stop.passengers_to_board
                print('current_stop_modified_passengers_to_board: ', [passenger.id for passenger in current_stop_modified_passengers_to_board])
                # input('Press Enter to continue...')
                current_stop_departure_time = \
                    route.current_stop.departure_time
            else:
                current_stop_modified_passengers_to_board = None
                current_stop_departure_time = None

            # Add the assigned_legs of route that were modified during
            # optimization.
            modified_trips_ids = [modified_trip.id for modified_trip in
                                  self.__optimization_result.modified_requests]
            # for trip in self.__optimization_result.modified_requests:
            #     if trip.next_legs is not None and len(trip.next_legs) > 0:
            #         if 'walk' in trip.next_legs[0].id:
            #             input('walk leg is in optimization_result.modified requests. Press Enter to continue...')
            modified_assigned_legs = [leg for leg in route.assigned_legs
                                      if leg.trip.id in modified_trips_ids]
            if self.__bus:
                modified_assigned_legs = list(set([leg for leg in route.assigned_legs + route.onboard_legs
                                          if leg.trip.id in modified_trips_ids]))
            print('modified_assigned_legs: ', [leg.id for leg in modified_assigned_legs])
            # for leg in modified_assigned_legs:
            #     if 'walk' in leg.id:
            #         input('walk leg is in modified_assigned_legs. Press Enter to continue...')

            next_stops = route.next_stops
            route_update = RouteUpdate(
                veh.id, current_stop_modified_passengers_to_board, next_stops,
                current_stop_departure_time, modified_assigned_legs)
            vehicle_event_process.VehicleNotification(
                route_update, self.queue, self.__bus).add_to_queue()

        EnvironmentIdle(self.queue).add_to_queue()

        return 'Environment Update process is implemented'


class EnvironmentIdle(ActionEvent):
    def __init__(self, queue):
        super().__init__('EnvironmentIdle', queue,
                         state_machine=queue.env.optimization.state_machine)

    def _process(self, env):
        return 'Environment Idle process is implemented'


class Hold(Event):
    def __init__(self, queue, event_time, cv, max_optimization_time):
        super().__init__('Hold', queue, event_time=event_time)

        self.__cv = cv
        self.__max_optimization_time = max_optimization_time
        self.__timestamp = time.time()

        self.__cancelled = False
        self.__on_hold = False
        self.__optimization_process = None

        self.__termination_waiting_time = \
            queue.env.optimization.config.termination_waiting_time

    @property
    def cv(self):
        return self.__cv

    @property
    def on_hold(self):
        return self.__on_hold

    @property
    def cancelled(self):
        return self.__cancelled

    @cancelled.setter
    def cancelled(self, cancelled):
        self.__cancelled = cancelled

    @property
    def optimization_process(self):
        return self.__optimization_process

    @optimization_process.setter
    def optimization_process(self, optimization_process):
        self.__optimization_process = optimization_process

    def _process(self, env):
        with self.__cv:
            self.__on_hold = True
            if not self.__cancelled:
                elapsed_time = time.time() - self.__timestamp
                timeout = self.__max_optimization_time - elapsed_time \
                    if self.__max_optimization_time - elapsed_time > 0 else 0
                wait_return = self.__cv.wait(timeout=timeout)
                if not wait_return:
                    self.__terminate_process()

        return 'Hold process is implemented'

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
