import logging
import math

from multimodalsim.optimization.optimization import OptimizationResult
from multimodalsim.simulator.vehicle import Stop, LabelLocation
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

    def prepare_input(self, state):
        # Extract from the state the trips and the vehicles that are sent as
        # input to the optimize method (i.e. the trips and the vehicles that
        # you want to optimize).
        #
        # By default, all trips (i.e., state.trips) and all vehicles (i.e.,
        # state.vehicles) existing at the time of optimization will be
        # optimized.
        #
        # This method can be overriden to return only the trips and the
        # vehicles that should be optimized based on your needs (see, for
        # example, ShuttleSimpleDispatcher).
        #
        # Input:
        #   -state: An object of type State that corresponds to a partial deep
        #    copy of the environment.
        #
        # Output:
        #   -trips: A list of objects of type Trip that corresponds to the
        #    trips (i.e., passengers or requests) that should be considered by
        #    the optimize methods.
        #   -vehicles: A list of objects of type Vehicle that corresponds to
        #   the vehicles (i.e., shuttles) that should be considered by the
        #   optimize methods.

        trips = state.trips  # All the trips
        vehicles = state.vehicles   # All the vehicles

        return trips, vehicles

    def optimize(self, trips, vehicles, current_time, state):
        # Must be overriden (see ShuttleSimpleDispatcher and
        # ShuttleSimpleNetworkDispatcher for simple examples).
        #
        # Input:
        #   -trips: List of the trips to be optimized.
        #   -vehicles: List of the vehicles to be optimized.
        #   -current_time: Integer equal to the current time of the State.
        #    The value of current_time is defined as follows:
        #       current_time = Environment.current_time
        #       + Optimization.freeze_interval.
        #    Environment.current_time: The time at which the Optimize event is
        #    processed.
        #    freeze_interval: 0, by default, see Optimization.freeze_interval
        #    for more details
        #   -state: An object of type State that corresponds to a partial deep
        #    copy of the environment.
        #
        # Output:
        #   -stops_list_by_vehicle_id:
        #       -Dictionary:
        #           -keys: IDs of the vehicles modified by the optimization.
        #           -values: List of dictionaries that correspond to a stop of
        #            the route associated with the vehicle. Each dictionary has
        #            the following structure:
        #               stop_dict = {
        #                   "stop_id": the label of the stop location,
        #                   "arrival_time": the time at which the vehicle will
        #                       arrive at the stop,
        #                   "departure_time": the time at which the vehicle
        #                                     will leave the stop.
        #               }
        #       -Example:
        #           -key: "1" # The ID of the vehicle
        #           -value:
        #               [
        #                  stop1_dict = {
        #                    "stop_id": "0",
        #                    "arrival_time": None,
        #                       # The arrival time of the first stop of the
        #                       # list does not matter. It will not be modified
        #                       # by the simulator since it is the current stop
        #                       # and cannot be altered.
        #                     "departure_time": current_time
        #                   },
        #                  stop2_dict = {
        #                     "stop_id": "5",
        #                    "arrival_time": current_time + 300
        #                    "departure_time": current_time + 360
        #                  },
        #                  stop3_dict = {
        #                    "stop_id": "2",
        #                    "arrival_time": current_time + 600
        #                    "departure_time": None
        #                       # The departure time of the last stop does not
        #                       # matter. It is set to math.inf.
        #                  }
        #              ]
        #       In this example, a route composed of 3 stops is assigned to the
        #       vehicle with an ID of "1". The locations of the 3 stops are
        #       labelled by "0", "5" and "2", respectively. The vehicle leaves
        #       the first stop at time current_time and arrives at the second
        #       stop at time current_time + 300. In other words, it took the
        #       vehicle 300 seconds to travel from the first stop to the second
        #       stop. Then, the vehicle leaves the second stop at time
        #       current_time + 360, which means that there was a time interval
        #       (e.g., service time) of 60 seconds between the arrival and the
        #       departure. Finally, the vehicle arrives at the third (and last)
        #       stop at time current_time + 600, which corresponds to a travel
        #       time of 240 seconds between the second and the third stop.
        #
        #   -trip_ids_by_vehicle_id:
        #       -Dictionary:
        #           -keys: IDs of the vehicles modified by the optimization.
        #           -values: List of the trip IDs assigned to the vehicle.
        #       -Example:
        #           -key: "1" # The ID of the vehicle
        #           -value: ["3", "4"] # List of IDs of the trips to be served
        #               by the vehicle.
        #           In this example, trips "3" and "4" are assigned to
        #           vehicle "1".

        raise NotImplementedError('optimize of {} not implemented'.
                                  format(self.__class__.__name__))

    def process_output(self, stops_list_by_vehicle_id, trip_ids_by_vehicle_id,
                       state):
        # Create and modify the simulation objects that correspond to the
        # output of the optimize method. In other words, this method
        # "translates" the results of optimization (i.e.,
        # stops_list_by_vehicle_id and trip_ids_by_vehicle_id) into the
        # "language" of the simulator.
        #
        # Input:
        #   -stops_list_by_vehicle_id: the first output of the optimize method
        #    (see optimize above).
        #   -trip_ids_by_vehicle_id: the second output of the optimize method
        #    (see optimize above).
        #   -state: An object of type State that corresponds to a partial deep
        #    copy of the environment.

        modified_trips = []
        modified_vehicles = []

        for vehicle_id, stops_list in stops_list_by_vehicle_id.items():
            vehicle = state.get_vehicle_by_id(vehicle_id)
            route = state.route_by_vehicle_id[vehicle_id]

            trips = [state.get_trip_by_id(trip_id) for trip_id
                     in trip_ids_by_vehicle_id[vehicle_id]]

            current_stop_departure_time = stops_list[0]["departure_time"]
            next_stops = []
            for stop_dict in stops_list[1:]:

                # The departure time of the last stop is set to infinity
                # (because it is unknown).
                departure_time = stop_dict["departure_time"] \
                    if stop_dict != stops_list[-1] else math.inf

                stop = Stop(stop_dict["arrival_time"],
                            departure_time,
                            LabelLocation(stop_dict["stop_id"]))
                next_stops.append(stop)

            self.__update_route_stops(route, current_stop_departure_time,
                                      next_stops)

            self.__assign_legs_vehicle(trips, vehicle, route)

            for trip in trips:
                self.__assign_trip_to_stops(trip, route)

            modified_trips.extend(trips)
            modified_vehicles.append(vehicle)

        return OptimizationResult(state, modified_trips, modified_vehicles)

    def dispatch(self, state):

        trips, vehicles = self.prepare_input(state)

        if len(trips) > 0 and len(vehicles) > 0:
            # The optimize method is called only if there is at least one trip
            # and one vehicle to optimize.
            stops_list_by_vehicle_id, trip_ids_by_vehicle_id = self.optimize(
                trips, vehicles, state.current_time, state)

            optimization_result = self.process_output(stops_list_by_vehicle_id,
                                                      trip_ids_by_vehicle_id,
                                                      state)
        else:
            optimization_result = OptimizationResult(state, [], [])

        return optimization_result

    def __update_route_stops(self, route, current_stop_departure_time,
                             next_stops):

        if route.current_stop is not None:
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

    def __assign_legs_vehicle(self, trips, vehicle, route):
        for trip in trips:
            trip.current_leg.assigned_vehicle = vehicle
            route.assign_leg(trip.current_leg)

    def __assign_trip_to_stops(self, trip, route):
        boarding_stop_found = False
        alighting_stop_found = False

        if route.current_stop is not None:
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

        trip.current_leg.assigned_vehicle = vehicle

        route.assign_leg(trip.current_leg)

        self.__modified_vehicles.append(vehicle)
        self.__modified_trips.append(trip)

    def __assign_trip_to_stops(self, trip, route):

        origin_stop = self.__get_stop_by_stop_id(trip.current_leg.origin.label,
                                                 route)
        destination_stop = self.__get_stop_by_stop_id(
            trip.current_leg.destination.label, route)

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
