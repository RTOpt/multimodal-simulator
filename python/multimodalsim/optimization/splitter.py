import logging
from typing import Any, Optional

import networkx as nx

import multimodalsim.simulator.request as request
import multimodalsim.optimization.state as state_module
from multimodalsim.simulator.stop import LabelLocation

logger = logging.getLogger(__name__)


class Splitter:

    def __init__(self) -> None:
        pass

    def split(self, trip: 'request.Trip',
              state: 'state_module.State') -> list['request.Leg']:
        raise NotImplementedError('Splitter.split not implemented')


class OneLegSplitter(Splitter):

    def __init__(self) -> None:
        super().__init__()

    def split(self, trip: 'request.Trip',
              state: 'state_module.State') -> list['request.Leg']:
        leg = request.Leg(trip.id, trip.origin, trip.destination,
                          trip.nb_passengers, trip.release_time,
                          trip.ready_time,
                          trip.due_time, trip)

        return [leg]


class MultimodalSplitter(Splitter):

    def __init__(self, network_graph: Any,
                 available_connections: Optional[dict] = None,
                 freeze_interval: float = 5) -> None:
        super().__init__()
        self.__network_graph = network_graph
        self.__available_connections = available_connections \
            if available_connections is not None else []
        self.__freeze_interval = freeze_interval
        self.__trip = None
        self.__state = None

    def split(self, trip: 'request.Trip',
              state: 'state_module.State') -> list['request.Leg']:

        self.__state = state
        self.__trip = trip

        optimal_legs = []

        potential_source_nodes = self.__find_potential_source_nodes(trip)
        potential_target_nodes = self.__find_potential_target_nodes(trip)

        if len(potential_source_nodes) != 0 \
                and len(potential_target_nodes) != 0:
            feasible_paths = self.__find_feasible_paths(potential_source_nodes,
                                                        potential_target_nodes)
            if len(feasible_paths) > 0:
                optimal_path = min(feasible_paths, key=lambda x: x[-1][2])
                optimal_legs = self.__get_legs_from_path(optimal_path)

        self.__state = None
        self.__trip = None

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
            if node in potential_target_nodes \
                    and self.__check_path_feasibility(path_dict[node]):
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
                leg = request.Leg(leg_id, LabelLocation(leg_first_stop_id),
                                  LabelLocation(leg_second_stop_id),
                                  self.__trip.nb_passengers,
                                  self.__trip.release_time,
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
        last_leg = request.Leg(leg_id, LabelLocation(leg_first_stop_id),
                               LabelLocation(last_leg_second_stop),
                               self.__trip.nb_passengers,
                               self.__trip.release_time,
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
