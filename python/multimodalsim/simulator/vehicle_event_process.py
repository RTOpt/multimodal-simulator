import logging

from multimodalsim.simulator.event import Event
from multimodalsim.simulator.optimization_event_process import Optimize
from multimodalsim.simulator.status import VehicleStatus
from multimodalsim.simulator.vehicle import Route

logger = logging.getLogger(__name__)


class VehicleReady(Event):
    def __init__(self, vehicle, next_stops, queue):
        super().__init__('VehicleReady', queue, vehicle.release_time)
        self.__vehicle = vehicle
        self.__next_stops = next_stops

    def process(self, env):
        env.add_vehicle(self.__vehicle)

        self.__vehicle.route = Route(self.__vehicle, self.__next_stops)

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
        else:
            # End of route
            # Patrick: Should we set the status to COMPLETE if there are no next stops?
            self.route.update_vehicle_status(VehicleStatus.COMPLETE)

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
        for request in passengers_to_alight_copy:
            if request in self.route.onboard_trips:
                self.route.alight(request)
                PassengerAlighting(request, self.queue).add_to_queue()

        VehicleBoarding(self.route, self.queue).add_to_queue()

        return 'Vehicle Alighting process is implemented'


class VehicleNotification(Event):
    def __init__(self, route_update, queue):
        super().__init__('VehicleNotification', queue)
        self.route_update = route_update

    def process(self, env):

        vehicle = env.get_vehicle_by_id(self.route_update.vehicle_id)
        logger.debug("vehicle.id={}".format(vehicle.id))

        if self.route_update.next_stops is not None:
            for stop in self.route_update.next_stops:
                self.__update_stop_with_actual_requests(env, stop)
            vehicle.route.next_stops = self.route_update.next_stops

        if self.route_update.current_stop_modified_passengers_to_board is not None:
            # Add passengers to board that were modified by optimization
            # and that are not already present in vehicle.route.current_stop.passengers_to_board
            actual_modified_passengers_to_board = self.__replace_copy_requests_with_actual_requests(
                env, self.route_update.current_stop_modified_passengers_to_board)
            for trip in actual_modified_passengers_to_board:
                if trip not in vehicle.route.current_stop.passengers_to_board:
                    vehicle.route.current_stop.passengers_to_board.append(trip)

        if self.route_update.current_stop_departure_time is not None and vehicle.route.current_stop is not None:
            # If vehicle.route.current_stop.departure_time is equal to env.current_time, then the vehicle may have
            # already left the current stop. In this case vehicle.route.current_stop is None, and we do not modify it.
            vehicle.route.current_stop.departure_time = self.route_update.current_stop_departure_time

        if self.route_update.assigned_trips is not None:
            vehicle.route.assigned_trips = \
                self.__replace_copy_requests_with_actual_requests(env,
                                                                  self.route_update.assigned_trips)

        return 'Notify Vehicle process is implemented'

    def __update_stop_with_actual_requests(self, env, stop):

        stop.passengers_to_board = self.__replace_copy_requests_with_actual_requests(env, stop.passengers_to_board)
        stop.boarding_passengers = self.__replace_copy_requests_with_actual_requests(env, stop.boarding_passengers)
        stop.boarded_passengers = self.__replace_copy_requests_with_actual_requests(env, stop.boarded_passengers)
        stop.passengers_to_alight = self.__replace_copy_requests_with_actual_requests(env, stop.passengers_to_alight)

    def __replace_copy_requests_with_actual_requests(self, env, requests_list):

        return list(env.get_trip_by_id(req.req_id) for req in requests_list)


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
