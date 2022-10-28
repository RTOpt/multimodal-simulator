import logging

from multimodalsim.optimization.state import State
from multimodalsim.simulator.event import ActionEvent
from multimodalsim.simulator.vehicle import RouteUpdate

import multimodalsim.simulator.request as request
import \
    multimodalsim.simulator.passenger_event as passenger_event_process
import multimodalsim.simulator.vehicle_event as vehicle_event_process

logger = logging.getLogger(__name__)


class Optimize(ActionEvent):
    def __init__(self, time, queue, multiple_optimize_events=False):
        super().__init__('Optimize', queue, time, event_priority=10,
                         state_machine=queue.env.optimization.state_machine)
        self.__multiple_optimize_events = multiple_optimize_events

    def _process(self, env):
        state_copy = env.get_state_copy()
        state = State(state_copy)

        state.freeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        optimization_result = env.optimization.dispatch(state)

        state.unfreeze_routes_for_time_interval(
            env.optimization.freeze_interval)

        EnvironmentUpdate(optimization_result, self.queue).add_to_queue()

        return 'Optimize process is implemented'

    def add_to_queue(self):

        if self.__multiple_optimize_events or not \
                self.queue.is_event_type_in_queue(self.__class__, self.time):
            self.queue.put(self)


class EnvironmentUpdate(ActionEvent):
    def __init__(self, optimization_result, queue):
        super().__init__('EnvironmentUpdate', queue,
                         state_machine=queue.env.optimization.state_machine)
        self.__optimization_result = optimization_result

    def _process(self, env):

        for trip in self.__optimization_result.modified_requests:
            current_leg = trip.current_leg
            next_legs = trip.next_legs

            passenger_update = request.PassengerUpdate(
                trip.current_leg.assigned_vehicle.id, trip.id, current_leg,
                next_legs)
            passenger_event_process.PassengerAssignment(
                passenger_update, self.queue).add_to_queue()

        for veh in self.__optimization_result.modified_vehicles:
            if veh.route.current_stop is not None:
                # Add the passengers_to_board of current_stop that were
                # modified during optimization.
                current_stop_modified_passengers_to_board = \
                    [trip for trip
                     in veh.route.current_stop.passengers_to_board
                     if trip in self.__optimization_result.modified_requests]
                current_stop_departure_time = \
                    veh.route.current_stop.departure_time
            else:
                current_stop_modified_passengers_to_board = None
                current_stop_departure_time = None

            # Add the assigned_legs of route that were modified during
            # optimization.
            modified_trips_ids = [modified_trip.id for modified_trip in
                                  self.__optimization_result.modified_requests]
            modified_assigned_legs = [leg for leg in veh.route.assigned_legs
                                      if leg.trip.id in modified_trips_ids]

            next_stops = veh.route.next_stops
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
