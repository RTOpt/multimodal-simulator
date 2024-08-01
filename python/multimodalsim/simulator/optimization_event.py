import logging
import time
from threading import Thread, Condition
import multiprocessing as mp
from typing import Optional, Callable

from multimodalsim.optimization.partition import PartitionSubset
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
import multimodalsim.state_machine.state_machine as state_machine_module

logger = logging.getLogger(__name__)


class Optimize(ActionEvent):
    def __init__(self, time: float, queue: 'event_queue.EventQueue',
                 multiple_optimize_events: Optional[bool] = None,
                 batch: Optional[float] = None,
                 max_optimization_time: Optional[float] = None,
                 asynchronous: Optional[bool] = None,
                 partition_subset: Optional[PartitionSubset] = None) -> None:

        self.__load_parameters_from_config(queue.env.optimization,
                                           multiple_optimize_events, batch,
                                           max_optimization_time, asynchronous)

        self.__partition_subset = partition_subset
        self.__state = None
        self.__process_pool = queue.env.optimization.process_pool

        other_events_created = self.__create_other_optimize_events_if_needed(
            queue.env.optimization, time, queue)

        if other_events_created:
            # This Optimize event is only used to create the Optimize events
            # related to the partition, but it will never be processed in
            # practice.
            super().__init__('Optimize (Partition)', queue, time)
        else:
            # Optimize event corresponding to a partition subset or normal
            # Optimize event if no partition is used.
            state_machine = self.__get_state_machine(queue.env.optimization)
            if self.__batch is not None:
                # Round to the smallest integer greater than or equal to time
                # that is also a multiple of batch.
                time = time + (batch - (time % batch)) % batch

            event_name = 'Optimize ({})'.format(self.__partition_subset.id) \
                if self.__partition_subset is not None else 'Optimize'
            super().__init__(event_name, queue, time,
                             event_priority=self.VERY_LOW_PRIORITY,
                             state_machine=state_machine)

    def process(self, env: 'environment.Environment') -> str:

        if self.state_machine.current_state.status \
                == OptimizationStatus.OPTIMIZING:
            optimize_cv = env.optimize_cv[self.__partition_subset.id] \
                if self.__partition_subset is not None else env.optimize_cv
            with optimize_cv:
                optimize_cv.wait()
            self.add_to_queue()
            process_message = 'Optimize process is put back in the event queue'
        else:
            process_message = super().process(env)

        return process_message

    def _process(self, env: 'environment.Environment') -> str:

        stats_extractor = env.optimization.environment_statistics_extractor
        env_stats = stats_extractor.extract_environment_statistics(env)

        if env.optimization.need_to_optimize(env_stats):
            self.__update_state(env)

            if self.__asynchronous:
                self.__update_optimize_cv(env)
                self.__optimize_asynchronously(env)
            else:
                self.__optimize_synchronously(env)
        else:
            optimization_result = optimization_module.OptimizationResult(
                None, [], [])
            EnvironmentUpdate(optimization_result, self.queue,
                              self.state_machine).add_to_queue()

        return 'Optimize process is implemented'

    def add_to_queue(self) -> None:

        if self.__partition_subset is None:
            if self.__multiple_optimize_events or not \
                    self.queue.is_event_type_in_queue(self.__class__,
                                                      self.time):
                if self.__other_optimize_events is not None:
                    # Case 1: Maine Optimize event of the Partition.
                    # Add all the Optimize events corresponding to a
                    # PartitionSubset to the queue. The main Optimize event of
                    # the Partition is not added to the queue.
                    for optimize_events in self.__other_optimize_events:
                        optimize_events.add_to_queue()
                else:
                    # Case 2: No Partition is used.
                    # The Optimize event is added to the queue.
                    super().add_to_queue()
        else:
            # Case 3: Optimize event of a PartitionSubset.
            # The Optimize event is added to the queue.
            super().add_to_queue()

    def __get_state_machine(self, optimization):
        if self.__partition_subset is not None:
            state_machine = optimization.state_machine[
                self.__partition_subset.id]
        else:
            state_machine = optimization.state_machine

        return state_machine

    def __create_other_optimize_events_if_needed(self, optimization, time,
                                                 queue):
        """If a Partition is used and the current Optimize event corresponds
        to the main Optimize event, then creates one Optimize event for each
        PartitionSubset of the Partition."""

        self.__other_optimize_events = None

        other_events_created = False
        if self.__partition_subset is None \
                and optimization.partition is not None:
            # Main Optimize event of the partition (it creates the Optimize
            # events of the partition subsets).
            self.__other_optimize_events = []
            for subset in optimization.partition.subsets:
                self.__other_optimize_events.append(
                    Optimize(time, queue, partition_subset=subset))
            other_events_created = True

        return other_events_created

    def __update_state(self, env):
        if self.__partition_subset is None:
            self.__state = env.get_new_state()
            env.optimization.update_state(self.__state)
        else:
            self.__state = env.get_new_state(
                self.__partition_subset,
                self.__state_includes_partition_subset_only)
            env.optimization.update_state(self.__state,
                                          self.__partition_subset)

    def __update_optimize_cv(self, env):
        if self.__partition_subset is None:
            env.optimize_cv = Condition()
        else:
            if env.optimize_cv is None:
                env.optimize_cv = {}
            env.optimize_cv[self.__partition_subset.id] = Condition()

    def __optimize_synchronously(self, env):
        self.__state.freeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        optimization_result = env.optimization.dispatch(
            self.__state)

        self.__state.unfreeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        EnvironmentUpdate(optimization_result, self.queue,
                          self.state_machine).add_to_queue()

    def __optimize_asynchronously(self, env):
        hold_cv = Condition()

        hold_event = Hold(self.queue, env.current_time
                          + env.optimization.freeze_interval, hold_cv,
                          self.__max_optimization_time, self.__process_pool)

        hold_event.add_to_queue()

        optimize_thread = Thread(target=self.__optimize_in_new_thread,
                                 args=(env, hold_event))
        optimize_thread.start()

    def __optimize_in_new_thread(self, env, hold_event):

        self.__state.freeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        async_result = self.__process_pool.apply_async(
            dispatch_process_function,
            args=(Optimize.dispatch, self.__state,
                  env.optimization.dispatcher.dispatch,
                  self.__partition_subset))

        optimization_result = async_result.get()

        self.__create_environment_update(optimization_result, hold_event)

        self.__state.unfreeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        if self.__partition_subset is None:
            optimize_cv = env.optimize_cv
        else:
            optimize_cv = env.optimize_cv[self.__partition_subset.id]
        with optimize_cv:
            optimize_cv.notify()

    def __create_environment_update(self, optimization_result, hold_event):
        with hold_event.cv:
            hold_event.cancelled = True
            EnvironmentUpdate(optimization_result,
                              self.queue, self.state_machine).add_to_queue()
            hold_event.cv.notify()

    @staticmethod
    def dispatch(dispatch_function: Callable,
                 state: State,
                 partition_subset: Optional[PartitionSubset] = None) \
            -> 'optimization_module.OptimizationResult':
        optimization_result = dispatch_function(state, partition_subset)

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

        self.__state_includes_partition_subset_only = \
            config.state_includes_partition_subset_only


