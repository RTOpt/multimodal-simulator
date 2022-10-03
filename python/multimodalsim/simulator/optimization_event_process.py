import logging

from multimodalsim.optimization.state import State
from multimodalsim.simulator.event import Event
from multimodalsim.simulator.request import PassengerUpdate
from multimodalsim.simulator.status import OptimizationStatus
from multimodalsim.simulator.vehicle import RouteUpdate

import multimodalsim.simulator.passenger_event_process as passenger_event_process
import multimodalsim.simulator.vehicle_event_process as vehicle_event_process

logger = logging.getLogger(__name__)


class Optimize(Event):
    def __init__(self, time, queue):
        super().__init__('Optimize', queue, time)
        self.__env = None

    def process(self, env):
        self.__env = env

        if self.__env.optimization.status.name != 'IDLE':
            self.time += 1
            self.add_to_queue()
            return 'Optimize event has been put back in the queue'

        self.__env.optimization.status = OptimizationStatus.OPTIMIZING

        state_copy = self.__env.get_state_copy()
        state = State(state_copy)

        state.fix_routes_for_time_interval(self.__env.optimization.fixed_time_interval)

        optimization_result = self.__env.optimization.dispatch(state)

        state.unfix_routes_for_time_interval(self.__env.optimization.fixed_time_interval)

        EnvironmentUpdate(optimization_result, self.queue).add_to_queue()

        return 'Optimize process is implemented'


class EnvironmentUpdate(Event):
    def __init__(self, optimization_result, queue):
        super().__init__('EnvironmentUpdate', queue)
        self.__optimization_result = optimization_result

    def process(self, env):

        env.optimization.status = OptimizationStatus.UPDATEENVIRONMENT

        for trip in self.__optimization_result.modified_requests:
            current_leg = trip.current_leg
            next_legs = trip.next_legs

            passenger_update = PassengerUpdate(trip.current_leg.assigned_vehicle.id, trip.id, current_leg,
                                               next_legs)
            passenger_event_process.PassengerAssignment(passenger_update, self.queue).add_to_queue()

        for veh in self.__optimization_result.modified_vehicles:
            if veh.route.current_stop is not None:
                # Add the passengers_to_board of current_stop that were modified during optimization.
                current_stop_modified_passengers_to_board = [trip for trip in veh.route.current_stop.passengers_to_board
                                                             if trip in self.__optimization_result.modified_requests]
                current_stop_departure_time = veh.route.current_stop.departure_time
            else:
                current_stop_modified_passengers_to_board = None
                current_stop_departure_time = None

            # Add the assigned_legs of route that were modified during optimization.
            modified_trips_ids = [modified_trip.id for modified_trip in self.__optimization_result.modified_requests]
            modified_assigned_legs = [leg for leg in veh.route.assigned_legs if leg.trip.id in modified_trips_ids]

            next_stops = veh.route.next_stops
            route_update = RouteUpdate(veh.id,
                                       current_stop_modified_passengers_to_board=
                                       current_stop_modified_passengers_to_board,
                                       next_stops=next_stops,
                                       current_stop_departure_time=current_stop_departure_time,
                                       modified_assigned_legs=modified_assigned_legs)
            vehicle_event_process.VehicleNotification(route_update, self.queue).add_to_queue()

        EnvironmentIdle(self.queue).add_to_queue()

        return 'Environment Update process is implemented'


class EnvironmentIdle(Event):
    def __init__(self, queue):
        super().__init__('EnvironmentIdle', queue)

    def process(self, env):
        env.optimization.status = OptimizationStatus.IDLE

        return 'Environment Idle process is implemented'
