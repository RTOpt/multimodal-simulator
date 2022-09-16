import logging

from multimodalsim.optimization.optimization import OptimizationResult
from multimodalsim.simulator.network import get_manhattan_distance
from multimodalsim.simulator.status import PassengersStatus
from multimodalsim.simulator.vehicle import Stop
from networkx.algorithms.shortest_paths.generic import shortest_path

logger = logging.getLogger(__name__)


class Dispatcher(object):

    def __init__(self):
        pass

    def dispatch(self, state):
        raise NotImplementedError('dispatch not implemented')


class ShuttleGreedyDispatcher(Dispatcher):

    def __init__(self):
        super().__init__()

    def dispatch(self, state):
        logger.info("\n******************\nOPTIMIZE (ShuttleGreedyDispatcher):\n")
        logger.info("current_time={}".format(state.current_time))

        BOARDING_TIME = 1  # Time between arrival_time and departure_time

        non_assigned_requests = state.get_non_assigned_trips()
        non_assigned_vehicles = state.get_non_assigned_vehicles()

        logger.debug("non_assigned_trips={}".format(list(req.req_id for req in non_assigned_requests)))
        logger.debug("non_assigned_vehicles={}".format(list(veh.id for veh in non_assigned_vehicles)))

        request_vehicle_pairs_list = []
        modified_requests = []
        modified_vehicles = []

        non_assigned_vehicles_sorted_by_departure_time = sorted(non_assigned_vehicles,
                                                                key=lambda x: x.route.current_stop.departure_time)
        for req in non_assigned_requests:
            potential_non_assigned_vehicles = list(x for x in non_assigned_vehicles_sorted_by_departure_time
                                                   if x.route.current_stop.departure_time >= req.ready_time)
            # The passenger must be ready before the departure time.
            logger.debug(
                "potential_non_assigned_vehicles={}".format(list(veh.id for veh in potential_non_assigned_vehicles)))
            if len(potential_non_assigned_vehicles) != 0:

                assigned_vehicle = potential_non_assigned_vehicles.pop(0)
                # Asma : The assigned vehicle must be removed from the non_assigned_vehicles_sorted_by_departure_time
                non_assigned_vehicles_sorted_by_departure_time = [x for x in
                                                                  non_assigned_vehicles_sorted_by_departure_time
                                                                  if not assigned_vehicle.id == x.id]

                path = self.__get_path(state.network, req.origin.gps_coordinates.get_coordinates(),
                                       req.destination.gps_coordinates.get_coordinates())

                req.assign_route(path)
                logger.debug("req.path={}".format(list("(" + str(node.get_coordinates()[0]) + "," +
                                                       str(node.get_coordinates()[1]) + ")" for node in req.path)))

                departure_time = assigned_vehicle.route.current_stop.departure_time
                # previous_node = path[0]

                # Asma : temporary solution - the code should be rearranged to
                if hasattr(assigned_vehicle.route.current_stop.location, 'gps_coordinates'):
                    previous_node = assigned_vehicle.route.current_stop.location.gps_coordinates
                else:
                    previous_node = assigned_vehicle.route.current_stop.location

                next_stops = []
                # OLD CODE : for node in path[1:]:
                for node in path:
                    # First node is excluded because it is the current_stop. Asma not necessarily
                    distance = get_manhattan_distance(previous_node.get_coordinates(), node.get_coordinates())
                    arrival_time = departure_time + distance
                    departure_time = arrival_time + BOARDING_TIME
                    location = node
                    stop = Stop(None, arrival_time, departure_time, location)
                    next_stops.append(stop)
                    previous_node = node

                assigned_vehicle.route.next_stops.extend(next_stops)
                req.current_leg.assign_vehicle(assigned_vehicle)
                assigned_vehicle.route.assign(req)
                req.update_status(PassengersStatus.ASSIGNED)

                logger.debug(assigned_vehicle)

                logger.debug("assigned_vehicle={}".format(req.current_leg.assigned_vehicle.id))
                logger.debug("assigned_trips={}".format(list(req.req_id for req in
                                                             assigned_vehicle.route.assigned_trips)))

                request_vehicle_pairs_list.append((req, assigned_vehicle))
                modified_requests.append(req)
                modified_vehicles.append(assigned_vehicle)

        logger.debug("request_vehicle_pairs_list:")
        for req, veh in request_vehicle_pairs_list:
            logger.debug("---(req_id={},veh_id={})".format(req.req_id, veh.id))

        for req, veh in request_vehicle_pairs_list:
            # MODIFIED (Patrick): The request should be added to the passengers_to_board of the current stop if and only
            # if the request is the origin of the request is the current stop.
            if req.origin.gps_coordinates.get_coordinates() == veh.route.current_stop.location.gps_coordinates:
                veh.route.current_stop.passengers_to_board.append(req)

            for stop in veh.route.next_stops:
                if req.origin.gps_coordinates.get_coordinates() == stop.location.get_coordinates():
                    stop.passengers_to_board.append(req)
                elif req.destination.gps_coordinates.get_coordinates() == stop.location.get_coordinates():
                    stop.passengers_to_alight.append(req)

        logger.info("END OPTIMIZE\n*******************")

        return OptimizationResult(state, modified_requests, modified_vehicles)

    def __find_shortest_path(self, G, o, d):
        path = shortest_path(G, source=o, target=d, weight='length')
        # path_length = path_weight(G, path, weight='length')

        return path

    def __get_path(self, G, node1, node2):
        for node in G.nodes:
            if node.coordinates == node1:
                origin = node
            if node.coordinates == node2:
                destination = node
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

        logger.info("\n******************\nOPTIMIZE (FixedLineDispatcher):\n")
        logger.info("current_time={}".format(state.current_time))

        self.__state = state
        self.__non_assigned_released_requests_list = state.get_non_assigned_trips()

        # Reinitialize modified_requests and modified_vehicles of Dispatcher.
        self.__modified_trips = []
        self.__modified_vehicles = []

        logger.debug("self.__non_assigned_released_requests_list={}".format(self.__non_assigned_released_requests_list))

        for trip in self.__non_assigned_released_requests_list:
            logger.debug("non_assigned trip: {}".format(trip.req_id))

            optimal_vehicle = self.__find_optimal_vehicle_for_leg(trip.current_leg)

            if optimal_vehicle is not None:
                self.__assign_trip_to_vehicle(trip, optimal_vehicle)
                self.__assign_trip_to_stops(trip, optimal_vehicle)

        logger.info("END OPTIMIZE\n*******************")

        return OptimizationResult(state, self.__modified_trips, self.__modified_vehicles)

    def __find_optimal_vehicle_for_leg(self, leg):

        origin_stop_id = leg.origin.label
        destination_stop_id = leg.destination.label

        optimal_vehicle = None
        earliest_arrival_time = None
        for vehicle in self.__state.vehicles:
            arrival_time = self.__get_destination_arrival_time(vehicle, origin_stop_id, destination_stop_id)
            if arrival_time is not None and (earliest_arrival_time is None or arrival_time < earliest_arrival_time):
                earliest_arrival_time = arrival_time
                optimal_vehicle = vehicle

        return optimal_vehicle

    def __get_destination_arrival_time(self, vehicle, origin_stop_id, destination_stop_id):
        origin_stop = self.__get_stop_by_stop_id(origin_stop_id, vehicle)
        destination_stop = self.__get_stop_by_stop_id(destination_stop_id, vehicle)

        destination_arrival_time = None
        if origin_stop is not None and destination_stop is not None \
                and origin_stop.departure_time < destination_stop.arrival_time:
            destination_arrival_time = destination_stop.arrival_time

        return destination_arrival_time

    def __assign_trip_to_vehicle(self, trip, vehicle):

        logger.debug("trip.current_leg={}".format(trip.current_leg))
        logger.debug("trip.next_legs={}".format(trip.next_legs))
        logger.debug("vehicle={}".format(vehicle))

        trip.current_leg.assign_vehicle(vehicle)
        trip.update_status(PassengersStatus.ASSIGNED)

        vehicle.route.assign(trip)

        self.__modified_vehicles.append(vehicle)
        self.__modified_trips.append(trip)

    def __assign_trip_to_stops(self, trip, vehicle):

        logger.debug("vehicle={}".format(vehicle))

        origin_stop = self.__get_stop_by_stop_id(trip.current_leg.origin.label, vehicle)
        destination_stop = self.__get_stop_by_stop_id(trip.current_leg.destination.label, vehicle)

        origin_stop.passengers_to_board.append(trip)
        logger.debug("origin_stop: {}".format(origin_stop))

        destination_stop.passengers_to_alight.append(trip)
        logger.debug("destination_stop: {}".format(destination_stop))

    def __get_stop_by_stop_id(self, stop_id, vehicle):
        found_stop = None
        if vehicle.route.current_stop is not None and stop_id == vehicle.route.current_stop.location.label:
            found_stop = vehicle.route.current_stop

        for stop in vehicle.route.next_stops:
            if stop_id == stop.location.label:
                found_stop = stop

        return found_stop
