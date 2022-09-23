import copy
import logging

from multimodalsim.optimization.state import State
from multimodalsim.simulator.event import Event
from multimodalsim.simulator.request import PassengerUpdate
from multimodalsim.simulator.status import OptimizationStatus
from multimodalsim.simulator.vehicle import RouteUpdate

logger = logging.getLogger(__name__)


class Optimize(Event):
    def __init__(self, time, queue):
        super().__init__('Optimize', queue, time)
        self.__env = None
        self.queue = queue

    def process(self, env):
        self.__env = env

        if self.__env.optimization.status.name != 'IDLE':
            self.time += 1
            self.add_to_queue()
            return 'Optimize event has been put back in the queue'

        self.__env.optimization.update_status(OptimizationStatus.OPTIMIZING)

        state_copy = self.__env.get_state_copy()
        state = State(state_copy)

        self.__set_current_stops_in_state_to_next_stop_if_none(state)

        optimization_result = self.__env.optimization.dispatch(state)

        self.__reinitialize_current_stops_in_state()

        EnvironmentUpdate(optimization_result, self.queue).add_to_queue()

        return 'Optimize process is implemented'

    def __set_current_stops_in_state_to_next_stop_if_none(self, state):

        self.__state_vehicles_with_modified_current_stops = []

        for vehicle in state.vehicles:
            if vehicle.route.current_stop is None:
                vehicle.route.current_stop = vehicle.route.next_stops.pop(0)
                self.__state_vehicles_with_modified_current_stops.append(vehicle)

    def __reinitialize_current_stops_in_state(self):
        for vehicle in self.__state_vehicles_with_modified_current_stops:
            vehicle.route.next_stops.insert(0, vehicle.route.current_stop)
            vehicle.route.current_stop = None


class EnvironmentUpdate(Event):
    def __init__(self, optimization_result, queue):
        super().__init__('EnvironmentUpdate', queue)
        self.optimization_result = optimization_result

    def process(self, env):

        env.optimization.update_status(OptimizationStatus.UPDATEENVIRONMENT)

        # Patrick: Temporary solution to prevent circular import. Maybe the code should be rearranged.
        from multimodalsim.simulator.passenger_event_process import PassengerAssignment
        for trip in self.optimization_result.modified_requests:
            current_leg = trip.current_leg
            next_legs = trip.next_legs

            passenger_update = PassengerUpdate(trip.current_leg.assigned_vehicle.id, trip.req_id, current_leg,
                                               next_legs)
            PassengerAssignment(passenger_update, self.queue).add_to_queue()

        # Patrick: Temporary solution to prevent circular import. Maybe the code should be rearranged.
        from multimodalsim.simulator.vehicle_event_process import VehicleNotification
        for veh in self.optimization_result.modified_vehicles:
            if veh.route.current_stop is not None:
                # Add the passengers_to_board of current_stop that were modified during optimization.
                current_stop_modified_passengers_to_board = [trip for trip in veh.route.current_stop.passengers_to_board
                                                             if trip in self.optimization_result.modified_requests]
                current_stop_departure_time = veh.route.current_stop.departure_time
            else:
                current_stop_modified_passengers_to_board = None
                current_stop_departure_time = None

            # Add the assigned_legs of route that were modified during optimization.
            modified_trips_ids = [modified_trip.req_id for modified_trip in self.optimization_result.modified_requests]
            modified_assigned_legs = [leg for leg in veh.route.assigned_legs if leg.trip.req_id in modified_trips_ids]

            next_stops = veh.route.next_stops
            route_update = RouteUpdate(veh.id,
                                       current_stop_modified_passengers_to_board=
                                       current_stop_modified_passengers_to_board,
                                       next_stops=next_stops,
                                       current_stop_departure_time=current_stop_departure_time,
                                       modified_assigned_legs=modified_assigned_legs)
            VehicleNotification(route_update, self.queue).add_to_queue()

        EnvironmentIdle(self.queue).add_to_queue()

        return 'Environment Update process is implemented'


class EnvironmentIdle(Event):
    def __init__(self, queue):
        super().__init__('EnvironmentIdle', queue)

    def process(self, env):
        env.optimization.update_status(OptimizationStatus.IDLE)

        return 'Environment Idle process is implemented'