import logging

from multimodalsim.simulator.event import Event
from multimodalsim.simulator.optimization_event_process import Optimize
from multimodalsim.simulator.status import VehicleStatus
from multimodalsim.simulator.vehicle import Route

logger = logging.getLogger(__name__)


class VehicleReady(Event):
    def __init__(self, vehicle, queue):
        super().__init__('VehicleReady', queue, vehicle.release_time)
        self.__vehicle = vehicle
        # self.__next_stops = next_stops

    def process(self, env):
        env.add_vehicle(self.__vehicle)
        env.add_non_assigned_vehicle(self.__vehicle)

        # self.__vehicle.route = Route(self.__vehicle, self.__next_stops)
        if self.__vehicle.route is None:
            self.__vehicle.route = Route(self.__vehicle)

        Optimize(env.current_time, self.queue).add_to_queue()
        VehicleBoarding(self.__vehicle.route, self.queue).add_to_queue()

        return 'Vehicle Ready process is implemented'


class VehicleBoarding(Event):
    def __init__(self, route, queue):

        # Patrick: Is the time current_stop.arrival_time or current_stop.departure_time?
        super().__init__('VehicleBoarding', queue, route.current_stop.departure_time)
        self.route = route

    def process(self, env):

        self.route.update_vehicle_status(VehicleStatus.BOARDING)

        # Patrick: Temporary solution to prevent circular import. Maybe the code should be rearranged.
        from multimodalsim.simulator.passenger_event_process import PassengerToBoard

        if len(self.route.requests_to_pickup()) > 0:
            # Passengers to board
            passengers_to_board_copy = self.route.current_stop.passengers_to_board.copy()
            for req in passengers_to_board_copy:
                self.route.current_stop.initiate_boarding(req)
                PassengerToBoard(req, self.queue).add_to_queue()
        elif len(self.route.next_stops) > 0:
            # No passengers to board
            VehicleDeparture(self.route, self.queue).add_to_queue()
        # else:
        #     # End of route
        #     # Patrick: Should we set the status to COMPLETE if there are no next stops?
        #     self.route.update_vehicle_status(VehicleStatus.COMPLETE)

        return 'Vehicle Boarding process is implemented'


class VehicleDeparture(Event):
    def __init__(self, route, queue):
        super().__init__('Vehicle Departure', queue, route.current_stop.departure_time)
        self.route = route

    def process(self, env):
        self.route.update_vehicle_status(VehicleStatus.ENROUTE)

        self.route.depart()

        VehicleArrival(self.route, self.queue).add_to_queue()

        return 'Vehicle Departure process is implemented'


class VehicleArrival(Event):
    def __init__(self, route, queue):
        super().__init__('VehicleArrival', queue, route.next_stops[0].arrival_time)
        self.route = route

    def process(self, env):
        self.route.update_vehicle_status(VehicleStatus.ALIGHTING)

        self.route.arrive()

        from multimodalsim.simulator.passenger_event_process import PassengerAlighting
        passengers_to_alight_copy = self.route.current_stop.passengers_to_alight.copy()
        for trip in passengers_to_alight_copy:
            if trip.current_leg in self.route.onboard_legs:
                self.route.alight(trip)
                PassengerAlighting(trip, self.queue).add_to_queue()

        VehicleBoarding(self.route, self.queue).add_to_queue()

        return 'Vehicle Alighting process is implemented'


class VehicleNotification(Event):
    def __init__(self, route_update, queue):
        super().__init__('VehicleNotification', queue)
        self.__env = None
        self.route_update = route_update

    def process(self, env):

        self.__env = env

        vehicle = self.__env.get_vehicle_by_id(self.route_update.vehicle_id)

        if self.route_update.next_stops is not None:
            for stop in self.route_update.next_stops:
                self.__update_stop_with_actual_trips(stop)
            vehicle.route.next_stops = self.route_update.next_stops

        if self.route_update.current_stop_modified_passengers_to_board is not None:
            # Add passengers to board that were modified by optimization and that are not already present in
            # vehicle.route.current_stop.passengers_to_board
            actual_modified_passengers_to_board = \
                self.__replace_copy_trips_with_actual_trips(self.route_update.
                                                            current_stop_modified_passengers_to_board)
            for trip in actual_modified_passengers_to_board:
                if trip not in vehicle.route.current_stop.passengers_to_board:
                    vehicle.route.current_stop.passengers_to_board.append(trip)

        if self.route_update.current_stop_departure_time is not None and vehicle.route.current_stop is not None:
            # If vehicle.route.current_stop.departure_time is equal to env.current_time, then the vehicle may have
            # already left the current stop. In this case vehicle.route.current_stop is None, and we do not modify it.
            vehicle.route.current_stop.departure_time = self.route_update.current_stop_departure_time

        if self.route_update.modified_assigned_legs is not None:
            # Add the assigned legs that were modified by optimization and that are not already present in
            # vehicle.route.assigned_legs.
            actual_modified_assigned_legs = self.__replace_copy_legs_with_actual_legs(self.route_update.
                                                                                      modified_assigned_legs)
            for leg in actual_modified_assigned_legs:
                if leg not in vehicle.route.assigned_legs:
                    vehicle.route.assigned_legs.append(leg)

        self.__update_env_assigned_vehicles(vehicle)
        VehicleBoarding(vehicle.route, self.queue).add_to_queue()

        return 'Notify Vehicle process is implemented'

    def __modify_route_update_current_stop_if_actual_current_stop_changed(self, actual_vehicle):
        if actual_vehicle.route.current_stop.location == self.route_update.next_stops[0].location:
            # Vehicle was ENROUTE at the time of optimization, but has now arrived at the next stop.
            new_current_stop = self.route_update.next_stops.pop(0)
            self.route_update.current_stop_modified_passengers_to_board = new_current_stop.passengers_to_board

    def __update_stop_with_actual_trips(self, stop):

        stop.passengers_to_board = self.__replace_copy_trips_with_actual_trips(stop.passengers_to_board)
        stop.boarding_passengers = self.__replace_copy_trips_with_actual_trips(stop.boarding_passengers)
        stop.boarded_passengers = self.__replace_copy_trips_with_actual_trips(stop.boarded_passengers)
        stop.passengers_to_alight = self.__replace_copy_trips_with_actual_trips(stop.passengers_to_alight)

    def __replace_copy_trips_with_actual_trips(self, trips_list):

        return list(self.__env.get_trip_by_id(req.req_id) for req in trips_list)

    def __replace_copy_legs_with_actual_legs(self, legs_list):

        return list(self.__env.get_leg_by_id(leg.req_id) for leg in legs_list)

    def __update_env_assigned_vehicles(self, vehicle):
        """Update the assigned vehicles of Environment if necessary"""
        if vehicle in self.__env.get_non_assigned_vehicles() and (len(vehicle.route.assigned_legs) != 0
                                                                  or len(vehicle.route.onboard_legs) != 0):
            self.__env.remove_non_assigned_vehicle(vehicle.id)
            self.__env.add_assigned_vehicle(vehicle)


class VehicleBoarded(Event):
    def __init__(self, trip, queue):
        super().__init__('VehicleBoarded', queue)
        self.trip = trip

    def process(self, env):
        route = self.trip.current_leg.assigned_vehicle.route
        route.board(self.trip)

        if len(route.current_stop.boarding_passengers) == 0:
            # All passengers are on board
            VehicleDeparture(route, self.queue).add_to_queue()
            # Else we wait until all the boarding passengers are on board before creating the event VehicleDeparture.

        return 'Vehicle Boarded process is implemented'
