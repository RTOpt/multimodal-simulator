import logging
import math

from multimodalsim.optimization.optimization import OptimizationResult
from multimodalsim.simulator.vehicle import Stop, GPSLocation
from networkx.algorithms.shortest_paths.generic import shortest_path

logger = logging.getLogger(__name__)


class Dispatcher(object):

    def __init__(self):
        pass

    def dispatch(self, state):
        raise NotImplementedError('dispatch not implemented')


class ShuttleDispatcher(Dispatcher):

    def __init__(self):
        super().__init__()

    def optimize(self, non_assigned_trips, vehicles, state):
        raise NotImplementedError('optimize of {} not implemented'.
                                  format(self.__class__.__name__))

    def dispatch(self, state):

        non_assigned_trips = state.non_assigned_trips
        vehicles = state.vehicles

        modified_trips = []
        modified_vehicles = []

        if len(non_assigned_trips) > 0:
            current_stop_departure_time_by_vehicle_id, \
            next_stops_by_vehicle_id, vehicle_trips_by_vehicle_id = \
                self.optimize(non_assigned_trips, vehicles, state)

            for vehicle_id, veh_trips in vehicle_trips_by_vehicle_id.items():
                vehicle = veh_trips["vehicle"]
                trips = veh_trips["trips"]

                current_stop_departure_time = \
                    current_stop_departure_time_by_vehicle_id[vehicle_id]
                next_stops = next_stops_by_vehicle_id[vehicle_id]

                self.__update_route_stops(vehicle.route,
                                                 current_stop_departure_time,
                                                 next_stops)

                self.__assign_legs_vehicle(trips, vehicle)

                modified_trips.extend(trips)
                modified_vehicles.append(vehicle)

            self.__assign_trips_to_stops(vehicle_trips_by_vehicle_id)

        return OptimizationResult(state, modified_trips, modified_vehicles)

    def __update_route_stops(self, route, current_stop_departure_time,
                             next_stops):

        route.current_stop.departure_time = current_stop_departure_time

        if len(route.next_stops) != 0 \
                and len(next_stops) != 0 \
                and route.next_stops[
            -1].location == \
                next_stops[0].location:
            route.next_stops.extend(
                next_stops[1:])
        else:
            route.next_stops.extend(next_stops)

    def __assign_legs_vehicle(self, trips, vehicle):
        for trip in trips:
            trip.current_leg.assigned_vehicle = vehicle
            vehicle.route.assign_leg(trip.current_leg)

    def __assign_trips_to_stops(self, vehicle_trips_by_vehicle_id):

        for vehicle_id, veh_trips in vehicle_trips_by_vehicle_id.items():
            veh = veh_trips["vehicle"]
            trips = veh_trips["trips"]

            for trip in trips:
                self.__assign_trip_to_stops(trip, veh.route)

    def __assign_trip_to_stops(self, trip, route):
        boarding_stop_found = False
        alighting_stop_found = False

        current_location = route.current_stop.location

        if trip.origin == current_location:
            route.current_stop.passengers_to_board.append(trip)
            boarding_stop_found = True

        for stop in route.next_stops:
            if trip.origin == stop.location and not boarding_stop_found:
                stop.passengers_to_board.append(trip)
                boarding_stop_found = True
            elif trip.destination == stop.location and boarding_stop_found \
                    and not alighting_stop_found:
                stop.passengers_to_alight.append(trip)
                alighting_stop_found = True


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
            if trip.current_leg is not None:
                optimal_vehicle = self.__find_optimal_vehicle_for_leg(
                    trip.current_leg)
            else:
                optimal_vehicle = None

            if optimal_vehicle is not None:
                self.__assign_trip_to_vehicle(trip, optimal_vehicle)
                self.__assign_trip_to_stops(trip, optimal_vehicle)

        logger.debug("END OPTIMIZE\n*******************")

        return OptimizationResult(state, self.__modified_trips,
                                  self.__modified_vehicles)

    def __find_optimal_vehicle_for_leg(self, leg):

        origin_stop_id = leg.origin.label
        destination_stop_id = leg.destination.label

        optimal_vehicle = None
        earliest_arrival_time = None
        for vehicle in self.__state.vehicles:
            origin_departure_time, destination_arrival_time = \
                self.__get_origin_departure_time_and_destination_arrival_time(
                    vehicle, origin_stop_id, destination_stop_id)

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
            self, vehicle, origin_stop_id, destination_stop_id):
        origin_stop = self.__get_stop_by_stop_id(origin_stop_id, vehicle)
        destination_stop = self.__get_stop_by_stop_id(destination_stop_id,
                                                      vehicle)

        origin_departure_time = None
        destination_arrival_time = None
        if origin_stop is not None and destination_stop is not None \
                and origin_stop.departure_time < destination_stop.arrival_time:
            origin_departure_time = origin_stop.departure_time
            destination_arrival_time = destination_stop.arrival_time

        return origin_departure_time, destination_arrival_time

    def __assign_trip_to_vehicle(self, trip, vehicle):

        trip.current_leg.assigned_vehicle = vehicle

        vehicle.route.assign_leg(trip.current_leg)

        self.__modified_vehicles.append(vehicle)
        self.__modified_trips.append(trip)

    def __assign_trip_to_stops(self, trip, vehicle):

        origin_stop = self.__get_stop_by_stop_id(trip.current_leg.origin.label,
                                                 vehicle)
        destination_stop = self.__get_stop_by_stop_id(
            trip.current_leg.destination.label, vehicle)

        origin_stop.passengers_to_board.append(trip)

        destination_stop.passengers_to_alight.append(trip)

    def __get_stop_by_stop_id(self, stop_id, vehicle):
        found_stop = None
        if vehicle.route.current_stop is not None and stop_id \
                == vehicle.route.current_stop.location.label:
            found_stop = vehicle.route.current_stop

        for stop in vehicle.route.next_stops:
            if stop_id == stop.location.label:
                found_stop = stop

        return found_stop