class EnvironmentUpdate(ActionEvent):
    def __init__(self,
                 optimization_result: 'optimization_module.OptimizationResult',
                 queue: 'event_queue.EventQueue',
                 state_machine:
                 'state_machine_module.StateMachine') -> None:
        super().__init__('EnvironmentUpdate', queue,
                         state_machine=state_machine)
        self.__optimization_result = optimization_result

    def _process(self, env: 'environment.Environment') -> str:

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
            route_update = vehicle_module.RouteUpdate(
                veh.id, current_stop_modified_passengers_to_board, next_stops,
                current_stop_departure_time, modified_assigned_legs)
            vehicle_event_process.VehicleNotification(
                route_update, self.queue).add_to_queue()

        EnvironmentIdle(self.queue, self.state_machine).add_to_queue()

        return 'Environment Update process is implemented'


class EnvironmentIdle(ActionEvent):
    def __init__(self, queue: 'event_queue.EventQueue',
                 state_machine:
                 'state_machine_module.StateMachine'
                 ) -> None:
        super().__init__('EnvironmentIdle', queue,
                         state_machine=state_machine)

    def _process(self, env: 'environment.Environment') -> str:
        return 'Environment Idle process is implemented'


class Hold(TimeSyncEvent):
    def __init__(self, queue: 'event_queue.EventQueue', event_time: float,
                 cv: Condition, max_optimization_time: float,
                 process_pool: mp.Pool) -> None:
        super().__init__(queue, event_time,
                         max_waiting_time=max_optimization_time,
                         event_name='Hold')

        self.__cv = cv
        self.__max_optimization_time = max_optimization_time
        self.__timestamp = time.time()

        self.__process_pool = process_pool

        self.__termination_waiting_time = \
            queue.env.optimization.config.termination_waiting_time

    @property
    def cv(self) -> Condition:
        return self.__cv

    def _synchronize(self) -> None:
        with self.__cv:
            if not self.cancelled:
                wait_return = self.__cv.wait(timeout=self._waiting_time)
                if not wait_return:
                    self.__terminate_process()

    def __terminate_process(self):
        logger.warning("Terminate optimization process in {} seconds.".format(
            self.__termination_waiting_time))
        self.__process_pool.terminate()
        time.sleep(self.__termination_waiting_time)
        for process in self.__process_pool._pool:
            if process.exitcode is None:
                process.kill()
        raise RuntimeError("Optimization exceeded the time limit of {} "
                           "seconds.".format(self.__max_optimization_time))


def dispatch_process_function(
        dispatch: Callable, state, dispatch_function, partition_subset) \
        -> optimization_module.OptimizationResult:
    optimization_result = dispatch(dispatch_function, state,
                                   partition_subset)

    return optimization_result
