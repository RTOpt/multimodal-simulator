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

    def __init__(self, network):
        super().__init__()
        self.__network = network

        # The time difference between the arrival and the departure time (10
        # seconds).
        self.__boarding_time = 10

    def optimize(self, network, non_assigned_requests, vehicles):
        raise NotImplementedError('optimize of {} not implemented'.
                                  format(self.__class__.__name__))

    def dispatch(self, state):
        logger.debug("\n******************\nOPTIMIZE ("
                     "ShuttleGreedyDispatcher):\n")
        logger.debug("current_time={}".format(state.current_time))

        non_assigned_requests = state.non_assigned_trips
        non_assigned_vehicles = state.non_assigned_vehicles

        logger.debug("non_assigned_trips={}"
                     .format(list(req.id for req in non_assigned_requests)))
        logger.debug("non_assigned_vehicles={}"
                     .format(list(veh.id for veh in non_assigned_vehicles)))

        request_vehicle_pairs_list = []
        modified_requests = []
        modified_vehicles = []

        if len(non_assigned_requests) > 0:
            vehicles_with_current_stops = \
                [veh for veh in non_assigned_vehicles if veh.route.current_stop
                 is not None]
            non_assigned_vehicles_sorted_by_departure_time = sorted(
                vehicles_with_current_stops,
                key=lambda x: x.route.current_stop.departure_time)

            potential_non_assigned_requests = non_assigned_requests

            routes, shuttle_dispatcher = self.optimize(
                self.__network, potential_non_assigned_requests,
                non_assigned_vehicles_sorted_by_departure_time)

            for dispatch in shuttle_dispatcher:
                assigned_vehicle = dispatch['vehicle']
                for req in dispatch['assigned_requests']:

                    path = self.__get_path(
                        self.__network,
                        req.origin.gps_coordinates.get_coordinates(),
                        req.destination.gps_coordinates.get_coordinates())

                    # departure_time = \
                    #     assigned_vehicle.route.current_stop.departure_time
                    # TODO: departure_time may not be defined correctly.
                    departure_time = req.ready_time
                    if assigned_vehicle.route.current_stop is not None:
                        assigned_vehicle.route.current_stop.departure_time = departure_time

                    if hasattr(assigned_vehicle.route.current_stop.location,
                               'gps_coordinates'):
                        previous_node = \
                            assigned_vehicle.route.current_stop.location.gps_coordinates
                    else:
                        previous_node = \
                            assigned_vehicle.route.current_stop.location

                    next_stops = []
                    for node in path:
                        if previous_node.get_node_id() != node:
                            distance = \
                                self.__network[previous_node.get_node_id()][
                                    node][
                                    'length']
                            if distance > 0:
                                arrival_time = departure_time + distance
                                departure_time = arrival_time + self.__boarding_time if node != path[-1] else math.inf
                                location = GPSLocation(self.__network.nodes[node]['Node'])

                                stop = Stop(arrival_time, departure_time,
                                            location)
                                next_stops.append(stop)
                                previous_node = self.__network.nodes[node][
                                    'Node']

                    if len(assigned_vehicle.route.next_stops) != 0 and len(
                            next_stops) != 0 \
                            and assigned_vehicle.route.next_stops[
                        -1].location == \
                            next_stops[0].location:
                        assigned_vehicle.route.next_stops.extend(
                            next_stops[1:])
                    else:
                        assigned_vehicle.route.next_stops.extend(next_stops)

                    req.current_leg.assigned_vehicle = assigned_vehicle

                    assigned_vehicle.route.assign_leg(req.current_leg)

                    logger.debug(assigned_vehicle)

                    logger.debug("assigned_vehicle={}".format(
                        req.current_leg.assigned_vehicle.id))
                    logger.debug(
                        "assigned_legs={}".format(list(req.id for req in
                                                       assigned_vehicle.route.assigned_legs)))

                    request_vehicle_pairs_list.append((req, assigned_vehicle))
                    modified_requests.append(req)
                    modified_vehicles.append(assigned_vehicle)

        logger.debug("request_vehicle_pairs_list:")
        for req, veh in request_vehicle_pairs_list:
            logger.debug("---(id={},veh_id={})".format(req.id, veh.id))

        for req, veh in request_vehicle_pairs_list:
            boarding_stop_found = False
            alighting_stop_found = False

            gps_coord = veh.route.current_stop.location.gps_coordinates \
                .get_coordinates()

            if req.origin.gps_coordinates.get_coordinates() == gps_coord:
                veh.route.current_stop.passengers_to_board.append(req)
                boarding_stop_found = True

            for stop in veh.route.next_stops:
                if req.origin.gps_coordinates.get_coordinates() \
                        == stop.location.gps_coordinates.get_coordinates() \
                        and not boarding_stop_found:
                    stop.passengers_to_board.append(req)
                    boarding_stop_found = True
                elif req.destination.gps_coordinates.get_coordinates() == \
                        stop.location.gps_coordinates.get_coordinates() \
                        and boarding_stop_found and not alighting_stop_found:
                    stop.passengers_to_alight.append(req)
                    alighting_stop_found = True

        logger.debug("END OPTIMIZE\n*******************")

        return OptimizationResult(state, modified_requests, modified_vehicles)

    def __find_shortest_path(self, G, o, d):
        path = shortest_path(G, source=o, target=d, weight='length')
        # path_length = path_weight(G, path, weight='length')

        return path

    def __get_path(self, G, node1, node2):
        for node in G.nodes(data=True):
            if (node[1]['pos'][0], node[1]['pos'][1]) == node1:
                origin = node[0]
            if (node[1]['pos'][0], node[1]['pos'][1]) == node2:
                destination = node[0]
        path = self.__find_shortest_path(G, origin, destination)
        # path_cost = get_manhattan_distance(node1, node2)
        return path


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

        # Reinitialize modified_requests and modified_vehicles of Dispatcher.
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
