import logging

from multimodalsim.optimization.dispatcher import Dispatcher
from multimodalsim.optimization.optimization import OptimizationResult

logger = logging.getLogger(__name__)


class FixedLineDispatcher(Dispatcher):

    def __init__(self):
        super().__init__()
        self.__non_assigned_released_requests_list = None
        self.__state = None
        self.__modified_trips = []
        self.__modified_vehicles = []

    def dispatch(self, state):

        logger.debug("\n******************\nOPTIMIZE (FixedLineDispatcher):\n")
        logger.debug("current_time={}".format(state.current_time))

        self.__state = state
        self.__non_assigned_released_requests_list = state.non_assigned_trips

        # Reinitialize modified_trip and modified_vehicles of Dispatcher.
        self.__modified_trips = []
        self.__modified_vehicles = []

        logger.debug("state.non_assigned_trips: {}".format(
            [trip.id for trip in state.non_assigned_trips]))

        for trip in self.__non_assigned_released_requests_list:
            if len(trip.next_legs) > 0:
                next_leg = trip.next_legs[0]
                optimal_vehicle = self.__find_optimal_vehicle_for_leg(next_leg)
            else:
                optimal_vehicle = None

            if optimal_vehicle is not None:
                route = self.__state.route_by_vehicle_id[optimal_vehicle.id]
                self.__assign_trip_to_vehicle(trip, optimal_vehicle, route)
                self.__assign_trip_to_stops(trip, route)

        logger.debug("END OPTIMIZE\n*******************")

        return OptimizationResult(state, self.__modified_trips,
                                  self.__modified_vehicles)

    def __find_optimal_vehicle_for_leg(self, leg):

        origin_stop_id = leg.origin.label
        destination_stop_id = leg.destination.label

        optimal_vehicle = None
        earliest_arrival_time = None
        for vehicle in self.__state.vehicles:
            route = self.__state.route_by_vehicle_id[vehicle.id]
            origin_departure_time, destination_arrival_time = \
                self.__get_origin_departure_time_and_destination_arrival_time(
                    route, origin_stop_id, destination_stop_id)

            if origin_departure_time is not None \
                    and origin_departure_time > self.__state.current_time \
                    and origin_departure_time >= leg.trip.ready_time \
                    and destination_arrival_time is not None \
                    and destination_arrival_time <= leg.trip.due_time \
                    and (earliest_arrival_time is None
                         or destination_arrival_time < earliest_arrival_time):
                earliest_arrival_time = destination_arrival_time
                optimal_vehicle = vehicle

        return optimal_vehicle

    def __get_origin_departure_time_and_destination_arrival_time(
            self, route, origin_stop_id, destination_stop_id):
        origin_stop = self.__get_stop_by_stop_id(origin_stop_id, route)
        destination_stop = self.__get_stop_by_stop_id(destination_stop_id,
                                                      route)

        origin_departure_time = None
        destination_arrival_time = None
        if origin_stop is not None and destination_stop is not None \
                and origin_stop.departure_time < destination_stop.arrival_time:
            origin_departure_time = origin_stop.departure_time
            destination_arrival_time = destination_stop.arrival_time

        return origin_departure_time, destination_arrival_time

    def __assign_trip_to_vehicle(self, trip, vehicle, route):

        trip.next_legs[0].assigned_vehicle = vehicle

        route.assign_leg(trip.next_legs[0])

        self.__modified_vehicles.append(vehicle)
        self.__modified_trips.append(trip)

    def __assign_trip_to_stops(self, trip, route):

        origin_stop = self.__get_stop_by_stop_id(
            trip.next_legs[0].origin.label, route)
        destination_stop = self.__get_stop_by_stop_id(
            trip.next_legs[0].destination.label, route)

        origin_stop.passengers_to_board.append(trip)

        destination_stop.passengers_to_alight.append(trip)

    def __get_stop_by_stop_id(self, stop_id, route):
        found_stop = None
        if route.current_stop is not None and stop_id \
                == route.current_stop.location.label:
            found_stop = route.current_stop

        for stop in route.next_stops:
            if stop_id == stop.location.label:
                found_stop = stop

        return found_stop
