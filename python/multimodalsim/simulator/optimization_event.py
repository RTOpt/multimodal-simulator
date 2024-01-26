import logging
import os
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
    def __init__(self, time, queue, multiple_optimize_events=False,
                 batch=None, max_optimization_time=1, wait_for=5):
        if batch is not None:
            # Round to the smallest integer greater than or equal to time that
            # is also a multiple of batch.#
            time = time + (batch - (time % batch)) % batch
        super().__init__('Optimize', queue, time,
                         event_priority=self.VERY_LOW_PRIORITY,
                         state_machine=queue.env.optimization.state_machine)
        self.__multiple_optimize_events = multiple_optimize_events
        self.__wait_for = wait_for
        self.__max_optimization_time = max_optimization_time

    def process(self, env):
        logger.error(
            "{} - {} - {}: {}".format(self.index, self.time, self.priority,
                                      self))

        logger.error("self.state_machine.current_state={}".format(self.state_machine.current_state))
        logger.error("type={}".format(
            type(self.state_machine.current_state.status)))
        if self.state_machine.current_state.status == OptimizationStatus.OPTIMIZING:
            logger.error("PUT BACK IN QUEUE")
            if env.optimize_cv is not None:
                with env.optimize_cv:
                    logger.error("env.optimize_cv.wait()")
                    env.optimize_cv.wait()
                    logger.error("AFTER env.optimize_cv.wait()")

            self.add_to_queue()

            process_message = 'Optimize process is put back in the event queue'
        else:
            logger.error("PROCESS")
            if self.state_machine is not None:
                self.state_machine.next_state(self.__class__, env)
            process_message = self._process(env)

        return process_message

    def _process(self, env):

        env_stats = env.get_environment_statistics()

        if env.optimization.need_to_optimize(env_stats):

            logger.warning("BEFORE")
            env.optimize_cv = Condition()

            env.optimization.state = env.get_new_state()

            cv = Condition()

            hold_event = Hold(self.queue, env.current_time
                              + env.optimization.freeze_interval, cv)
            hold_event.add_to_queue()

            logger.warning("hold_event")

            optimize_thread = Thread(target=self.__optimize, args=(env, cv,
                                                                   hold_event))
            logger.warning("AFTER")

            optimize_thread.start()

        return 'Optimize process is implemented'

    def add_to_queue(self):

        if self.__multiple_optimize_events or not \
                self.queue.is_event_type_in_queue(self.__class__, self.time):
            super().add_to_queue()

    def __optimize(self, env, cv, hold_event):

        logger.warning("__optimize")



        logger.error("BEFORE optimize_cv")

        logger.error(env.optimization.state.__dict__)

        # logger.error(env.optimization.state.optimize_cv)

        logger.warning("get_new_state")

        env.optimization.state.freeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        logger.warning("env.optimization.state.current_time={}".format(
            env.optimization.state.current_time))

        logger.warning("env.optimization.freeze_interval={}".format(env.optimization.freeze_interval))

        logger.error("env.current_time={}".format(env.current_time))

        with mp.Manager() as manager:

            logger.error("env.current_time={}".format(env.current_time))

            logger.warning("manager")

            process_dict = manager.dict()

            logger.warning("manager.dict()")

            logger.error(env.optimization.__dict__)

            process_dict["optimization"] = env.optimization

            process_dict["optimization_result"] = None

            logger.warning("DispatchProcess")

            opt_process = DispatchProcess(dispatch=Optimize.dispatch,
                                          process_dict=process_dict)

            logger.warning("BEFORE opt_process")

            opt_process.start()

            logger.warning("PROCESS PID: {}".format(opt_process.pid))

            logger.warning("opt_process.start()")



            logger.warning(
                "opt_process.is_alive()={}".format(opt_process.is_alive()))

            # time.sleep(5)

            process_terminated = False

            logger.warning("BEFORE PROCESS IS ALIVE")
            logger.warning(
                "opt_process.is_alive()={}".format(opt_process.is_alive()))

            while opt_process.is_alive():
                if hold_event.on_hold:
                    logger.warning("BEFORE SLEEP")
                    time.sleep(self.__max_optimization_time)
                    logger.warning("AFTER SLEEP")
                    if opt_process.is_alive():
                        logger.warning("Terminate optimization process"
                                       .format(self.__wait_for))
                        opt_process.terminate()
                        time.sleep(self.__wait_for)
                        if opt_process.exitcode is None:
                            opt_process.kill()
                        process_terminated = True

            logger.warning("process_terminated: {}".format(process_terminated))
            if not process_terminated:
                opt_process.join()
            logger.warning("opt_process.join(): AFTER: {}".format(
                opt_process.pid))

            opt_process.close()

            logger.warning("cv")
            with cv:
                hold_event.canceled = True

                optimization_result = process_dict["optimization_result"]
                logger.warning(optimization_result)

                logger.warning("EnvironmentUpdate")
                EnvironmentUpdate(optimization_result,
                                  self.queue).add_to_queue()

                logger.warning("notify")
                cv.notify()

                logger.warning("OUT")

        env.optimization.state.unfreeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        with env.optimize_cv:
            env.optimize_cv.notify()

    @staticmethod
    def dispatch(optimization):
        optimization_result = optimization.dispatch(optimization.state)

        return optimization_result


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
                # Add the passengers_to_board of current_stop that were
                # modified during optimization.
                current_stop_modified_passengers_to_board = \
                    [trip for trip
                     in route.current_stop.passengers_to_board
                     if trip in self.__optimization_result.modified_requests]
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


class Hold(Event):
    def __init__(self, queue, event_time, cv):
        super().__init__('Hold', queue, event_time=event_time)

        self.__cv = cv

        self.__canceled = False
        self.__on_hold = False

    @property
    def cv(self):
        return self.__cv

    @property
    def on_hold(self):
        return self.__on_hold

    @property
    def canceled(self):
        return self.__canceled

    @canceled.setter
    def canceled(self, canceled):
        self.__canceled = canceled

    def _process(self, env):
        logger.critical("HOLD: BEGIN")
        self.__on_hold = True
        if not self.__canceled:
            logger.critical("not canceled!")
            with self.__cv:
                self.__cv.wait()
        logger.critical("HOLD: END")

        return 'Hold process is implemented'


class DispatchProcess(mp.Process):
    def __init__(self, dispatch, process_dict):

        super().__init__()
        self.__dispatch = dispatch
        self.__process_dict = process_dict

    def run(self):
        process_id = os.getpid()
        logger.error("PROCESS BEGIN: {}".format(process_id))

        optimization = self.__process_dict["optimization"]

        optimization_result = self.__dispatch(optimization)

        self.__process_dict["optimization_result"] = optimization_result

        logger.error("PROCESS END: {}".format(process_id))
