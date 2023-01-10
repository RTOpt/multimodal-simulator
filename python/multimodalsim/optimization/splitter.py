import logging

import networkx as nx
import pickle

from multimodalsim.simulator.request import Leg
from multimodalsim.simulator.vehicle import LabelLocation

logger = logging.getLogger(__name__)


class Splitter(object):

    def __init__(self):
        pass

    def split(self, trip, state):
        raise NotImplementedError('Splitter.split not implemented')


class OneLegSplitter(Splitter):

    def __init__(self):
        self.__state = None
        self.__accessibility_matrix = None
        super().__init__()

    def split(self, trip, state):
        self.__state = state
        if self.__accessibility_matrix is None:
            self.__create_accessibility_matrix()

        if str(trip.origin) in self.__accessibility_matrix \
                and str(trip.destination) \
                in self.__accessibility_matrix[str(trip.origin)]:
            leg = Leg(trip.id, trip.origin, trip.destination,
                      trip.nb_passengers, trip.release_time, trip.ready_time,
                      trip.due_time, trip)
        else:
            leg = None

        return [leg]

    def __create_accessibility_matrix(self):
        logger.debug("__create_graph_from_state")

        self.__accessibility_matrix = {}

        for vehicle in self.__state.vehicles:

            all_stops = []
            if vehicle.route.current_stop is not None:
                all_stops.append(vehicle.route.current_stop)

            for stop in vehicle.route.next_stops:
                all_stops.append(stop)

            if len(all_stops) > 1:
                for i in range(0, len(all_stops) - 1):
                    for j in range(i + 1, len(all_stops)):
                        origin_location = all_stops[i].location
                        destination_location = all_stops[j].location
                        if str(origin_location) in self.__accessibility_matrix:
                            self.__accessibility_matrix[str(origin_location)][
                                str(destination_location)] = True
                        else:
                            self.__accessibility_matrix[
                                str(origin_location)] = {
                                str(destination_location): True}


class MultimodalSplitter(Splitter):

    def __init__(self, network_graph, available_connections=None,
                 freeze_interval=5):
        super().__init__()
        self.__network_graph = network_graph
        self.__available_connections = available_connections \
            if available_connections is not None else []
        self.__freeze_interval = freeze_interval
        self.__trip = None
        self.__state = None

    def split(self, trip, state):

        self.__state = state
        self.__trip = trip

        optimal_legs = []

        potential_source_nodes = self.__find_potential_source_nodes(trip)
        potential_target_nodes = self.__find_potential_target_nodes(trip)

        logger.debug(
            "potential_source_nodes={}".format(potential_source_nodes))
        logger.debug(
            "potential_target_nodes={}".format(potential_target_nodes))

        if len(potential_source_nodes) != 0 \
                and len(potential_target_nodes) != 0:
            feasible_paths = self.__find_feasible_paths(potential_source_nodes,
                                                        potential_target_nodes)
            if len(feasible_paths) > 0:
                optimal_path = min(feasible_paths, key=lambda x: x[-1][2])
                optimal_legs = self.__get_legs_from_path(optimal_path)

        return optimal_legs

    def __find_potential_source_nodes(self, trip):
        potential_source_nodes = []
        for node in self.__network_graph.nodes():
            if node[0] == trip.origin.label and node[3] >= trip.ready_time:
                potential_source_nodes.append(node)

        return potential_source_nodes

    def __find_potential_target_nodes(self, trip):
        potential_target_nodes = []
        for node in self.__network_graph.nodes():
            if node[0] == trip.destination.label and node[2] <= trip.due_time:
                potential_target_nodes.append(node)

        return potential_target_nodes

    def __find_feasible_paths(self, potential_source_nodes,
                              potential_target_nodes):

        logger.debug("__find_feasible_paths")

        distance_dict, path_dict = nx.multi_source_dijkstra(
            self.__network_graph, set(potential_source_nodes))
        feasible_paths = []
        for node, distance in distance_dict.items():
            if node in potential_target_nodes and self.__check_path_feasibility(path_dict[node]):
                feasible_paths.append(path_dict[node])

        return feasible_paths

    def __check_path_feasibility(self, path):
        path_feasible = True

        min_arrival_time = 0
        for node in path:
            if node[3] - min_arrival_time < self.__freeze_interval:
                path_feasible = False
            if node[2] > min_arrival_time:
                min_arrival_time = node[2]

        return path_feasible

    def __get_legs_from_path(self, path):

        legs = []

        leg_vehicle_id = path[0][1]
        leg_first_stop_id = path[0][0]

        leg_second_stop_id = None
        leg_number = 1
        for node in path:
            if node[1] != leg_vehicle_id:
                leg_id = self.__trip.id + "_" + str(leg_number)
                leg = Leg(leg_id, LabelLocation(leg_first_stop_id),
                          LabelLocation(leg_second_stop_id),
                          self.__trip.nb_passengers, self.__trip.release_time,
                          self.__trip.ready_time, self.__trip.due_time,
                          self.__trip)
                legs.append(leg)

                leg_vehicle_id = node[1]
                leg_first_stop_id = node[0]

                leg_number += 1

            leg_second_stop_id = node[0]

        # Last leg
        last_leg_second_stop = path[-1][0]
        leg_id = self.__trip.id + "_" + str(leg_number)
        last_leg = Leg(leg_id, LabelLocation(leg_first_stop_id),
                       LabelLocation(last_leg_second_stop),
                       self.__trip.nb_passengers, self.__trip.release_time,
                       self.__trip.ready_time, self.__trip.due_time,
                       self.__trip)
        legs.append(last_leg)

        filtered_legs = self.__filter_legs(legs)

        return filtered_legs

    def __filter_legs(self, legs):

        filtered_legs = []
        for leg in legs:
            if str(leg.origin) != str(leg.destination) and \
                    (str(leg.origin) not in self.__available_connections
                     or (str(leg.destination) not in
                         self.__available_connections[str(leg.origin)])):
                filtered_legs.append(leg)

        return filtered_legs
