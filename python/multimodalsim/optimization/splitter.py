import logging

import networkx as nx

from multimodalsim.simulator.request import Leg
from multimodalsim.simulator.vehicle import LabelLocation

logger = logging.getLogger(__name__)


class Splitter(object):

    def __init__(self):
        pass

    def split(self, request, state):
        raise NotImplementedError('split not implemented')


class OneLegSplitter(Splitter):

    def __init__(self):
        super().__init__()

    def split(self, request, state):
        leg = Leg(request.req_id, request.origin, request.destination, request.nb_passengers, request.ready_time,
                  request.due_time, request.release_time)

        return [leg]


class MultimodalSplitter(Splitter):

    def __init__(self):
        super().__init__()
        self.__request = None
        self.__state = None
        self.__bus_network_graph = None

    def split(self, request, state):

        self.__state = state
        self.__request = request

        self.__create_graph_from_state()

        optimal_legs = []

        potential_source_nodes = self.__find_potential_source_nodes(request)
        potential_target_nodes = self.__find_potential_target_nodes(request)

        logger.debug("potential_source_nodes={}".format(potential_source_nodes))
        logger.debug("potential_target_nodes={}".format(potential_target_nodes))

        if len(potential_source_nodes) != 0 and len(potential_target_nodes) != 0:
            logger.debug("req.req_id={}".format(request.req_id))
            feasible_paths = self.__find_feasible_paths(potential_source_nodes, potential_target_nodes)
            if len(feasible_paths) > 0:
                optimal_path = min(feasible_paths, key=lambda x: x[-1][2])
                logger.debug("optimal_path={}".format(optimal_path))
                optimal_legs = self.__get_legs_from_path(optimal_path)
                logger.debug("optimal_legs={}".format(optimal_legs))

        return optimal_legs

    def __create_graph_from_state(self):

        self.__bus_network_graph = nx.DiGraph()

        for vehicle in self.__state.vehicles:

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

    def __get_legs_from_path(self, path):
        legs = []

        leg_vehicle_id = path[0][1]
        leg_first_stop_id = path[0][0]

        leg_number = 1
        for node in path:
            if node[1] != leg_vehicle_id:
                leg_second_stop_id = node[0]

                leg_id = self.__request.req_id + "_" + str(leg_number)
                leg = Leg(leg_id, LabelLocation(leg_first_stop_id), LabelLocation(leg_second_stop_id),
                          self.__request.nb_passengers, self.__request.ready_time, self.__request.due_time,
                          self.__request.release_time)
                legs.append(leg)

                leg_vehicle_id = node[1]
                leg_first_stop_id = node[0]

                leg_number += 1

        # Last leg
        last_leg_second_stop = path[-1][0]
        leg_id = self.__request.req_id + "_" + str(leg_number)
        last_leg = Leg(leg_id, LabelLocation(leg_first_stop_id), LabelLocation(last_leg_second_stop),
                       self.__request.nb_passengers, self.__request.ready_time, self.__request.due_time,
                       self.__request.release_time)
        legs.append(last_leg)

        return legs
