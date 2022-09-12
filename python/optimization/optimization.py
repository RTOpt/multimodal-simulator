import networkx as nx
import logging
from networkx.algorithms.shortest_paths.generic import shortest_path

from python.simulator.network import get_manhattan_distance
from python.simulator.request import Leg
from python.simulator.status import OptimizationStatus, PassengersStatus
from python.simulator.vehicle import Stop, GPSLocation

logger = logging.getLogger(__name__)


class Optimization(object):

    def __init__(self):
        self.status = OptimizationStatus.IDLE

    def optimize(self, state):
        raise NotImplementedError('optimize not implemented')

    def update_status(self, status):
        self.status = status


class ShuttleOptimization(Optimization):

    def __init__(self):
        super().__init__()

    def optimize(self, state):
        BOARDING_TIME = 1  # Time between arrival_time and departure_time

        logger.info("\n******************\nOPTIMIZE (GreedyOptimization):\n")
        logger.info("current_time={}".format(state.current_time))

        non_assigned_requests = state.get_non_assigned_requests()
        non_assigned_vehicles = state.get_non_assigned_vehicles()

        logger.debug("non_assigned_requests={}".format(list(req.req_id for req in non_assigned_requests)))
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
                non_assigned_vehicles_sorted_by_departure_time = [x for x in non_assigned_vehicles_sorted_by_departure_time
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
                req.assign_vehicle(assigned_vehicle)
                assigned_vehicle.route.assign(req)
                req.update_passenger_status(PassengersStatus.ASSIGNED)

                logger.debug(assigned_vehicle)

                logger.debug("assigned_vehicle={}".format(req.assigned_vehicle.id))
                logger.debug("assigned_requests={}".format(list(req.req_id for req in
                                                                assigned_vehicle.route.assigned_requests)))

                request_vehicle_pairs_list.append((req, assigned_vehicle))
                modified_requests.append(req)
                modified_vehicles.append(assigned_vehicle)

        logger.debug("request_vehicle_pairs_list:")
        for req, veh in request_vehicle_pairs_list:
            logger.debug("---(req_id={},veh_id={})".format(req.req_id, veh.id))

        for req, veh in request_vehicle_pairs_list:
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


class BusOptimization(Optimization):

    def __init__(self):
        super().__init__()
        self.__modified_vehicles = None
        self.__modified_requests = None
        self.__non_assigned_released_requests_list = None
        self.__all_vehicles = None
        self.__state = None

    def optimize(self, state):
        logger.info("\n******************\nOPTIMIZE (BusOptimization):\n")
        logger.info("current_time={}".format(state.current_time))

        self.__state = state
        self.__non_assigned_released_requests_list = state.get_non_assigned_requests()
        self.__all_vehicles = state.vehicles

        self.__create_graph_from_state()

        self.__modified_requests = []
        self.__modified_vehicles = []

        logger.debug("self.__non_assigned_released_requests_list={}".format(self.__non_assigned_released_requests_list))

        for req in self.__non_assigned_released_requests_list:
            print("non_assigned req: {}".format(req.req_id))
            potential_source_nodes = self.__find_potential_source_nodes(req)
            potential_target_nodes = self.__find_potential_target_nodes(req)

            logger.debug("potential_source_nodes={}".format(potential_source_nodes))
            logger.debug("potential_target_nodes={}".format(potential_target_nodes))

            if len(potential_source_nodes) != 0 and len(potential_target_nodes) != 0:
                logger.debug("req.req_id={}".format(req.req_id))
                feasible_paths = self.__find_feasible_paths(potential_source_nodes, potential_target_nodes)
                if len(feasible_paths) > 0:
                    optimal_path = min(feasible_paths, key=lambda x: x[-1][2])
                    logger.debug("optimal_path={}".format(optimal_path))
                    optimal_route = self.__get_route_from_path(optimal_path)
                    logger.debug("optimal_route={}".format(optimal_route))

                    self.__assign_request_to_route(req, optimal_route)
                    self.__assign_request_to_stops(req, optimal_route)

        logger.info("END OPTIMIZE\n*******************")

        # Draw the network.
        # if len(self.__modified_requests) > 0:
        #     logger.debug(self.__bus_network_graph)
        #     import matplotlib.pyplot as plt
        #     pos = nx.spring_layout(self.__bus_network_graph, seed=0)
        #     nx.draw(self.__bus_network_graph, pos, with_labels=True)
        #     labels = nx.get_edge_attributes(self.__bus_network_graph, 'weight')
        #     nx.draw_networkx_edge_labels(self.__bus_network_graph, pos, edge_labels=labels)
        #     plt.show()

        return OptimizationResult(state, self.__modified_requests, self.__modified_vehicles)

    def __create_graph_from_state(self):

        self.__bus_network_graph = nx.DiGraph()

        for vehicle in self.__all_vehicles:

            if vehicle.route.current_stop is not None:
                first_stop = vehicle.route.current_stop
                remaining_stops = vehicle.route.next_stops
            else:
                first_stop = vehicle.route.next_stops[0]
                remaining_stops = vehicle.route.next_stops[1:]

            first_node = (first_stop.location.label, vehicle.id, first_stop.arrival_time, first_stop.departure_time)

            for stop in remaining_stops:
                second_node = (stop.location.label, vehicle.id, stop.arrival_time, stop.departure_time)
                self.__bus_network_graph.add_edge(first_node, second_node, weight=second_node[2] - first_node[2])
                first_node = (stop.location.label, vehicle.id, stop.arrival_time, stop.departure_time)

        for node1 in self.__bus_network_graph.nodes:
            for node2 in self.__bus_network_graph.nodes:
                if node1[0] == node2[0] and node1[1] != node2[1]:
                    # Nodes correspond to same stop but different vehicles
                    if node2[3] > node1[2]:
                        # Departure time of the second node is greater than the arrival time of the first node.
                        # A connection is possible
                        self.__bus_network_graph.add_edge(node1, node2, weight=node2[3] - node1[2])

    def __find_potential_source_nodes(self, request):
        potential_source_nodes = []
        for node in self.__bus_network_graph.nodes():
            if node[0] == request.origin.label and node[3] >= request.ready_time:
                potential_source_nodes.append(node)

        return potential_source_nodes

    def __find_potential_target_nodes(self, request):
        potential_target_nodes = []
        for node in self.__bus_network_graph.nodes():
            if node[0] == request.destination.label and node[2] <= request.due_time:
                potential_target_nodes.append(node)

        return potential_target_nodes

    def __find_feasible_paths(self, potential_source_nodes, potential_target_nodes):
        distance_dict, path_dict = nx.multi_source_dijkstra(self.__bus_network_graph, set(potential_source_nodes))
        feasible_paths = []
        for node, distance in distance_dict.items():
            logger.debug("{}: {}".format(node, distance))
            logger.debug(path_dict[node])
            if node in potential_target_nodes:
                feasible_paths.append(path_dict[node])

        return feasible_paths

    def __get_route_from_path(self, path):
        route = []

        leg_vehicle_id = path[0][1]
        leg_vehicle = self.__state.get_vehicle_by_id(leg_vehicle_id)
        leg_first_stop_id = path[0][0]

        for node in path:
            if node[1] != leg_vehicle_id:
                leg_second_stop_id = node[0]
                route.append((leg_vehicle, leg_first_stop_id, leg_second_stop_id))

                leg_vehicle_id = node[1]
                leg_vehicle = self.__state.get_vehicle_by_id(leg_vehicle_id)
                leg_first_stop_id = node[0]

        # Last leg
        last_leg_second_stop = path[-1][0]
        route.append((leg_vehicle, leg_first_stop_id, last_leg_second_stop))

        return route

    def __assign_request_to_route(self, request, route):

        logger.debug("route={}".format(route))

        first_vehicle = route[0][0]
        request.assign_vehicle(first_vehicle)
        first_vehicle.route.assign(request)

        # self.__modified_vehicles.append(first_vehicle)

        request.next_legs = []
        for route_leg_tuple in route:

            next_vehicle = route_leg_tuple[0]
            next_vehicle.route.assign(request)

            next_leg = Leg(request.req_id, route_leg_tuple[1], route_leg_tuple[2], request.nb_passengers,
                           request.ready_time, request.due_time, request.release_time)
            next_leg.assigned_vehicle = next_vehicle

            request.next_legs.append(next_leg)
            self.__modified_vehicles.append(next_vehicle)

        self.__modified_requests.append(request)
        request.update_passenger_status(PassengersStatus.ASSIGNED)

    def __assign_request_to_stops(self, request, route):
        is_connection = False
        previous_vehicle = None
        vehicle = None
        for route_leg in route:
            stop_id = route_leg[1]
            vehicle = route_leg[0]
            stop = self.__get_stop_by_stop_id(stop_id, vehicle)

            logger.debug("passengers_to_board: {} -> {}".format(request.req_id, vehicle.id))
            stop.passengers_to_board.append(request)
            logger.debug("stop: {}".format(stop))
            if is_connection:
                connection_stop = self.__get_stop_by_stop_id(stop_id, previous_vehicle)
                connection_stop.passengers_to_alight.append(request)
                logger.debug(connection_stop)

            is_connection = True
            previous_vehicle = route_leg[0]

        logger.debug("vehicle.id={} | request.origin.label={} | request.destination.label={}".format(vehicle.id,
                                                                                                request.origin.label,
                                                                                                request.destination.label))
        destination_stop = self.__get_stop_by_stop_id(request.destination.label, vehicle)
        destination_stop.passengers_to_alight.append(request)

    def __get_stop_by_stop_id(self, stop_id, vehicle):
        found_stop = None
        if vehicle.route.current_stop is not None and stop_id == vehicle.route.current_stop.location.label:
            found_stop = vehicle.route.current_stop

        for stop in vehicle.route.next_stops:
            if stop_id == stop.location.label:
                found_stop = stop

        return found_stop


class OptimizationResult(object):

    def __init__(self, state, modified_requests, modified_vehicles):
        self.state = state
        self.modified_requests = modified_requests
        self.modified_vehicles = modified_vehicles


class Splitter(object):
    pass


class Dispatcher(object):
    pass
