from multimodalsim.optimization.optimization import OptimizationResult
from multimodalsim.simulator.vehicle import Stop, LabelLocation

import matplotlib.pyplot as plt
from collections import defaultdict
from operator import itemgetter
import numpy as np
from mip import *
import timeit
from typing import List
import matplotlib
import copy
import os
import networkx as nx
from matplotlib.lines import Line2D

print(matplotlib.__version__)

class Graph_Node:
    """ Class defining the nodes in a graph. 
    Each Node has: 
    - stop_id: the id of the stop
    - ad: "a" if the node is an arrival node, "d" if the node is a departure node
    - time: the time of the node
    - real_time: the real time of the node
    - type: the type of the node. The types are as follows:
            "transfer" if this is a node used to represent outgoing flow to another line
            "puit" if this is a node representing the descending passengers at stop_id. All "puit" nodes are arrival nodes. 
            "source" if this is a node representing the mounting passengers at stop_id. All "source" nodes are eparture nodes.
            "skip" if this is a node used in a skip-stop tactic 
            "normal" if the node is used as a normal node for the bus to pass through (no exogenous flow)
    - flow: the exogenous flow at this node (negative if people are alighting, psotivie if people are mounting)
    - level: the level of the node in the graph.
    - dist: the distance of the node from the source node
    - bus: the bus to which the node belongs (the bus trip_id)
    """
    def __init__(self,
                 stop_id,
                 ad,
                 time = 0,
                 transfer_time=0,
                 type='normal',
                 flow=0,
                 level=-1,
                 dist=0,
                 bus=-1):
        self.__stop_id = stop_id
        self.__type = type
        self.__time = time
        self.__transfer_time = transfer_time
        self.__ad = ad
        self.__flow = flow
        if level == -1:
            self.__level = stop_id
        else:
            self.__level = level
        self.__dist = dist
        self.__bus = bus

    def __eq__(self, other):
        """Overrides the default implementation of =="""
        if isinstance(other, Graph_Node):
            return (self.__stop_id == other.__stop_id and self.__type==other.__type and self.__time==other.__time and self.__transfer_time==other.__transfer_time and self.__ad==other.__ad and self.__flow==other.__flow)
        return False

    def __ne__(self, other):
        """Overrides the default implementation (unnecessary in Python 3)"""
        return not self.__eq__(other)
    
    def __lt__(self, other):
        return((self.__time<=other.__time))

    def __hash__(self):
        return hash((self.__stop_id, self.__type, self.__time, self.__ad, self.__flow))
    
    @property
    def node_stop_id(self):
        return(self.__stop_id)
    
    @property
    def node_time(self):
        return(self.__time)

    @property
    def node_transfer_time(self):
        return(self.__transfer_time)
    
    @property
    def node_arrival_departure(self):
        return(self.__ad)
    
    @property
    def node_type(self):
        return(self.__type)
    
    @property
    def node_flow(self):
        return(self.__flow)
    
    @property
    def node_level(self):
        return(self.__level)
    
    @property
    def node_dist(self):
        return(self.__dist)
    
    @property
    def node_bus(self):
        return(self.__bus)
    
    @node_flow.setter
    def node_flow(self, flow):
        self.__flow = flow

    @node_type.setter
    def node_type(self, type):
        self.__type = type
    
    @node_time.setter
    def node_time(self, time):
        self.__time = time

    @property
    def show_node(self):
        print('***NODE***')
        print("stop id:", self.node_stop_id) 
        print("       time:",self.node_time)
        print("       arrival or dep:", self.node_arrival_departure)
        print("       node type: ", self.node_type)
        print("       exogenous flow: ", self.node_flow)
        print("       level:  ", self.node_level)
        print("       bus:  ", self.node_bus)
        print('***NODE***')

class Graph_Edge:
    """ Class defining the edges in a graph.
    Each Edge has:
    - origin: the origin node of the edge
    - destination: the destination node of the edge
    - weight: the weight of the edge (the time it takes to travel from the origin to the destination)
    - capacity: the capacity of the edge (the maximum number of passengers that can travel from the origin to the destination)
    - sp: indicates if this edge is associated with a speedup tactic
    - ss: indicates if this edge is associated with a skip-stop tactic"""
    def __init__(self, origin: Graph_Node, dest: Graph_Node, weight = 0, capacity = 10000, sp = 0, ss = 0):
        self.__o = origin
        self.__d = dest
        self.__w = weight
        self.__c = capacity
        self.__sp = sp
        self.__ss = ss 
    
    def __eq__(self, other):
        """Overrides the default implementation of =="""
        if isinstance(other, Graph_Edge):
            return (self.__o == other.__o and self.__d == other.__d and self.__w == other.__w and self.__c == other.__c)
        return False

    def __ne__(self, other):
        """Overrides the default implementation (unnecessary in Python 3)"""
        return not self.__eq__(other)
    
    def __hash__(self):
        return hash((self.__o, self.__d, self.__w, self.__sp, self.__ss))
    
    @property
    def origin(self):
        return(self.__o)
    
    @property
    def destination(self):
        return(self.__d)
    @property
    def weight(self):
        return(self.__w)
    
    @property
    def speedup(self):
        return(self.__sp)
    
    @property
    def skip_stop(self):
        return(self.__ss)
    
    @property
    def capacity(self):
        return(self.__c)
    
    @property
    def show_edge(self):
        print('***EDGE***')
        print("origin: stop_id :", self.origin.node_stop_id,
              ", arrival/dparture :", self.origin.node_arrival_departure,
              ", time :", self.origin.node_time,
              ", type :", self.origin.node_type,
              ", flow :", self.origin.node_flow,
              ", level :", self.origin.node_level,
              ", bus :", self.origin.node_bus)
        print("destination: stop_id :", self.destination.node_stop_id,
                ", arrival/dparture :", self.destination.node_arrival_departure,
                ", time :", self.destination.node_time,
                ", type :", self.destination.node_type,
                ", flow :", self.destination.node_flow,
                ", level :", self.destination.node_level,
                ", bus :", self.destination.node_bus)
        print("weight: ", self.weight)
        print("speedup: ", self.speedup, "skip-stop: ", self.skip_stop)
        print('***EDGE***')

class Graph:
    """ Classe définissant la structure des graphes. 
    Un graphe a un nom "name". 
    Un graphe comprend une liste de noeuds "nodes" de la classe Node et une liste d'arcs "edges" de la classe Edge. 
    De plus, chaque graphe a un noeud source "source" et un noeud puit "target" définit dès le départ.
    """
    def __init__(self, name: str, nodes: List[Graph_Node], edges: List[Graph_Edge], source: Graph_Node, target: Graph_Node):
        self.__name = name
        if (source in nodes) == False: 
            nodes.insert(0, source)
        if (target in nodes) == False: 
            nodes.insert(1, target)
        self.__nodes = nodes
        self.__edges = edges
        self.__s = source
        self.__t = target
        self.__time_step = 20
        self.__price = 3600
    @property
    def name(self):
        return self.__name
    
    @property
    def time_step(self):
        return self.__time_step
    
    @time_step.setter
    def time_step(self, time_step):
        self.__time_step = time_step

    @property
    def price(self):
        return self.__price
    
    @price.setter
    def price(self, price):
        self.__price = price

    @property
    def edges(self):
        return(self.__edges)
    
    @property
    def nodes(self):
        return(self.__nodes)
    
    @property
    def source(self):
        return(self.__s)
    
    @property
    def target(self):
        return(self.__t)
    
    @property
    def nb_nodes(self):
        return(len(self.__nodes))
    
    @property
    def nb_edges(self):
        return(len(self.__edges))
    
    def get_node(self, stop_id : int, ad :str, time :int, type: str):
        for node in self.nodes:
            if node.node_stop_id == stop_id and node.node_arrival_departure == ad and node.node_time == time and node.node_type==type:
                return(node)
        return(False)
    
    def contains_node(self, node: Graph_Node):
        return(node in self.nodes)
    
    def add_node(self, node : Graph_Node):
        if self.contains_node(node) == False:
            self.__nodes.append(node)
    
    def remove_node(self, node: Graph_Node):
        if self.contains_node(node):
            self.__nodes.remove(node)

    def contains_edge(self, origin:Graph_Node, dest:Graph_Node, weight: int, sp : int = 0, ss : int = 0):
        edges=[edge for edge in self.edges if edge.origin == origin and edge.destination == dest and edge.weight == weight and edge.speedup == sp and edge.skip_stop == ss]
        if len(edges)>0:
            return(True)
        return(False)
    
    def append_edge(self, edge: Graph_Edge):
        self.__edges.append(edge)

    def add_edge(self, origin : Graph_Node, dest : Graph_Node, weight : int = -1, sp=0, ss = 0):
        if weight == -1:
            if dest == self.target:
                weight = 0
            else:
                weight = dest.node_time - origin.node_time
        if weight >= 0:
            if self.contains_edge(origin, dest, weight, sp = sp, ss = ss) == False: 
                if self.contains_node(origin) == False:
                    print("pb origin not in nodes", origin.show_node)
                    print(self.edges)
                    self.add_node(origin)
                if self.contains_node(dest) == False:
                    print("pb dest not in nodes", dest.show_node)
                    self.add_node(dest)
                    print(self.edges)
                edge = Graph_Edge(origin, dest, weight, sp = sp, ss = ss)
                self.append_edge(edge)
            # else:
                # print('Edge already in graph...')
    
    @property
    def show_graph(self):
        """ This functions shows the graph.
        First we print the source node and the target node.
        Then we print all the nodes in the graph in the order they were added to the graph.
        Then we print all the edges in the graph in the order they were added to the graph.
        """
        print('***GRAPH***')
        print('Source node:')
        self.source.show_node
        print('Target node:')
        self.target.show_node
        print('Nodes:')
        for node in self.nodes:
            node.show_node
        print('Edges:')
        for edge in self.edges:
            edge.show_edge
        print('***GRAPH***')
        
    def add_alighting_transfer_passenger_edge(self, arrival_node, alighting_transfer_node, walking_time = 0, stop_is_skipped = 0):
        alighting_transfer_node_time = alighting_transfer_node.node_time
        arrival_time = arrival_node.node_time + walking_time
        if alighting_transfer_node_time - arrival_time > 0:
            self.add_edge(arrival_node, alighting_transfer_node, alighting_transfer_node_time - arrival_time, ss = stop_is_skipped)
        else: 
            wait_for_next_transfer_bus = alighting_transfer_node_time - arrival_time
            while wait_for_next_transfer_bus <= 0:
                wait_for_next_transfer_bus += alighting_transfer_node.node_transfer_time
            self.add_edge(arrival_node, alighting_transfer_node, wait_for_next_transfer_bus, ss = stop_is_skipped) # if we miss the transfer, the waiting time is equal to the wait to the next available transfer bus
                        
    def add_source_node(self,
                        sources : dict,
                        start_time : int,
                        initial_flow :int,
                        trip_id : str,
                        global_source_node: Graph_Node):
        """
        This function adds a secondary source node to the graph for each trip.
        Inputs:
            - G: the graph
            - sources: dictionary of source nodes
            - start_time: the start time of the bus trip
            - initial_flow: the initial flow of passengers on the bus trip
            - trip_id: the bus trip id
            - global_source_node: the global source node for the graph
        Outputs:
            - G: the updated graph
            - sources: dictionary of source nodes
        """
        source = Graph_Node(0, "d", start_time-1, start_time-1, "normal", initial_flow, 0, -0.05, trip_id)
        self.add_node(source)
        self.add_edge(global_source_node, source, 1) # Add edge from global source to bus source, the weight is non-zero to avoid MIP constraints.
        sources[trip_id] = source
        return sources
    
    def add_target_node(self,
                        target_nodes : dict,
                        od_d_dict : dict,
                        trip_id : str,
                        stop : Stop,
                        start_time : int,
                        l : int,
                        d : int):
        """
        This functions adds a node with negative exogenous flow to the graph.
        Inputs:
            - G: the graph
            - target_nodes: dictionary of target nodes
            - od_d_dict: dictionary of nodes with negative exogenous flow
            - trip_id: the bus trip id
            - stop: the stop at which the target node is created
            - start_time: the start time of the bus trip
            - l: the level of the stop
            - d: the distance of the stop
        Outputs:
            - target_nodes: updated dictionary of target nodes
            - od_d_dict: udpated dictionary of nodes with negative exogenous flow"""
        stop_id = int(stop.location.label)
        target = Graph_Node(stop_id, "a", start_time, start_time, "puit", -stop.passengers_to_alight_int, l, d, trip_id)
        self.add_node(target)
        target_nodes[trip_id][stop_id] = target
        od_d_dict[trip_id].append((stop_id, target))
        return target_nodes, od_d_dict
    
    def create_stops_dict(self,
                          bus_trips: dict,
                          with_tactics = False):
        """
        This function creates a dictionary of stops and their corresponding levels in the graph.
        Inputs:
            - bus_trips: dictionary of bus trips containing the data on the two trips' stops, travel times, dwell times, number of boarding/alighting passengers etc.
            - with_tactics: boolean indicating whether tactics are allowed.
        Outputs:
            - stops_level: dictionary containing the level of each stop in the graph
            - stops_dist: dictionary containing the distance of each stop in the graph
            - targets: dictionary containing the target nodes for each stop
        """
        global_target_node = self.target
        stop_id_and_dist = []
        for trip_id in bus_trips:
            for stop in bus_trips[trip_id]:
                stop_id_and_dist.append((int(stop.location.label), stop.cumulative_distance))
        stop_id_and_dist=np.unique(stop_id_and_dist,axis=0)
        stop_id_and_dist=sorted(stop_id_and_dist, key=itemgetter(1))
        stops_level = {}
        stops_dist = {}
        targets = {}
        level = 1
        for i in range(len(stop_id_and_dist)):
            stop_id = int(stop_id_and_dist[i][0])
            if (stop_id in stops_level) == False:
                stops_level[stop_id] = level
                stops_dist[stop_id] = stop_id_and_dist[i][1]
                target_node_for_level = Graph_Node(stop_id, "d", 0, 0, 'puit', 0, level, stop_id_and_dist[i][1])
                targets[stop_id] = target_node_for_level
                self.add_node(target_node_for_level)
                if with_tactics == False: 
                    self.add_edge(target_node_for_level, global_target_node, 0)
                level += 1
        return stops_level, stops_dist, targets
    
    def get_transfer_data(self,
                      transfers: dict,
                      stops_level: dict,
                      stops_dist: dict,
                      trip_id: str,
                      od_d_dict: dict,
                      od_m: list):
        """
        This function creates transfer nodes and gets transfer data for passengers transferring on the bus trip.
        Inputs:
            - transfers: dictionary containing the transfer data for passengers transferring on the bus trip.
            - stops_level: dictionary containing the level of each stop in the graph.
            - stops_dist: dictionary containing the distance of each stop in the graph.
            - trip_id: the bus trip id
            - od_d_dict: dictionary containing the origins/destinations of each passenger
            - od_m: list containing the number of passengers boarding the bus trip at each stop
            - G: the graph
        Outputs:
            - transfer_nodes: dictionary of transfer nodes for each stop, contains transfer nodes for passenger going to other lines.
            - transfer_passengers: dictionary containing the time and number of passengers arriving from other lines at each stop

        """
        # Create transfer nodes and get transfer data
        transfer_nodes = {} # dict of transfer nodes for each stop, contains transfer nodes for passenger going to other lines.
        transfer_passengers = defaultdict(lambda : defaultdict(dict)) # dict containing the time and number of passengers arriving from other lines at each stop
        level = -1 # level of the stop
        for stop_id in transfers[trip_id]: 
            level = stops_level[stop_id]
            dist = stops_dist[stop_id]
            # Passengers aligting and transfering to other lines
            if len(transfers[trip_id][stop_id]['alighting']) > 0:
                for (time, nbr_passengers, interval) in transfers[trip_id][stop_id]['alighting']:
                    if stop_id not in transfer_nodes:
                        transfer_nodes[stop_id] = []
                    add_flow_to_existing_node = False
                    for i in range(len(transfer_nodes[stop_id])):
                        node = transfer_nodes[stop_id][i]
                        if node.node_time == time:
                            input("We should never be here as transfers for the same bus are aggregated")
                            transfer_nodes[stop_id].remove(node)
                            self.remove_node(node)
                            node.node_flow = node.node_flow - nbr_passengers
                            add_flow_to_existing_node = True
                            od_d_dict[trip_id].append((stop_id, node))
                            transfer_nodes[stop_id].insert(i, node)
                            self.add_node(node)
                            break
                    if add_flow_to_existing_node == False: 
                        transfer_node = Graph_Node(stop_id, "a", time, interval, "transfer", -nbr_passengers, level, dist, trip_id)
                        transfer_nodes[stop_id].append(transfer_node)
                        self.add_node(transfer_node)
                        od_d_dict[trip_id].append((stop_id, transfer_node))

            # Passengers transfering from other lines and boarding main line.
            if len(transfers[trip_id][stop_id]['boarding']) > 0:
                for (time, nbr_passengers, interval) in transfers[trip_id][stop_id]['boarding']:
                    if stop_id not in transfer_passengers: 
                        transfer_passengers[stop_id] = {}
                    transfer_passengers[stop_id][time] = nbr_passengers # all transfer times are unique
                    od_m.append((nbr_passengers, stop_id, time))
        return(transfer_nodes, transfer_passengers, od_d_dict, od_m, level)
    
    def add_speedup_tactic_path(self,
                            stop : Stop,
                            speedup_factor : float,
                            travel_time : int,
                            time_prev : int, 
                            dwell : int,
                            cur_arr: dict,
                            departs_current: dict,
                            target: Graph_Node,
                            prev_node: Graph_Node,
                            l: int,
                            d: float,
                            trip_id: str):
        """
        This function adds a speedup tactic path to the graph.
        Inputs:
            - stop: the stop at which the path is created
            - speedup: the speedup factor
            - travel_time: the travel time between the previous stop and the current stop
            - time_prev: the departure time from the previous stop
            - dwell: the dwell time at the current stop
            - cur_arr: dictionary of arrival nodes
            - departs_current: dictionary of departure nodes
            - target: the target node
            - prev_node: the node at the previous stop from which the path is created
            - l: the level of the stop
            - d: the distance of the stop
            - trip_id: the bus trip id
        Outputs:
            - speedup_path_is_added: boolean indicating whether the speedup tactic path is added
            - cur_arr: updated dictionary of arrival nodes
            - departs_current: updated dictionary of departure nodes
            - speedup_arrival_node: the arrival node with speedup tactic
            - speedup_departure_node: the departure node with speedup tactic"""
        time_step = self.time_step
        speedup_path_is_added = False
        stop_id = int(stop.location.label)
        # print('time_prev', time_prev, 'type', type(time_prev), 'travel_time', travel_time, 'type', type(travel_time), 'speedup_factor', speedup_factor, 'type', type(speedup_factor))
        speedup_arrival_time = int(time_prev + travel_time * speedup_factor)
        speedup_departure_time = (speedup_arrival_time + dwell + time_step - 1)//time_step * time_step

        if speedup_factor == 1 or travel_time <= 30 or speedup_departure_time < stop.planned_arrival_time - 60:
            # Do not a speedup tactic path
            return speedup_path_is_added,  None, cur_arr, departs_current
        
        # Add speedup tactic path
        if speedup_arrival_time in cur_arr:
            speedup_arrival_node = cur_arr[speedup_arrival_time]
        else: 
            speedup_arrival_node = Graph_Node(stop_id, 'a', speedup_arrival_time, 0,'normal', 0, l, d, trip_id)
            self.add_node(speedup_arrival_node)
            self.add_edge(speedup_arrival_node, target, 0) # arc for alighting passengers to reach target node
            cur_arr[speedup_arrival_time] = speedup_arrival_node
        if speedup_departure_time in departs_current: 
            speedup_departure_node = departs_current[speedup_departure_time]
        else:
            speedup_departure_node = Graph_Node(stop_id, "d", speedup_departure_time, 0, "normal", 0, l, d, trip_id)
            self.add_node(speedup_departure_node)
            departs_current[speedup_departure_time] = speedup_departure_node
        self.add_edge(prev_node, speedup_arrival_node, sp = 1) # speedup arc from previous stop current stop 
        self.add_edge(speedup_arrival_node, speedup_departure_node) # dwell time arc at current stop
        speedup_path_is_added = True
        return speedup_path_is_added, speedup_arrival_node, cur_arr, departs_current
    
    def add_no_tactics_path(self,
                            stop : Stop,
                            travel_time : int,
                            time_prev : int,
                            dwell : int,
                            cur_arr: dict,
                            departs_current: dict,
                            target: Graph_Node,
                            prev_node: Graph_Node,
                            l: int,
                            d: float,
                            trip_id: str,
                            sp : int = 0,
                            ss : int = 0):
        """
        This function adds a path without tactics to the graph.
        Inputs:
            - stop: the stop at which the path is created
            - travel_time: the travel time between the previous stop and the current stop
            - time_prev: the departure time from the previous stop
            - dwell: the dwell time at the current stop
            - cur_arr: dictionary of arrival nodes
            - departs_current: dictionary of departure nodes
            - target: the target node
            - prev_node: the previous node
            - l: the level of the stop
            - d: the distance of the stop
            - trip_id: the bus trip id
            - sp: indicates if this edge is associated with a speedup tactic (only when evaluating REGRETS)
            - ss: indicates if this edge is associated with a skip-stop tactic (only when evaluating REGRETS)
        Outputs:
            - no_tactics_arrival_node: the arrival node without tactics
            - no_tactics_departure_node: the departure node without tactics
            """
        stop_id = int(stop.location.label)
        time_step = self.time_step
        arrival_time = time_prev + travel_time  
        if arrival_time in cur_arr:
            no_tactics_arrival_node = cur_arr[arrival_time]
        else: 
            no_tactics_arrival_node = Graph_Node(stop_id,'a', arrival_time, 0, 'normal', 0, l, d, trip_id)
            cur_arr[arrival_time] = no_tactics_arrival_node
            self.add_node(no_tactics_arrival_node)
            self.add_edge(no_tactics_arrival_node, target, 0)
        departure_time = (arrival_time + dwell + time_step-1) //time_step * time_step
        if departure_time in departs_current:
            no_tactics_departure_node = departs_current[departure_time]
        else: 
            no_tactics_departure_node = Graph_Node(stop_id, "d", departure_time, 0, "normal", 0, l, d, trip_id)
            departs_current[departure_time] = no_tactics_departure_node
            self.add_node(no_tactics_departure_node)
        if ss == 1: 
            no_tactics_arrival_node.type = 'skip'
        self.add_edge(no_tactics_arrival_node, no_tactics_departure_node)
        self.add_edge(prev_node, no_tactics_arrival_node, sp=sp, ss=ss)
        return no_tactics_arrival_node, no_tactics_departure_node, cur_arr, departs_current
    
    def add_skip_stop_path(self,
                            stop : Stop,
                            travel_time : int,
                            time_prev : int,
                            last: int,
                            skips: dict,
                            target_nodes: dict,
                            prev_node: Graph_Node,
                            arrival_time: int,
                            walking_time: int,
                            id_in_transfer_passengers: bool,
                            l: int,
                            d: float,
                            trip_id: str,
                            skip_stop_is_allowed: bool):            
        """
        This function adds a skip-stop path to the graph.
        Inputs:
            - stop: the stop at which the path is created
            - travel_time: the travel time between the previous stop and the current stop
            - time_prev: the departure time from the previous stop
            - last: the last stop at which tactics are allowed
            - skips: dictionary of skip-stop nodes
            - target_nodes: dictionary of nodes with negative exogenous flow
            - prev_node: the node from which the path is created
            - arrival_time: the arrival time at the stop
            - walking_time: the time it takes for passengers to walk from the previous/next stop to the skipped stop
            - id_in_transfer_passengers: boolean indicating whether the stop_id is in the transfer passengers
            - l: the level of the stop
            - d: the distance of the stop
            - trip_id: the bus trip id
            - skip_stop_is_allowed: indicates if the skip-stop tactic is allowed"""
        stop_id = int(stop.location.label)
        time_step = self.time_step
        skip_stop_time = (arrival_time + time_step - 1)//time_step*time_step # here arrival and departure time are the same
        if l > last or skip_stop_is_allowed==False or id_in_transfer_passengers or (skip_stop_time <= stop.planned_arrival_time - 60):
            return skips
        
        if skip_stop_time in skips: 
            skip_node = skips[skip_stop_time]
        else:
            skip_node = Graph_Node(stop_id, "d", skip_stop_time, 0, "skip", 0, l, d, trip_id)
            skips[skip_stop_time] = skip_node
            self.add_node(skip_node)
        if skip_stop_time > time_prev:
            # print('skip-stop time > time_prev. Adding edge from previous node to skip node')
            self.add_edge(prev_node, skip_node, ss = 1)
        else:
            # print('skip-stop time <= time_prev. Adding edge from previous node to skip node')
            self.add_edge(prev_node, skip_node, travel_time, ss = 1)
        self.add_edge(skip_node, target_nodes[trip_id][stop_id], walking_time, ss = 1) # for passengers that need to walk to their destination
        return skips

    def add_boarding_transfer_passenger_edges(self, 
                                              stop: Stop,
                                              trip_id: str,
                                              transfer_passengers: dict,
                                              exo_current: dict,
                                              od_m_dict: dict,
                                              planned_departure_node_tmp: Graph_Node,
                                              planned_departure_time: int,
                                              edge_dep_plan: Graph_Edge,
                                              walking_time = 0,
                                              stop_is_skipped = 0,
                                              boarding_without_transfer = False,
                                              l: int = 0,
                                              d: float = 0
                                              ):
        """This function add edges to the graph allowing passengers transferring from other buses to the main line to
        board the bus at the newly created nodes at the current stop.
        
        Inputs:
            - stop: Stop, the stop at which the boarding transfer passengers are boarding
            - trip_id: str, the bus trip id
            - transfer_passengers: dict, the dictionary of transfer passengers
                The format is as follows:
                transfer_passengers[stop_id: int][transfer_time: int] = number of passengers
            - exo_current: dict, the dictionary of exogenous nodes at the current stop
                The format is as follows:
                exo_current[time] = node
            - od_m_dict: dict, the dictionary of OD pairs
                The format is as follows:
                od_m_dict[trip_id] = [(number of passengers, stop, edge), ...]
            - planned_departure_node_tmp: Graph_Node, the planned departure node of the bus with exogenous flow
            - planned_departure_time: int, the planned departure time of the bus at the stop
            - edge_dep_plan: Graph_Edge, the edge from the planned departure node with exogenous flow to the network
            - walking_time: int, the time it takes for passengers to walk from the previous/next stop to the current stop
            - stop_is_skipped: int, indicates if the stop is skipped or not
        Outputs:
            - tmp: list of newly created nodes for the transfer passengers"""
        # Boarding transfer passengers
        stop_id = int(stop.location.label)
        time_step = self.time_step
        tmp = []

        if stop_id not in transfer_passengers:
            return tmp, exo_current, od_m_dict
        
        for transfer_time in transfer_passengers[stop_id]:
            transfer_bus_arrival_time_discrete = (transfer_time + time_step - 1)//time_step * time_step
            # There are two possibilities: transfer happens at the same time as the normal boarding or not
            if transfer_bus_arrival_time_discrete == planned_departure_time and boarding_without_transfer: 
                planned_departure_node_tmp.node_flow = planned_departure_node_tmp.node_flow + transfer_passengers[stop_id][transfer_time]
                planned_departure_node_tmp.node_type = 'transfer'
                od_m_dict[trip_id].append((transfer_passengers[stop_id][transfer_time], stop, edge_dep_plan))
                # print('Adding transfer passengers to planned departure node, adding flow', transfer_passengers[stop_id][transfer_time])
            else: 
                # All transfer times are unique so we only need to check for the planned departure time.
                # Transfer_passengers[stop_id][transfer_time] > 0 for all transfer times
                additional_time = 0 if stop_is_skipped == 0 else walking_time
                transfer_passenger_arrival_time_at_stop = transfer_bus_arrival_time_discrete + additional_time
                edge_weight = 1 if stop_is_skipped == 0 else walking_time
                while (transfer_bus_arrival_time_discrete + walking_time in exo_current)==True:
                    transfer_bus_arrival_time_discrete += 1
                transfer_departure_node = Graph_Node(stop_id, "d", transfer_passenger_arrival_time_at_stop, 0, "transfer", 0, l, d, trip_id)
                transfer_departure_node_tmp = Graph_Node(stop_id, "d", transfer_bus_arrival_time_discrete, 0, "transfer", transfer_passengers[stop_id][transfer_time], l, d, trip_id)
                self.add_node(transfer_departure_node)
                self.add_node(transfer_departure_node_tmp)
                edge_deb = Graph_Edge(transfer_departure_node_tmp, transfer_departure_node, edge_weight, ss = stop_is_skipped)
                self.add_edge(transfer_departure_node_tmp, transfer_departure_node, edge_weight, ss = stop_is_skipped)
                exo_current[transfer_bus_arrival_time_discrete] = transfer_departure_node_tmp
                tmp.append(transfer_departure_node)
                od_m_dict[trip_id].append((transfer_passengers[stop_id][transfer_time], stop, edge_deb)) 
        return tmp, exo_current, od_m_dict
        
    def link_passengers_from_previous_bus(self,
                                          times: list,
                                          stop_id: int,
                                          last_exo: dict,
                                          exo_current: dict,
                                          departs_current: dict,
                                          with_tactics: bool):
        """
        This function links passengers from the previous bus to the current bus.
        If passengers missed the previous bus, a waiting time arc is added to the current bus trip_id.
        Inputs:
            - times: list of all possible passenger ready times and bus departure times
            - stop_id: the stop id
            - last_exo: dictionary of last exogenous nodes
            - exo_current: dictionary of current exogenous nodes
            - departs_current: dictionary of current departure nodes
            - with_tactics: indicates if tactics are allowed
        """
        if stop_id in last_exo:
            for node_exo in last_exo[stop_id]: 
                if node_exo.node_time <= times[0][0]: 
                    self.add_edge(node_exo, times[0][1])
                elif node_exo.node_time > times[-1][0]: # This should not happen, passenger assigned to previous bus arrived after current bus...
                    node_dep = [edge for edge in self.edges if edge.origin == node_exo][0].destination
                    times.append((node_dep.node_time, node_dep))
                    if with_tactics == False:
                        # For the no tactics case, the bus must depart from the no_tactics_departure_node
                        # No need to add these nodes to departs_current as they are after the no_tactics_departure_node
                        exo_current[node_exo.node_time] = node_exo
                    else:
                        # Add node to departs_current as a new possible departure node for the bus
                        while node_dep.node_time in departs_current:
                            node_dep.node_time = node_dep.node_time + 1
                        departs_current[node_dep.node_time] = node_dep
                else: 
                    i = 1
                    node_exo_test = True
                    while i < len(times) and node_exo_test:
                        if node_exo.time<=times[i][0]:
                            self.add_edge(node_exo, times[i][1])
                            node_exo_test = False
                        i+=1
            last_exo.pop(stop_id, None)
        return times, last_exo, exo_current, departs_current
    
    def finalize_graph_for_current_stop_without_tactics(self,
                                                        times: list,
                                                        no_tactics_departure_node: Graph_Node,
                                                        last_exo: dict,
                                                        exo_current: dict,
                                                        stop_id: int,
                                                        start_time: int,
                                                        trip_id: str,
                                                        order: list):
        """
        This function finalizes the graph for the current stop.
        Edges for passengers waiting at the stop are added.
        Edges for bus holding are added for the with tactics case.
        Inputs:
            - times: list of all possible passenger ready times and bus departure times
            - no_tactics_departure_node: the bus departure node without tactics
            - last_exo: dictionary of exogenous nodes form previous bus
            - exo_current: dictionary of exogenous nodes for the current bus (=trip_id)
            - stop_id: the stop id
            - start_time: the start time of the bus trip
            - trip_id: the bus trip id
            - order: list of bus trips with their start times
        Outputs:"""
        for k in range(len(times)-1): # Add waiting time arcs for passengers waiting at the stop
            if times[k][0] < no_tactics_departure_node.node_time: 
                self.add_edge(times[k][1], times[k+1][1]) 
        # Passengers ready after the bus departure will wait for the next bus
        if times[len(times)-1][1] != no_tactics_departure_node or (start_time, trip_id) == order[-1]:
            exogenous_nodes_to_link_to_next_bus = [exo_current[key] for key in exo_current if key >= no_tactics_departure_node.node_time]
            if len(exogenous_nodes_to_link_to_next_bus) > 0:
                last_exo[stop_id] = exogenous_nodes_to_link_to_next_bus
        return last_exo
    
    def finalize_graph_for_current_stop_with_tactics(self,
                                                    times: list,
                                                    no_tactics_departure_node: Graph_Node,
                                                    last_exo: dict,
                                                    exo_current: dict,
                                                    stop_id: int,
                                                    start_time: int,
                                                    trip_id: str,
                                                    order: list,
                                                    skip_stop_is_allowed: bool,
                                                    speedup_factor: int):
        """
        This function finalizes the graph for the current stop for a graph with tactics.
        Inputs:
            - times: list of all possible passenger ready times and bus departure times
            - no_tactics_departure_node: the departure node without tactics
            - last_exo: dictionary of exogenous nodes form previous bus
            - exo_current: dictionary of exogenous nodes for current bus (=trip_id)
            - stop_id: the stop id
            - ss: indicates if the skip-stop tactic is allowed
            - speedup: indicates the speedup factor
        """
        if (start_time, trip_id) == order[-1]:
            last_exo = self.finalize_graph_for_current_stop_without_tactics(times,
                                                                            no_tactics_departure_node,
                                                                            last_exo,
                                                                            exo_current,
                                                                            stop_id,
                                                                            start_time,
                                                                            trip_id,
                                                                            order)
            return last_exo
        
        for k in range(len(times)-1): # Finalize the graph for this bus stop
            self.add_edge(times[k][1], times[k+1][1])
        if skip_stop_is_allowed == False and speedup_factor == 1: # Only hold tactic is allowed
            nodes_to_link_to_next_bus = [exo_current[key] for key in exo_current if key >= no_tactics_departure_node.node_time] # any earlier departures are impossible
        else: 
            nodes_to_link_to_next_bus = [exo_current[key] for key in exo_current]
        if len(nodes_to_link_to_next_bus) > 0:
            last_exo[stop_id] = nodes_to_link_to_next_bus
        return last_exo
    
    def finalize_graph_for_current_bus_trip(self,
                                            stop_id: int,
                                            times: list,
                                            exo_current: dict,
                                            last_exo: dict,
                                            skips: dict,
                                            global_target_node: Graph_Node,
                                            targets: dict,
                                            price: int,
                                            start_time: int,
                                            trip_id: str,
                                            order: list):
        """
        This function finalizes the graph for the current bus trip.
        Inputs:
            - stop_id: the stop id
            - times: list of all possible passenger ready times and bus departure times
            - exo_current: dictionary of exogenous nodes for the current bus (=trip_id)
            - last_exo: dictionary of exogenous nodes form previous bus
            - skips: dictionary of skip-stop nodes (= {} for graphs without tactics)
            - global_target_node: global target node for the graph
            - targets: dictionary of targets for each level
            - price: the cost of not getting a bus in this control horizon
            - start_time: the start time of the current bus trip
            - trip_id: the bus trip id
            - order: list of bus trips with their start times"""
        for k in range(len(times)):
            self.add_edge(times[k][1], global_target_node, 0)
        for time in skips:
            self.add_edge(skips[time], global_target_node, 0)
        for node_exo in exo_current: 
            self.add_edge(exo_current[node_exo], global_target_node, 0)
        if (start_time, trip_id) == order[-1]:
            for id in last_exo: 
                target_niveau = targets[id]
                for node_exo in last_exo[id]:
                    if node_exo.node_bus == str(trip_id):
                        self.add_edge(node_exo, target_niveau, price)
        return

    def convert_graph_to_model_format(self):
        """Converts the graph G into a format that can be used by the optimization solver.
        Inputs:
            - G: Graph, the graph to convert
        Outputs:
            - Vnew: set of all nodes (each node is a number 1,2,3 ...)
            - Anew: set of all arcs
            - snew: source node
            - tnew: target node
            - flows: exogenous flow at each node. example: flows[6]=+2
            - ids: a dictionary that for each node gives its stop_id. example: ids[6]=46884
            - node_dict: a dictionary that for each node number gives the corresponding Graph_Node object
            - edge_dict: a dictionary that for each edge number gives the corresponding Graph_Edge object
            - bus_dict: a dictionary that for each node number gives its bus trip_id. example: bus_dict[6]='2546781'
         """
        # print('Converting graph to model format')
        V = self.nodes
        A = self.edges
        s = self.source
        t = self.target

        #create new vertices
        Vnew = {}
        flows = {}
        i = 0
        ids = {}
        node_dict = {}
        edge_dict = {}
        bus = {}
        sources = {}
        puits = {}
        puits['t'] = {}
        puits['n'] = {}
        for v in V: 
            Vnew[v] = i
            node_dict[i] = v
            stop_id = v.node_stop_id
            ids[i] = stop_id
            bus[i] = v.node_bus
            if stop_id == 0 and v.node_bus !=- 1:
                sources[v.node_bus] = v.node_time
            if v.node_type == 'puit' and v.node_arrival_departure=='a': #target node for non-transfer passengers
                if v.node_bus not in puits['n']:
                    puits['n'][v.node_bus] = []
                puits['n'][v.node_bus].append(i)
            if v.node_type == 'transfer' and v.node_flow < 0: # node with alighting transfer passengers, called 'transfer target nodes'
                if v.node_bus not in puits['t']:
                    puits['t'][v.node_bus] = []
                puits['t'][v.node_bus].append(i)
            if v != t:
                flows[i] = v.node_flow
            i+=1
        Anew = set()
        for edge in A:
            u = edge.origin
            v = edge.destination
            j = edge.weight
            edge_dict[(u, v, j)] = edge
            Anew.add((Vnew[u], Vnew[v], j))
        snew = Vnew[s]
        tnew = Vnew[t]
        Vnewset = set([Vnew[v] for v in V])
        return(Vnewset, Anew, snew, tnew, flows, ids, node_dict, edge_dict, bus)
    
    def build_and_solve_model_from_graph(self,
                                     name,
                                     verbose = True,
                                     out_of_bus_price = 1,
                                     savepath = 'output',
                                     keys = {},
                                     sources = {},
                                     puits = {},
                                     extras = {}):

        """ 
        Function that takes a graph, information on buses and Origin/Destination pairs and returns the optimal solution of the arc-flow model.

        Inputs:
            - name: instance name
            - verbose: boolean, if True, the function prints the optimal value and the flows
            - out_of_bus_price: out of bus waiting time cost 'as perceived by passengers'.
            - savepath: directory where to save the arc-flow model (optional)
            - keys: dict that for each node with negative exogenous flow returns a list of edges. These are the edges passengers use to board the bus.
            If the flow on such an edge is 0, that means the passenger did not board the current bus. The alighting flow of the node must be ajusted accordingly.
            - sources: dict that for each trip_id returns the departure time at the origin of the trip
            - puits: dict that for each bus trip returns the nodes with negative exogenous flows (alighting nodes)
            - extras: dict that contains additional information (optional)
        Outputs:
            - optimal_value: int, the optimal value of the objective function of the arc-flow model
            #- flow: dict, the passenger flows on each edge
            - bus_flows: dict, the bus flows on each edge
            - display_flows: dict, the passenger flow on each edge, used in the display_graph function.
            - runtime: float, the runtime of the optimization model
        """
        print('Converting graph to model format')
        V, A, s, t, flows, ids, node_dict, edge_dict, bus_dict = self.convert_graph_to_model_format()
        print('Creating optimization model')
        m = Graph.create_opt_model_from_graph_with_mip(V, A, s, t, flows, ids, name,
                                                        bus_dict, 
                                                        savepath=savepath,
                                                        out_of_bus_price=out_of_bus_price,
                                                        keys=keys,
                                                        sources=sources,
                                                        puits=puits,
                                                        extras=extras)
        m.store_search_progress_log = False

        #Solve
        runtime = timeit.default_timer()
        print('Solving optimization model')
        m.optimize() 
        runtime = timeit.default_timer()-runtime
        gap = m.gap
        print('Optimality GAP = ',gap)

        #Get results 
        # passenger_flows = {}
        bus_flows = {}
        display_flows = {}
        indicator_flows = {}
        for (u1,v1,i) in A:
            x = m.vars['x({},{},{})'.format(u1,v1,i)]
            y = m.vars['y({},{},{})'.format(u1,v1,i)]
            u = node_dict[u1]
            v = node_dict[v1]
            # unew = (str)(u.node_stop_id)+' '+u.node_arrival_departure+' '+u.node_type+' '+(str)(u.node_time)
            # vnew = (str)(v.node_stop_id())+' '+v.node_arrival_departure+' '+v.node_type+' '+(str)(v.node_time)
            # print('Edge (',u1,',',v1,',',i,')', 'x=',x.x, 'y=',y.x)
            display_flows[edge_dict[(u,v,i)]] = round(x.x)
            # passenger_flows[(unew, vnew, i)] = (int)(x.x)
            bus_flows[edge_dict[(u,v,i)]]=round(y.x)

        optimal_value = m.objective_value
        if verbose: 
            print("Noeuds: ", len(V) + 1)
            print("Arcs: ", len(A))
            print("valeur optimale: ", optimal_value)
            # print("flots:", flow)
        # return(optimal_value, flow, display_flows, bus_flows, runtime)
        return(optimal_value, bus_flows, display_flows, runtime)

    @staticmethod    
    def get_all_passenger_ready_times_and_bus_departure_times(times,
                                                            departs_current: dict,
                                                            boarding_without_transfer: bool,
                                                            planned_departure_time: int,
                                                            planned_departure_node: Graph_Node):
        """
        This function returns, sorted, all possible passenger ready times and bus departure times for the bus from the current bus stop.
        Inputs:
            - times: list of all possible passenger ready times and bus departure times
            - departs_current: dictionary of bus departure times
            - boarding_without_transfer: boolean indicating whether passengers are boarding without a transfer
            - planned_departure_time: the planned departure time of the bus
            - planned_departure_node: the planned departure node of the bus
            - planned_departure_time_in_departs_current: boolean indicating whether the planned departure time is in departs_current"""
        for time in departs_current:
            times.append((time, departs_current[time]))
        if boarding_without_transfer and (planned_departure_time in departs_current) == False:
            times.append((planned_departure_time, planned_departure_node))
        times = sorted(times, key=itemgetter(0))
        return times
    
    @staticmethod
    def get_last_stop(last_stop, level, stops_level):
        """Returns the stop level of the last stop at which tactics are allowed."""
        if last_stop == 0:
            last = level
        elif last_stop == -1:
            last = 0
        else: 
            last = stops_level[int(last_stop)]
        return(last)
    
    @staticmethod
    def initialize_graph_and_parameters(first_trip_id : str,
                                        bus_trips : dict, 
                                        transfers : dict,
                                        last_departure_times : dict,
                                        price = 3600,
                                        time_step = 20):
        """
        This function creates the source and target nodes for the graph and initializes the parameters for the optimization.
        Inputs:
            - first_trip_id: trip_id of the earliest considered bus (this is the bus to which tactics will be applied)
            - bus_trips: dictionary of bus trips containing the data on the two trips' stops, travel times, dwell times, number of boarding/alighting passengers etc.
            - transfers: dictionary containing the transfer data for passengers transferring on the two bus trips: transfer time, number of transfers, stops, etc.
                The format of the transfers dictionary is as follows:
                transfers[trip_id][stop_id]['boarding'/'alighting'] = [(transfer_time : int, nbr_passengers : int, interval), ...]
            - last_departure_times: dictionary containing the previous bus trip's arrival time at the stops. 
                The format of the last_departure_times dictionary is as follows:
                last_departure_times[trip_id] = int
            - price: cost of a passenger missing their bus (not equal to the bus interval!!!)
        Outputs:
            - G: the constructed graph
            - order: the order of the bus trips
            - price: the cost of a passenger missing their bus
            - global_source_node: the source node for the graph
            - global_target_node: the target node for the graph
        """
        order = []
        order.append((last_departure_times[first_trip_id], first_trip_id))
        second_bus = [trip_id for trip_id in bus_trips if trip_id != first_trip_id][0]
        order.append( (last_departure_times[second_bus], second_bus))
        time_min = min(order[0][0], order[1][0])
        last_stop_second_bus = bus_trips[second_bus][-1]

        # print('*** BUS TRIPS ***')
        # for trip_id in bus_trips: 
        #     print('trip_id', trip_id)
        #     for stop in bus_trips[trip_id]:
        #         print('stop', stop.location.label, 'arrival time', stop.arrival_time, 'departure time', stop.departure_time, )
        # print('*** BUS TRIPS ***')

        time_max = 100 + max( [last_stop_second_bus.departure_time]+[time for (time, nbr_passengers, interval) in transfers[second_bus][int(last_stop_second_bus.location.label)]['boarding'] + transfers[second_bus][int(last_stop_second_bus.location.label)]['alighting']])
        if time_max - time_min > price: 
            price = time_max - time_min
        global_source_node = Graph_Node(-1, "d", order[0][0]-2, order[0][0]-2, "normal", 0, 0, -0.1) # General source node for all buses. Need a non-zero time difference between source nodes to avoid MIP constraints.
        global_target_node = Graph_Node(0, "a", 0, 0, "normal", 0)
        G = Graph('G', [], [], global_source_node, global_target_node)
        G.price = price
        G.time_step = time_step
        return G, order, price, global_source_node, global_target_node

    @staticmethod
    def build_graph_with_tactics(first_trip_id:str,
                                 bus_trips: dict, 
                                transfers: dict,
                                last_departure_times: dict,
                                initial_flows: dict,
                                time_step: int = 20,
                                price: int = 3600,
                                global_speedup_factor = 1,
                                global_skip_stop_is_allowed : bool = False,
                                od_dict : dict = {},
                                simu: bool = False,
                                last_stop = 0):
        """
        This function takes as input the data on two consecutive bus trips on the same line and returns a graph on which a flow optimization must be performed.
        The constructed graph integrates hold, speedup and skip-stop tactics when possible.
        Inputs: 
            - first_trip_id: trip id of the earliest considered trip (this is the trip we apply tactics to)
            - bus_trips: dictionary of bus trips containing the data on the two trips' stops, travel times, dwell times, number of boarding/alighting passengers etc.
            - transfers: dictionary containing the transfer data for passengers transferring on the two bus trips: transfer time, number of transfers, stops, etc.
                The format of the transfers dictionary is as follows:
                transfers[trip_id][stop_id]['boarding'/'alighting'] = [(transfer_time : int, nbr_passengers : int, interval : int), ...]
            - initial_flows: dictionary containing the initial flow of passengers on the two bus trips.
                The format of the initial_flows dictionary is as follows:
                initial_flows[trip_id] = int
            - time_step: time step for the optimization
            - price: cost of a passenger missing their bus (not equal to the bus interval!!!)
            - speedup_gen: acceleration factor for trips between stops
            - ss_gen: boolean indicating whether the skip-stop tactic is allowed
            - od_dict: dictionary containing the origins/destinations of each passenger
            - simu: boolean indicating whether we are in a simulation or not (if yes, we do not apply Skip-Stop, Speedup or Hold tactics to the second bus).
            - last_stop: the last stop at which tactics are allowed.
        Outputs:
            - G: the constructed graph
            """
        if time_step<2 and global_skip_stop_is_allowed: 
            return
        
        G, order, price, global_source_node, global_target_node = Graph.initialize_graph_and_parameters(first_trip_id = first_trip_id,
                                                                                                        bus_trips = bus_trips,
                                                                                                        transfers = transfers,
                                                                                                        last_departure_times = last_departure_times,
                                                                                                        price = price,
                                                                                                        time_step = time_step)

        # Create a dict with all stops in the two bus trips
        stops_level, stops_dist, targets = G.create_stops_dict(bus_trips,
                                                               with_tactics = False)

        # Initialize variables
        sources = {}
        last_exo = {}
        od_m_dict = {}
        od_d_dict = {}
        target_nodes = {}

        # print('First bus : ', order[0][1], ' Second bus: ', order[-1][1])
        # Create nodes and edges for each bus trip
        for (start_time, trip_id) in order:
            print('Building graph for bus trip', trip_id)
            if (start_time, trip_id) != order[0]:
                with_tactics = False
            else:
                with_tactics = True
            # Initialize dictionaries stocking data for the bus trip
            od_m_dict[trip_id] = []
            od_m = []
            od_d_dict[trip_id] = []
            target_nodes[trip_id] = {}
            skip_stop_is_allowed = global_skip_stop_is_allowed
            speedup_factor = global_speedup_factor
            sources = G.add_source_node(sources, start_time, initial_flows[trip_id], trip_id, global_source_node)

            # Create transfer nodes and get transfer data
            print('Creating transfer nodes and getting transfer data')
            transfer_nodes, transfer_passengers, od_d_dict, od_m, level = G.get_transfer_data(transfers,
                                                                                            stops_level,
                                                                                            stops_dist,
                                                                                            trip_id,
                                                                                            od_d_dict,
                                                                                            od_m)

            print('Done creating transfer nodes and getting transfer data')
            # Decide last stop at which tactics are allowed
            last = Graph.get_last_stop(last_stop, level, stops_level)

            # Initialize dicts
            departs_prev = {}
            departs_prev[sources[trip_id].node_time] = sources[trip_id]
            prev_departure_time = last_departure_times[trip_id]

            # Create nodes and edges at each stop
            for j in range(len(bus_trips[trip_id])):
                # Initialize variables
                departs_current = {}
                skips = {}
                exo_current = {}
                stop = bus_trips[trip_id][j]
                stop_id = int(stop.location.label)
                l = stops_level[stop_id]
                d = stop.cumulative_distance
                if l > last:
                    speedup_factor = 1
                    skip_stop_is_allowed = False
                travel_time = max(1, stop.arrival_time - prev_departure_time) #dwell at previous stop. We need the dwell time to be non-null for the constraints in the MIP solver.
                dwell = stop.departure_time - stop.arrival_time
                prev_departure_time = stop.departure_time

                # Add target node and the flow corresponding to passengers alighting at this stop without a transfer
                target_nodes, od_d_dict = G.add_target_node(target_nodes, od_d_dict, trip_id, stop, start_time, l, d)

                # In this modelization we want to separate transfers and normal alighting passengers
                #  *** TRANSFER PASSENGERS ARE NOT INCLUDED IN THE NUMBER OF ALIGHTING PASSENGERS ***
                # ***
                # if stop_id in transfer_nodes: 
                #     for node in transfer_nodes[stop_id]:
                #         target.flow += -node.get_node_flow()
                # *** 

                # Add all possible paths from previous stop to current stop, given the current existing paths
                for node_time in departs_prev:
                    cur_arr = {}
                    prev_node = departs_prev[node_time]
                    time_prev = prev_node.node_time

                    # Add bus path using the speedup tactic
                    speedup_path_is_added, speedup_arrival_node, cur_arr, departs_current = G.add_speedup_tactic_path(stop,
                                                                                                                    speedup_factor,
                                                                                                                    travel_time,
                                                                                                                    time_prev,
                                                                                                                    dwell,
                                                                                                                    cur_arr,
                                                                                                                    departs_current,
                                                                                                                    target_nodes[trip_id][stop_id],
                                                                                                                    prev_node, l, d, trip_id)
                    # Add bus path without tactics
                    no_tactics_arrival_node, no_tactics_departure_node, cur_arr, departs_current = G.add_no_tactics_path(stop, travel_time, time_prev, dwell, cur_arr, departs_current, target_nodes[trip_id][stop_id], prev_node, l, d, trip_id)

                    # Add path for alighting passengers with transfers
                    walking_time = int(max(0, (d-prev_node.node_dist)/4 * 3600 - travel_time))
                    if stop_id in transfer_nodes:
                        for alighting_transfer_node in transfer_nodes[stop_id]:
                            # Link to bus path using speedup tactic
                            if speedup_path_is_added: #there is a speedup tactic
                                G.add_alighting_transfer_passenger_edge(speedup_arrival_node, alighting_transfer_node)
                            # Link to bus path without tactics
                            G.add_alighting_transfer_passenger_edge(no_tactics_arrival_node, alighting_transfer_node)
                            # If stop is skipped, the passengers cannot alight here.
                    # Add bus path using the skip-stop tactic
                    else: 
                        skips = G.add_skip_stop_path(stop, travel_time, time_prev, last, skips, target_nodes, prev_node, no_tactics_arrival_node.node_time, walking_time, (stop_id in transfer_passengers), l, d, trip_id, skip_stop_is_allowed = skip_stop_is_allowed)
                # All bus paths are added

                # Add paths for passengers boarding without a transfer
                min_departure_time = min([time for time in departs_current])
                planned_departure_time = stop.planned_arrival_time - 60
                boarding_without_transfer = False
                if stop.passengers_to_board_int > 0:
                    boarding_without_transfer = True
                    planned_departure_node_tmp = Graph_Node(stop_id, "d", planned_departure_time, 0, "normal", stop.passengers_to_board_int, l, d, trip_id)
                    if planned_departure_time in departs_current:
                        print('Plannned departure time already in departs_current')
                        planned_departure_node = departs_current[planned_departure_time]
                    else: 
                        planned_departure_node = Graph_Node(stop_id, "d", planned_departure_time, 0, "normal", 0, l, d, trip_id)
                        G.add_node(planned_departure_node)
                        if planned_departure_time > min_departure_time and with_tactics:
                            departs_current[planned_departure_time] = planned_departure_node
                    G.add_node(planned_departure_node_tmp)
                    edge_dep_plan = Graph_Edge(planned_departure_node_tmp, planned_departure_node, 1)
                    G.add_edge(planned_departure_node_tmp, planned_departure_node, 1)
                    exo_current[planned_departure_time] = planned_departure_node_tmp
                    od_m_dict[trip_id].append((stop.passengers_to_board_int, stop, edge_dep_plan))
                    for skip_node in skips:
                        skip_edge_is_possible = (skips[skip_node].node_time-(walking_time + planned_departure_time))>0 # there is enough time for passengers to walk from the previous stop to the skipped stop
                        if skip_edge_is_possible:
                            G.add_edge(planned_departure_node, skips[skip_node], skips[skip_node].node_time-planned_departure_time, ss = 1)
                else:
                    planned_departure_node_tmp = -1
                    edge_dep_plan = -1
                    planned_departure_node = -1
                # Add paths for passengers boarding with a transfer
                new_transfer_nodes, exo_current, od_m_dict = G.add_boarding_transfer_passenger_edges(stop, trip_id,
                                                                                                    transfer_passengers,
                                                                                                    exo_current,
                                                                                                    od_m_dict,
                                                                                                    planned_departure_node_tmp,
                                                                                                    planned_departure_time,
                                                                                                    edge_dep_plan,
                                                                                                    walking_time = 0,
                                                                                                    stop_is_skipped = 0,
                                                                                                    boarding_without_transfer = boarding_without_transfer,
                                                                                                    l = l,
                                                                                                    d = d)
                # All bus and passenger paths have been added 

                times = G.create_possible_departures_list(stop_id,
                                                         transfer_passengers,
                                                         new_transfer_nodes,
                                                         min_departure_time,
                                                         departs_current,
                                                         with_tactics = with_tactics)
                
                # Get all possible passenger ready times and bus departure times for the current stop
                times = Graph.get_all_passenger_ready_times_and_bus_departure_times(times,
                                                                                    departs_current,
                                                                                    boarding_without_transfer,
                                                                                    planned_departure_time,
                                                                                    planned_departure_node)
                for time in skips: 
                    if (time in departs_current) == False:
                        departs_current[time] = skips[time]
                    elif (time+1 in departs_current) == False:
                        departs_current[time+1] = skips[time]
                    else:
                        input('how rare is this?')

                # Add paths for passengers who missed the previous bus
                times, last_exo, exo_current, departs_current = G.link_passengers_from_previous_bus(times, stop_id, last_exo, exo_current, departs_current, with_tactics = with_tactics)

                if j != len(bus_trips[trip_id])-1:
                    last_exo = G.finalize_graph_for_current_stop_with_tactics(times,
                                                                            no_tactics_departure_node,
                                                                            last_exo,
                                                                            exo_current,
                                                                            stop_id,
                                                                            start_time,
                                                                            trip_id,
                                                                            order,
                                                                            skip_stop_is_allowed,
                                                                            speedup_factor)
                else:
                    G.finalize_graph_for_current_bus_trip(stop_id, times, exo_current, last_exo, skips, global_target_node, targets, price, start_time, trip_id, order)
                departs_prev = departs_current
            if simu:
                global_skip_stop_is_allowed = False
                global_speedup_factor = 1
        print('Graph built')
        return(G)

    @staticmethod
    def build_graph_without_tactics(first_trip_id : str,
                                    bus_trips: dict, 
                                    transfers: dict,
                                    last_departure_times: dict,
                                    initial_flows: dict,
                                    time_step = 20,
                                    price = 3600,
                                    od_dict = {}):
        """
        This function takes as input the data on two consecutive bus trips on the same line and returns a graph on which a flow optimization must be performed.
        The graph does not include any tactics.
        Inputs: 
            - first_trip_id: the trip id of the earliest considered bus.
            - bus_trips: dictionary of bus trips containing the data on the two trips' stops, travel times, dwell times, number of boarding/alighting passengers etc.
            - transfers: dictionary containing the transfer data for passengers transferring on the two bus trips: transfer time, number of transfers, stops, etc.
                The format of the transfers dictionary is as follows:
                transfers[trip_id][stop_id]['boarding'/'alighting'] = [(transfer_time : int, nbr_passengers : int, interval : int), ...]
            - initial_flows: dictionary containing the initial flow of passengers on the two bus trips.
                The format of the initial_flows dictionary is as follows:
                initial_flows[trip_id] = int
            - time_step: time step for the optimization
            - price: cost of a passenger missing their bus (not equal to the bus interval!!!)
            - od_dict: dictionary containing the origins/destinations of each passenger
            - simu: boolean indicating whether we are in a simulation or not (if yes, we do not apply Skip-Stop, Speedup or Hold tactics to the second bus).
        Outputs:
            - G: the constructed graph
            """
        
        G, order, price, global_source_node, global_target_node = Graph.initialize_graph_and_parameters(first_trip_id = first_trip_id,
                                                                                                        bus_trips = bus_trips,
                                                                                                        transfers = transfers,
                                                                                                        last_departure_times = last_departure_times,
                                                                                                        price = price,
                                                                                                        time_step = time_step)
        stops_level, stops_dist, targets = G.create_stops_dict(bus_trips,
                                                               with_tactics = False)
        # Initialize variables
        sources = {}
        last_exo = {}
        od_m_dict = {}
        od_d_dict = {}
        target_nodes = {}
        prev_transfers = []
        bus_departures = {}

        # Create nodes and edges for each bus trip
        for (start_time, trip_id) in order:

            # Initialize dictionaries stocking data for the bus trip
            od_m_dict[trip_id] = []
            od_m = []
            od_d_dict[trip_id] = []
            target_nodes[trip_id] = {}
            bus_departures[trip_id] = {}
            sources = G.add_source_node(sources, start_time, initial_flows[trip_id], trip_id, global_source_node)

            # Create transfer nodes and get transfer data
            transfer_nodes, transfer_passengers, od_d_dict, od_m, level = G.get_transfer_data(transfers,
                                                                                            stops_level,
                                                                                            stops_dist,
                                                                                            trip_id,
                                                                                            od_d_dict,
                                                                                            od_m)
            # Get missed transfers from previous bus
            extras = []
            # if prev_transfers != [] and od_dict != {}:
            #     for (stop_id, transfer_node) in [(stop, transfer_node) for (stop, transfer_node) in prev_transfers if transfer_node.get_node_flow() <0]:
            #         l = stops_level[stop_id]
            #         d = stops_dist[stop_id]
            #         # Transfer passengers from main line towards other lines (alighting transfers)
            #         time = transfer_node.get_node_time() + 10 # 10 seconds of dwell time
            #         hp = stop.planned_arrival_time
            #         while time < hp - 60: 
            #             time += get_passage_cost(p)
            #         if (stop_id in transfer_nodes) == False:
            #             transfer_nodes[stop_id] = []
            #         times = [node.get_node_time() for node in transfer_nodes[stop_id]]
            #         while (time in times) == True: 
            #             time += 1
            #         transfer_node = Graph_Node(stop_id, "a", time, get_passage_cost(p),"transfer", 0, l, d, trip_id)
            #         transfer_nodes[stop_id].append(transfer_node)
            #         G.add_node(transfer_node)
            #         extras.append((stop, transfer_node))

            # Initialize dicts
            departs_prev = {}
            departs_prev[sources[trip_id].node_time] = sources[trip_id]
            prev_departure_time = last_departure_times[trip_id]

            # Create nodes and edges for each stop
            for j in range(len(bus_trips[trip_id])):
                # Initialize variables
                departs_current = {}
                exo_current = {}
                stop = bus_trips[trip_id][j]
                stop_id = int(stop.location.label)
                l = stops_level[stop_id]
                d = stop.cumulative_distance
                travel_time = max(1, stop.arrival_time - prev_departure_time) 
                dwell = stop.departure_time - stop.arrival_time
                prev_departure_time = stop.departure_time

                # Add target node and the flow corresponding to passengers alighting at this stop without a transfer
                target_nodes, od_d_dict = G.add_target_node(target_nodes, od_d_dict, trip_id, stop, start_time, l, d)

                # In this modelization we want to separate transfers and normal alighting passengers
                #  *** TRANSFER PASSENGERS ARE NOT INCLUDED IN THE NUMBER OF ALIGHTING PASSENGERS ***
                # ***
                # if stop_id in transfer_nodes: 
                #     for node in transfer_nodes[stop_id]:
                #         target.flow += -node.get_node_flow()
                # *** 

                stop_is_skipped = stop.skip_stop
                speedup_to_stop = stop.speedup

                # Add all possible paths from previous stop to current stop, givent the current existing paths
                for node_time in departs_prev:
                    cur_arr = {}
                    prev_node = departs_prev[node_time]
                    time_prev = prev_node.node_time

                    # Add bus path without any tactics 
                    no_tactics_arrival_node, no_tactics_departure_node, cur_arr, departs_current = G.add_no_tactics_path(stop, travel_time, time_prev, dwell, cur_arr, departs_current, target_nodes[trip_id][stop_id], prev_node, l, d, trip_id, sp = speedup_to_stop, ss = stop_is_skipped)
                    bus_departures[trip_id][l] = no_tactics_departure_node

                    # Add paths for passengers alighting without a transfer
                    walking_time = int(max(0, (d-prev_node.node_dist)/4*3600-travel_time))
                    edge_weight = 0 if stop_is_skipped == 0 else walking_time
                    # ONLY WHEN EVALUATING REGRETS: when this stop is skipped, we need to add a walking time to the next stop
                    G.add_edge(no_tactics_arrival_node, target_nodes[trip_id][stop_id], edge_weight, ss = stop_is_skipped)

                    # Add paths for passengers alighting with a transfer
                    if stop_id in transfer_nodes and stop_is_skipped == 0:
                        for alighting_transfer_node in transfer_nodes[stop_id]:
                            # Link to no tactics path
                            G.add_alighting_transfer_passenger_edge(no_tactics_arrival_node, alighting_transfer_node)

                    if stop_id in transfer_nodes and stop_is_skipped == 1: # extra walking time because of skipped stop
                        for alighting_transfer_node in transfer_nodes[stop_id]:
                            # Link to skip stop path (# ONLY WHEN EVALUATING REGRETS)
                            G.add_alighting_transfer_passenger_edge(no_tactics_arrival_node, alighting_transfer_node, walking_time, ss = stop_is_skipped)

                # Add paths for passengers boarding without a transfer
                boarding_without_transfer = False
                additional_time = 0 if stop_is_skipped == 0 else walking_time
                edge_weigth = 1 if stop_is_skipped == 0 else walking_time
                planned_departure_time = stop.planned_arrival_time - 60 + additional_time
                if stop.passengers_to_board_int > 0:
                    boarding_without_transfer = True
                    planned_departure_node_tmp = Graph_Node(stop_id, "d", planned_departure_time, 0, "normal", stop.passengers_to_board_int, l, d, trip_id)
                    if planned_departure_time in departs_current:
                        print('Plannned departure time already in departs_current')
                        planned_departure_node = departs_current[planned_departure_time]
                    else:
                        planned_departure_node = Graph_Node(stop_id, "d", planned_departure_time, 0, "normal", 0, l, d, trip_id) 
                        G.add_node(planned_departure_node)
                    G.add_node(planned_departure_node_tmp)
                    edge_dep_plan = Graph_Edge(planned_departure_node_tmp, planned_departure_node, edge_weigth, ss = stop_is_skipped)
                    G.add_edge(planned_departure_node_tmp, planned_departure_node, edge_weigth, ss = stop_is_skipped)
                    exo_current[planned_departure_time] = planned_departure_node_tmp
                    od_m_dict[trip_id].append((stop.passengers_to_board_int, stop, edge_dep_plan))
                else:
                    planned_departure_node_tmp = -1
                    edge_dep_plan = -1
                    planned_departure_node = -1
                
                # Add paths for passengers boarding with a transfer
                new_transfer_nodes, exo_current, od_m_dict = G.add_boarding_transfer_passenger_edges(stop, trip_id,
                                                                                                    transfer_passengers,
                                                                                                    exo_current,
                                                                                                    od_m_dict,
                                                                                                    planned_departure_node_tmp,
                                                                                                    planned_departure_time,
                                                                                                    edge_dep_plan,
                                                                                                    walking_time = walking_time,
                                                                                                    stop_is_skipped = stop_is_skipped,
                                                                                                    boarding_without_transfer = boarding_without_transfer,
                                                                                                    l = l,
                                                                                                    d = d)
                # All possible bus and passenger paths have been added.

                times = G.create_possible_departures_list(stop_id,
                                                            transfer_passengers,
                                                            new_transfer_nodes,
                                                            min_departure_time = -1,
                                                            departs_current = departs_current,
                                                            with_tactics = False)
                
                times = Graph.get_all_passenger_ready_times_and_bus_departure_times(times,
                                                                                    departs_current,
                                                                                    boarding_without_transfer,
                                                                                    planned_departure_time,
                                                                                    planned_departure_node)

                # If passengers missed the previous bus, add a waiting time arc to the current bus trip_id
                times, last_exo, exo_current, departs_current = G.link_passengers_from_previous_bus(times, stop_id, last_exo, exo_current, departs_current, with_tactics = False)

                if j != len(bus_trips[trip_id])-1:
                    # Finalize the graph for this bus stop
                    last_exo = G.finalize_graph_for_current_stop_without_tactics(times,
                                                                                no_tactics_departure_node,
                                                                                last_exo,
                                                                                exo_current,
                                                                                stop_id,
                                                                                start_time,
                                                                                trip_id,
                                                                                order)
                else: # Last stop of the current bus trip
                    skips = {}
                    G.finalize_graph_for_current_bus_trip(stop_id, times, exo_current, last_exo,
                                                        skips,
                                                        global_target_node,
                                                        targets,
                                                        price,
                                                        start_time,
                                                        trip_id,
                                                        order)
                departs_prev = departs_current
        return(G, trip_id, bus_departures)

    def create_possible_departures_list(self, stop_id,
                                        transfer_passengers,
                                        new_transfer_nodes,
                                        min_departure_time,
                                        departs_current,
                                        with_tactics = False):
        """
        This function returns a list of all possible bus departure times for the bus from the current bus stop.
        Inputs:
            - stop_id: the current bus stop
            - transfer_passengers: list of transfer passengers
            - new_transfer_nodes: list of new transfer nodes
            - min_departure_time: the minimum departure time for the bus
            - departs_current: dictionary of bus departure times
            - with_tactics: boolean indicating whether tactics are allowed
        """
        times = []
        if stop_id in transfer_passengers:
            for new_transfer_node in new_transfer_nodes: 
                if with_tactics == False:
                    times.append((new_transfer_node.node_time, new_transfer_node))
                else: 
                    if new_transfer_node.node_time > min_departure_time:
                        departs_current[new_transfer_node.node_time] = new_transfer_node # The bus can depart from this node after some holding time
                    else: 
                        times.append((new_transfer_node.node_time, new_transfer_node)) # The bus cannot depart from this node as it is before the first path arrival at the stop
        return times

    @staticmethod
    def create_opt_model_from_graph_with_mip(V,A,s,t,flows,ids, name='TestSolverMip',
                                            bus_dict = False,
                                            savepath = 'output',
                                            out_of_bus_price = 2,
                                            keys={}, sources={}, puits={}, extras={}): 
        """ Function that takes a graph, information on buses and Origin/Destination pairs and returns an arc-flow model to solve.

        Inputs: 
            - V: set of all nodes (each node is a number 1,2,3 ...)
            - A: set of all arcs 
            - s: source node
            - t: target node
            - flows: exogenous flow at each node. example: flows[6]=+2
            - ids: a dictionary that for each node gives its stop_id. example: ids[6]=46884 
            - bus_dict: a dictionary that for each node gives its bus trip_id. example: bus_dict[6]='2546781'
            - name: instance name
            - savepath: directory where to save the arc-flow model (optional)
            - out_of_bus_price: out of bus waiting time cost 'as perceived by passengers'. 
                    If out_of_bus_price > 1, then passengers prefer to wait inside the bus then to wait out of bus (for example in winter if it's very cold)
                    If out_of_bus_price == 1, then it doesn't matter to passengers if they wait in or out of bus.
        keys: dict that for each node with negative exogenous flow returns a list of edges. These are the edges passengers use to board the bus.
            If the flow on such an edge is 0, that means the passenger did not board the current bus. The alighting flow of the node must be ajusted accordingly.
        sources: dict that for each trip_id returns the departure time at the origin of the trip
        puits: dict that for each bus trip returns the nodes with negative exogenous flows (alighting nodes)

        Outputs: 
        Arc-flow model
        """
        #Initialize model
        m = Model(solver_name="CBC")
        m.verbose = 2
        m.presolve = 0
        
        #Initialize Variables
        x = {(u,v,i): m.add_var(name='x({},{},{})'.format(u,v,i), var_type = INTEGER, lb=0, ub=100) for (u,v,i) in A}
        y = {(u,v,i): m.add_var(name='y({},{},{})'.format(u,v,i), var_type = INTEGER, lb=0, ub=1) for (u,v,i) in A}
        if keys != {}:
            prev_bus = {}
            liste_temp = []
            for bus in sources: 
                liste_temp.append( (bus,sources[bus]))
            liste_temp=sorted(liste_temp, key=itemgetter(1))
            prev_bus[liste_temp[0][0]]=-1
            for value in range(1,len(liste_temp)):
                prev_bus[liste_temp[value][0]]=liste_temp[value-1][0]#dictionnary that gives the trip_id of the previous bus
            keys[-1] = {}
            V3 = copy.deepcopy(V)
            V3.remove(t) #remove target, not included in this constraint. Remove all nodes with negative exogenous flow (treated in particular constraints)
            V4 = set()# nodes with alighting transfer passengers (negative exogenous flow)
            V5 = set()# nodes with 'normal' alighting passengers (negative exogenous flow)
            V6 = set()# nodes with alighting transfer passengers from previous buses (0 flow)
            for trip in puits['t']:
                for v in puits['t'][trip]:
                    V4.add(v)
                    V3.remove(v)
            for trip in puits['n']:
                for v in puits['n'][trip]:
                    V5.add(v)
                    V3.remove(v)
            for v in extras: 
                V6.add(v)
                V3.remove(v)
            indicator_arcs_set = set()
            for k in extras:
                for (u,v,i) in extras[k]:
                    indicator_arcs_set.add((u, v, i))
            for bus in keys: 
                for k in keys[bus]:
                    for (u, v, i) in keys[bus][k]:
                        indicator_arcs_set.add((u, v, i))
            ind = {(u,v,i): m.add_var(name='ind({},{},{})'.format(u,v,i), var_type = INTEGER, lb = 0, ub = 1) for (u,v,i) in [(u, v, i) for (u, v, i) in indicator_arcs_set]}
        if out_of_bus_price !=1 :
            z={(u,v,i): m.add_var(name='z({},{},{})'.format(u, v, i), var_type = INTEGER, lb = 0, ub = 100) for (u,v,i) in [(u, v, i) for (u, v, i) in A if i != 0 and ids[u] == ids[v]]}
        
        #Initialize objective 
        if out_of_bus_price == 1:
            m.objective = minimize(xsum(i * x[u, v, i] for (u,v,i) in A))
        else:
            m.objective = minimize(xsum(i * x[u, v, i] for (u, v, i) in A)+ xsum(i*(out_of_bus_price - 1) * z[u, v, i] for (u, v, i) in [(u, v, i) for (u, v, i) in A if i != 0 and ids[u] == ids[v]]))

        #Constraints

        #Passenger flow constraints
        ### 1st case: there is no information on Origin/Destination pairs (generated instances case)
        if keys == {}: 
            V.remove(t)
            for k in V:
                m += xsum(x[u, v, i] for (u, v, i) in A if v == k) - xsum(x[u, v, i] for (u, v, i) in A if u == k) + flows[k] == 0, 'flow_cst'+str(k) 
            V.add(t)
            V5 = set()
        ### 2nd case: we have O/D pairs. 
        ### Need to make sure passenger demand is transfered to the next bus when a passenger misses their bus.
        else:
            for k in V3:# node without alighting passengers
                m += xsum(x[u, v, i] for (u, v, i) in A if v == k) - xsum(x[u, v, i] for (u, v, i) in A if u == k) + flows[k] == 0, 'flow_cst'+str(k)
            
            for k in V6:#alighting transfer passengers that missed their bus
                ### if a passenger missed their bus, the alighting transfer demand is transferred to the next bus.
                ### ici flows[k]=0 !
                bus = bus_dict[k]
                sum0 = xsum(x[u,v,i] for (u,v,i) in A if v==k)
                sum1 = xsum((1-ind[u,v,i]) for (u,v,i) in extras[k])
                m += sum0 - sum1 == 0, 'flow_cst_transferts_missed'+str(k)

            for k in V4:#alighting transfer passengers 
                ### if a passenger missed their bus, the alighting transfer demand is adapted to the real number of passengers that will get off here.
                bus = bus_dict[k]
                m += xsum(x[u,v,i] for (u,v,i) in A if v==k) + flows[k] + xsum((1-ind[u,v,i]) for (u,v,i) in keys[bus][k])==0, 'flow_cst_transferts'+str(k) 
                
            for k in V5:#'normal' alighting passengers
                bus=bus_dict[k]
                id=ids[k]
                bus_prev=prev_bus[bus_dict[k]]
                if (k in keys[bus])==False: 
                    keys[bus][k]=[]
                if bus_prev!=-1:
                    # This is NOT the first bus in the optimization horizon
                    # We need to retrieve the destinations of passengers that missed the previous bus
                    # and add these to the current bus
                    
                    #1st: find passengers with 'normal' destinations (no transfer) from previous bus
                    k1 = next( (k1 for k1 in V5 if ids[k1]==id and k1!=k),-1)
                    if (k1 in keys[bus_prev])==False: 
                        keys[bus_prev][k1]=[]

                    # #2nd: find passengers with transfer destinations form previous bus
                    # k2s=[k2 for k2 in V4 if ids[k2]==id and k2 in keys[bus_prev]]
                    # transfers=[]
                    # for k2 in k2s:
                    #     transfers+=[(u,v,i) for (u,v,i) in keys[bus_prev][k2]]
                    
                    # here flows[k]<0.
                    # If ind=0, a passenger could not board the bus so they will not alight the bus. (1-ind)=1 and we get an exogenous flow of flows[k]+1
                    # For passengers from the previous bus, if they missed the previous bus they will board and alight this bus. We get an exogenous flow of flows[k]-1
                    m += xsum(x[u,v,i] for (u,v,i) in A if v==k) + flows[k] + xsum((1-ind[u,v,i]) for (u,v,i) in keys[bus][k])- xsum((1-ind[u,v,i]) for (u,v,i) in keys[bus_prev][k1])==0, 'flow_cst_bus'+str(k)  
                else: 
                    # This is the first bus in the optimization horizon.
                    # No passengers from previous bus to retrieve from previous.  
                    # This constraint takes into account if a passenger boarded the current bus or not, in order to adapt the destination node flow. 
                    m += xsum(x[u,v,i] for (u,v,i) in A if v==k)+flows[k]+xsum((1-ind[u,v,i]) for (u,v,i) in keys[bus][k])==0, 'flow_cst'+str(k)
                    
        # "Bus Flow" constraints
        compte_bus=[]
        for u in V:
            compte_bus.append(bus_dict[u])
        compte_bus = len(np.unique(compte_bus))-1 #we don't count bus=-1 for the source and target nodes
        V.remove(s)
        V.remove(t)
        for k in V: 
            m += xsum(y[u,v,i] for (u,v,i) in A if v==k)-xsum(y[u,v,i] for (u,v,i) in A if u == k)==0, 'bus_flow_cst'+str(k) 
        m += -xsum(y[u,v,i] for (u,v,i) in A if u==s) + compte_bus==0, 'source_bus_flow_cst_s'
        m += xsum(y[u,v,i] for (u,v,i) in A if v==t) - compte_bus==0, 'target_bus_flow_cst_final' 
        V.add(s)
        V.add(t)

        #Path constraint: a bus can choose only one path between two nodes
        arcs={}
        for (u,v,i) in A:
            id1=ids[u]
            id2=ids[v]
            puit_ind = (v in V5)
            bus = bus_dict[v]# doesn't take into account the source and destination nodes
            if puit_ind == False:
                if bus in arcs:
                    if (id1,id2) in arcs[bus]: 
                        arcs[bus][(id1,id2)].append((u,v,i))
                    else: 
                        arcs[bus][(id1,id2)]=[(u,v,i)]
                else: 
                    arcs[bus]={}
                    arcs[bus][(id1,id2)]=[(u,v,i)]
        for bus in arcs:
            for (id1,id2) in [(id1,id2) for (id1,id2) in arcs[bus] if id1!=id2]:
                for (u,v,i) in [(u,v,i) for (u,v,i) in arcs[bus][(id1,id2)] if i!=0]:
                    m += x[u,v,i]-100*y[u,v,i]<=0,'bus_path_cst'+str(u)+str(v)+str(i) #if there are no passengers in the bus, x is equal to 0 bus y is equal to 1
        
        #### Indicator variable constraints 
        # 1) Ind=1 if x>0 and ind=0 otherwise. Used to see if a passenger boarded a bus or not.
        ### On peut limiter le nombre de variables aux arcs de depart !!!
        # Only needed if we have Origin/Destination pairs. 
        if keys!={}:
            for (u,v,i) in [(u,v,i) for (u,v,i) in indicator_arcs_set if i!=0]: 
                m+=x[u,v,i]-100*ind[u,v,i]<=0,'ind_cst_max'+str(u)+str(v)+str(i)
                m+=x[u,v,i]-ind[u,v,i]>=0,'ind_cst_min'+str(u)+str(v)+str(i)

        #2)z = x if y=1 and z=0 otherwise.
        # Only needed in the objective function if out_of_bus_price != 1
        if out_of_bus_price != 1:
            for (u,v,i) in [(u,v,i) for (u,v,i) in A if i != 0 and ids[u]==ids[v]]: 
                m+=x[u,v,i]-100*y[u,v,i] <= z[u,v,i], 'z_cst_max'+str(u)+str(v)+str(i)
                m+=z[u,v,i]<=x[u,v,i], 'z_x_cst'+str(u)+str(v)+str(i)

        #write model 
        # completename = os.path.join(savepath,name+'.lp')
        completename = os.path.join('output','Model_Tactics.lp')
        m.write(completename)
        return(m)

    @staticmethod
    def extract_tactics_from_solution(flows: dict,
                                    stop_id : int,
                                    trip_id : str):
        """ 
        This function evaluates the solution of the arc-flow model for a given graph G and returns the tactics used at the stop with stop_id for the bus trip with trip_id.
        The tactics are: Skip-Stop, Speedup and Hold.
        Inputs:
            - bus_flows: dictionary containing the bus flows on each edge of the graph. The format of the bus_flows dictionary is as follows:
                bus_flows[edge : Graph_Edge] = int
            - stop_id: the id of the stop
            - trip_id: the id of the bus trip
        Outputs:
            - time_max: the latest departure time of the bus from the stop
            - wait: indicates if there is a hold time: 
                -1: no hold time
                0: hold time for normal passengers
                1: hold time for transfer passengers
            - speedup: indicates if the speedup tactic used at the stop
                0: no speedup
                1: speedup
            - ss: indicates if the skip-stop tactic is used at the stop
                0: no skip-stop
                1: skip-stop
        """
        # keep only keys with positive values
        bus_flows = {edge: flows[edge] for edge in flows if flows[edge] > 0}
        hold = -1
        skip_stop = 0
        max_departure_time = -1
        speedup = 0
        # Check the skip-stop tactic
        skip_stop_edges = []
        for edge in bus_flows:
            if edge.destination.node_bus == trip_id and edge.origin.node_stop_id != stop_id and edge.destination.node_stop_id == stop_id and edge.destination.node_type == 'skip':
                skip_stop_edges.append(edge)
        if len(skip_stop_edges) > 0:
            # The skip-stop tactic is used
            skip_stop_departure_node = skip_stop_edges[0].destination 
            max_departure_time = skip_stop_departure_node.node_time
            skip_stop = 1
            return(max_departure_time, hold, speedup, skip_stop)
        
        else:
            # Check the hold tactic
            hold_edges = []
            for edge in bus_flows:
                if edge.origin.node_bus == trip_id and edge.origin.node_stop_id == stop_id and edge.destination.node_stop_id == stop_id and edge.origin.node_arrival_departure == 'd' and edge.destination.node_type != 'puit':
                    hold_edges.append(edge)
            if len(hold_edges) > 0:
                # The hold tactic is used
                nodes = [(edge.destination, edge.destination.node_time) for edge in hold_edges]
                hold_departure_node = np.array(sorted(nodes, key=itemgetter(1)) )[-1][0]
                max_departure_time = hold_departure_node.node_time
                if hold_departure_node.node_type == 'transfer':
                    hold = 1 # hold time for transfer passengers
                else: 
                    hold = 0 # hold time for normal passengers (bus arrived before planned arrival time)
            else:
                # No hold tactic is used
                departure_nodes = []
                for edge in bus_flows:
                    if edge.destination.node_stop_id == stop_id and edge.destination.node_arrival_departure == 'd' and edge.origin.node_arrival_departure == 'a' and edge.destination.node_bus == trip_id and edge.destination.node_type != 'puit':
                        departure_nodes.append(edge.destination)
                max_departure_time = departure_nodes[0].node_time # only one possible departure node

            # Check the speedup tactic 
            speedup_edges = []
            for edge in bus_flows:
                if edge.destination.node_stop_id == stop_id and edge.destination.node_bus == trip_id and edge.speedup == 1 : #and edge.origin.node_arrival_departure == 'd' and edge.destination.node_arrival_departure == 'a' and edge.origin.node_stop_id != edge.destination.node_stop_id:
                    speedup_edges.append(edge)
            # The speedup tactic is used
            if len(speedup_edges) > 0:
                speedup = 1
        return(max_departure_time, hold, speedup, skip_stop)

    @staticmethod
    def get_all_tactics_used_in_solution(bus_flows : dict,
                                        trip_id : str,
                                        next_trip_id : str):
        """
        This function returns the tactics applied at each stop for the two buses.
        Inputs:
            -bus_flows: dict associating each edge of the graph to the bus flow on it. The format is as follows:
                bus_flows[edge : Graph_Edge] = int (0 or 1)
            -stop_id: 1st stop of the simulation on which we will do the regret algorithm (decisions on the tactics to use)
            -main_line_trip_id: trip_id on which to work
            -next_line_trip_id: trip_id on which to work
        Outputs:
            -tactics: dict, the tactics applied at each stop for the two buses
        """
        tactics = {}
        tactics[trip_id] = {}
        tactics[next_trip_id] = {}
        travel_edges_between_stops = {}
        bus_flows = {edge: bus_flows[edge] for edge in bus_flows if bus_flows[edge]>0}
        # For each bus trip, get edges used to travel between stops (no hold or dwell edges)
        for bus_trip_id in [trip_id, next_trip_id]:
            travel_edges_between_stops[bus_trip_id] = []
            for e in [e for e in bus_flows if (e.destination.node_bus == bus_trip_id or e.origin.node_bus == bus_trip_id) and e.origin.node_bus != -1 and e.origin.node_stop_id != e.destination.node_stop_id ]:#and (e.d.stop_id!=0 or e.d.ad!='a')]:
                travel_edges_between_stops[bus_trip_id].append((e.origin.node_time, e.destination.node_time, e))
            travel_edges_between_stops[bus_trip_id] = sorted(travel_edges_between_stops[bus_trip_id], key = itemgetter(0, 1))

        # Create a dict containing the arrival, start of hold and departure time nodes for each stop
        departures_in_solution = {}
        for bus in travel_edges_between_stops:
            departures_in_solution[bus]={}
            for element in travel_edges_between_stops[bus]:
                e = element[2] 
                o = e.origin # departure node from previous stop
                a = e.destination # arrival node at current stop (before dwell)
                d = e.destination # first departure node at current stop after dwell (it there is a hold time, this is the beginning of the hold time)
                if a.node_arrival_departure == 'a': # There is no skip-stop tactic, we need to find the departure node after the dwell time is over
                    if e.speedup == 1: 
                        tactics[bus][a.node_stop_id] = ('sp', -1)
                    if int(a.node_level) != 0 : # We do not consider the global target node
                        tmp=[edge for edge in bus_flows if edge.origin == a and edge.destination.node_arrival_departure == "d" and edge.origin.node_stop_id == edge.destination.node_stop_id]
                        if len(tmp)==0 or len(tmp)>1: 
                            print(len(tmp), 'Error finding travel edges between stops\n')
                        else: 
                            edge = tmp[0]
                            d = edge.destination
                else: # a skip-stop tactic is used so a and d are the same node.
                    tactics[bus][d.node_stop_id] = ('ss', -1)
                l1 = o.node_stop_id
                l2 = d.node_stop_id
                if l1 != 0:
                    if l1 not in departures_in_solution[bus]: 
                        departures_in_solution[bus][l1] = {}
                    departures_in_solution[bus][l1]['fin'] = o
                if l2 != 0:
                    if l2 not in departures_in_solution[bus]: 
                        departures_in_solution[bus][l2] = {}
                    departures_in_solution[bus][l2]['arr'] = a
                    departures_in_solution[bus][l2]['deb'] = d
        for bus in [trip_id, next_trip_id]:
            for l in departures_in_solution[bus]:
                hold_time = departures_in_solution[bus][l]['fin'].node_time - departures_in_solution[bus][l]['deb'].node_time
                if hold_time > 0: # There is a hold tactic. Is it used in combination with a speedup tactic?
                                    # Are we waiting for transfer passengers or for planned departure time?
                    if l in tactics[bus]: # This means there is also a speedup tactic at this stop (hold not possible with skip-stop tactic)
                        if departures_in_solution[bus][l]['fin'].node_type == 'transfer': 
                            tactics[bus][l]=('sp_t', departures_in_solution[bus][l]['fin'].node_time) # speedup + hold for transfer
                        else:
                            tactics[bus][l]=('sp_hp', departures_in_solution[bus][l]['fin'].node_time) # speedup + hold for planned departure
                    else: 
                        if departures_in_solution[bus][l]['fin'].node_type == 'transfer': 
                            tactics[bus][l]=('h_t', departures_in_solution[bus][l]['fin'].node_time) # hold for transfer (no speedup)
                        else: 
                            tactics[bus][l]=('h_hp', departures_in_solution[bus][l]['fin'].node_time) # hold for planned departure (no speedup)
                else: 
                    if (l in tactics[bus]) == False: # no speedup, no hold, no skip-stop
                        tactics[bus][l]=('none', -1)
                    # else: # nothing to do as speedup and skip-stop are already in the dictionary
        return(tactics)

    def display_graph(self,
                    display_flows = False,
                    name = 'Graph_Image',
                    savepath = os.path.join('output','fixed_line','gtfs'),
                    figsize = (12,18)): 
        """This function creates an visual representation of the graph using different colors for different node types and edge types.
        Inputs:
            - self: the graph to display
            - display_flows: dictionary containing the flows on each edge of the graph. The format of the display_flows dictionary is as follows:
                display_flows[edge : Graph_Edge] = int
            - name: the name of the image
            - savepath: the path to save the image
            - figsize: the size of the image
        Outputs:
            - None"""

        lost = False
        n_d_exo = False
        n_t_exo = False
        n_ss = False
        l_ss = False
        l_t_nul = False
        l_t_nnul = False

        nodes = self.nodes
        edges = self.edges
        if display_flows == False: 
            display_flows={}
            for edge in edges:
                display_flows[edge] = 1
        t = self.target
        s = self.source
        temps_min = s.node_time
        newnodes = {}
        index = {}
        distances = {}
        G = nx.MultiGraph()
        max_time = temps_min
        max_dist = 0
        levels = {}
        tmp_level_one = []
        j=0
        for i in range(len(nodes)): 
            node = nodes[i] 
            if node != t and node != s and node.node_level != 0 and (node.node_type != 'puit' or node.node_arrival_departure !='d'):
                newnodes[node] = j
                index[j] = node
                distances[node.node_level] = node.node_dist
                levels[node.node_level] = (node.node_dist, node.node_stop_id)
                G.add_node(j, x = node.node_time-temps_min, y = node.node_dist, flow = node.node_flow)
                if node.node_time>max_time: 
                    max_time = node.node_time
                if node.node_dist > max_dist:
                    max_dist=node.node_dist
                if node.node_level == 1 and node.node_arrival_departure == 'a' and node.node_type != 'puit':
                    tmp_level_one.append(j)
            j+=1
        max_time = max_time + 50
        labels = {id: (str)(index[id].node_time-temps_min) for id in G.nodes}
        pos = {}
        ids_to_skip = set()
        nodes_to_skip = set()
        gc = {} #graph colors
        gc['n'] = {}#node colors
        gc['e'] = {}#edge colors 
        gc['e']['n0'] = ('grey','-')
        gc['e']['n1'] = ('black','-')
        gc['e']['p1'] = ('black',':')
        gc['e']['p0'] = ('none','--')
        gc['e']['td1'] = ('black','-')
        gc['e']['td0'] = gc['e']['n0']
        gc['e']['ta1'] = ('royalblue',':')
        gc['e']['ta0'] = ('lightblue',':')
        gc['e']['s1'] = ('yellow','-')
        gc['e']['s0'] = gc['e']['n0']
        gc['e']['final'] = ('powderblue','--')
        gc['n']['p'] = 'none'#'lightgrey'
        gc['n']['na'] = 'pink'
        gc['n']['nd0'] = 'lightgreen'
        gc['n']['nd1'] = 'mediumseagreen'
        # gc['n']['t']='deepskyblue'
        gc['n']['source'] = 'red'
        gc['n']['ta'] = 'lightskyblue'#gc['n']['nd1']#'mediumseagreen'
        gc['n']['td'] = 'dodgerblue'#gc['n']['na']#'pink''deepskyblue'
        gc['n']['s'] = 'yellow'
        for edge in edges:
            u=edge.origin
            v=edge.destination
            edge_labels={}
            if ( u.node_level != 0 and v.node_level != 0 and u.node_level!=-1):
                if u.node_type=="skip":
                    if display_flows[edge]>0:
                        l_ss = True
                        edge_labels[(newnodes[u],newnodes[v])]=str(display_flows[edge])
                        G.add_edge(newnodes[u], newnodes[v], w=display_flows[edge]+1, color=gc['e']['s1'][0], type=gc['e']['s1'][1], label=str(display_flows[edge]))
                    else: 
                        edge_labels[(newnodes[u], newnodes[v])]=""
                        G.add_edge(newnodes[u], newnodes[v], w=1,color=gc['e']['s0'][0],type=gc['e']['s0'][1],label="")
                elif v.node_type=='normal':
                    if display_flows[edge]>0:
                        edge_labels[(newnodes[u],newnodes[v])]=str(display_flows[edge])
                        G.add_edge(newnodes[u], newnodes[v], w=display_flows[edge]+1, color=gc['e']['n1'][0],type=gc['e']['n1'][1], label=str(display_flows[edge]))
                    else: 
                        edge_labels[(newnodes[u],newnodes[v])]=""
                        G.add_edge(newnodes[u], newnodes[v], w=1, color=gc['e']['n0'][0],type=gc['e']['n0'][1],label="")
                elif v.node_type=='puit':
                    if v.node_arrival_departure == "a":
                        if u.node_flow>0 and u.node_level != v.node_level:
                            if (u in nodes_to_skip) == False:
                                if display_flows[edge]>0:
                                    lost = True ### add a red dotted arrow indicating that this passenger did not get a bus in the optimization horizon
                                    G.add_node(j, x=G.nodes[newnodes[u]]['x']+1000, y=G.nodes[newnodes[u]]['y'], flow=0,size=1000)
                                    labels[j] = ">"
                                    pos[j] = (G.nodes[j]['x'], G.nodes[j]['y'])
                                    G.nodes[j]['c'] = 'none'
                                    G.nodes[j]['type'] = 'puit'
                                    edge_labels[(newnodes[u],j)] = str(u.node_flow)
                                    G.add_edge(newnodes[u], j, w=display_flows[edge]+1, color='red', type=gc['e']['p1'][1], label=str(display_flows[edge]))
                                    ids_to_skip.add(j)
                                    nodes_to_skip.add(u)
                                    j+=1
                                else:
                                    edge_labels[(newnodes[u],newnodes[v])]=""
                                    G.add_edge(newnodes[u], newnodes[v], w=1, color=gc['e']['p0'][0], type= gc['e']['p0'][1], label="")
                        else: # alighting without transfer
                            if display_flows[edge]>0:
                                edge_labels[(newnodes[u],newnodes[v])] = str(display_flows[edge])
                                G.add_edge(newnodes[u], newnodes[v], w=display_flows[edge]+1,color= gc['e']['p1'][0], type= gc['e']['p1'][1], label=str(display_flows[edge]))
                            else: 
                                edge_labels[(newnodes[u],newnodes[v])]=""
                                G.add_edge(newnodes[u], newnodes[v], w=1, color= gc['e']['p0'][0], type= gc['e']['p0'][1], label="")
                    else:# Passenger missed their bus
                        if display_flows[edge]>0:
                            lost = True
                            G.add_node(j, x=G.nodes[newnodes[u]]['x']+100, y=G.nodes[newnodes[u]]['y'], flow=0,size=1000)
                            labels[j]=">"
                            pos[j]=(G.nodes[j]['x'], G.nodes[j]['y'])
                            G.nodes[j]['c']='none'
                            G.nodes[j]['type']='puit'
                            edge_labels[(newnodes[u],j)]=str(u.node_flow)
                            G.add_edge(newnodes[u],j,w=display_flows[edge]+1,color='red',type=gc['e']['p1'][1],label=str(display_flows[edge]))
                            ids_to_skip.add(j)
                            nodes_to_skip.add(u)
                            j+=1
                elif v.node_type=='transfer':
                    if v.node_arrival_departure=='d':
                        if display_flows[edge]>0:
                            edge_labels[(newnodes[u],newnodes[v])]=str(display_flows[edge])
                            G.add_edge(newnodes[u], newnodes[v], w=display_flows[edge]+1,color=gc['e']['td1'][0],type=gc['e']['td1'][1],label=str(display_flows[edge]))
                        else: 
                            edge_labels[(newnodes[u],newnodes[v])]=""
                            G.add_edge(newnodes[u], newnodes[v], w=display_flows[edge]+1,color=gc['e']['td0'][0],type=gc['e']['td0'][1],label="")
                    else: 
                        if display_flows[edge]>0:
                            l_t_nnul=True
                            edge_labels[(newnodes[u],newnodes[v])]=str(display_flows[edge])
                            G.add_edge(newnodes[u], newnodes[v], w=display_flows[edge]+1,color=gc['e']['ta1'][0],type=gc['e']['ta1'][1],label=str(display_flows[edge]))
                        else:
                            edge_labels[(newnodes[u],newnodes[v])]="test"
                            l_t_nul=True
                            G.add_edge(newnodes[u], newnodes[v], w=1,color=gc['e']['ta0'][0],type=gc['e']['ta0'][1],label="")
                elif v.node_type=="skip":
                    if display_flows[edge]>0:
                        l_ss=True
                        edge_labels[(newnodes[u],newnodes[v])]=str(display_flows[edge])
                        G.add_edge(newnodes[u], newnodes[v], w=display_flows[edge]+1,color=gc['e']['s1'][0],type=gc['e']['s1'][1],label=str(display_flows[edge]))
                    else: 
                        edge_labels[(newnodes[u],newnodes[v])]=""
                        G.add_edge(newnodes[u], newnodes[v], w=1,color=gc['e']['s0'][0],type=gc['e']['s0'][1],label="")
        print('Nodes:', G.number_of_nodes() )
        print('Edges:',G.number_of_edges() )
        distances[0]=0
        for id in [id for id in G.nodes if (id in ids_to_skip)==False]: 
            node = index[id]
            if node == s:
                pos[id] = (0, distances[1]-0.5)
                G.nodes[id]['c']='green'
                G.nodes[id]['type']='d'
            elif node==t:
                pos[id]=(G.nodes[id]['x'], G.nodes[id]['y'])
                G.nodes[id]['c']='red'
                G.nodes[id]['type']='a'
            elif node.node_dist<0:  #source node
                pos[id]=(G.nodes[id]['x'], distances[1]-0.4)
                G.nodes[id]['c']='green'
                G.nodes[id]['type']='d'
            else:
                if distances[node.node_level]==0:
                    d=0.5
                else:
                    d=distances[node.node_level]
                    d-=distances[node.node_level-1]
                if node.node_type=='puit':
                    pos[id]=(max_time-temps_min,G.nodes[id]['y']-0.3*d)
                    G.nodes[id]['c']=gc['n']['p']
                    G.nodes[id]['type']='puit'
                elif node.node_type=='transfer':
                    n_t_exo=True
                    if node.node_arrival_departure=='a':
                        G.nodes[id]['c']=gc['n']['ta']
                        pos[id]=(G.nodes[id]['x'], G.nodes[id]['y']-0.2*d)
                    else:
                        G.nodes[id]['c']=gc['n']['td']
                        pos[id]=(G.nodes[id]['x'], G.nodes[id]['y'])
                        if node.node_flow!=0:
                            pos[id]=(G.nodes[id]['x'], G.nodes[id]['y']+0.1*d)
                    G.nodes[id]['type']='t'
                elif node.node_type=='normal':
                    if node.node_arrival_departure=='a':
                        pos[id]=(G.nodes[id]['x'], G.nodes[id]['y']-0.3*d)
                        G.nodes[id]['c']=gc['n']['na']
                        G.nodes[id]['type']='a'
                    else: 
                        G.nodes[id]['type']='d'
                        if node.node_flow!=0:
                            G.nodes[id]['c']=gc['n']['nd1']
                            pos[id]=(G.nodes[id]['x'], G.nodes[id]['y']+0.1*d)
                        else:
                            n_d_exo=True
                            G.nodes[id]['c']=gc['n']['nd0']
                            pos[id]=(G.nodes[id]['x'], G.nodes[id]['y'])
                        # pos[id]=(G.nodes[id]['x'], G.nodes[id]['y'])
                elif node.node_type=='skip':
                    G.nodes[id]['type']='skip'
                    n_ss=True
                    pos[id]=(G.nodes[id]['x'], G.nodes[id]['y'])
                    G.nodes[id]['c']=gc['n']['s']

        for id in [id for id in G.nodes if (id in ids_to_skip)==False]:
            node = index[id]
            if node.node_flow!=0: 
                if node.node_type=='puit':
                    if node.node_arrival_departure=="a":
                        labels[id]=">"
                        # labels[id]="sink"
                else: 
                    if node.node_flow>0:
                        # labels[id]="+"+str(node.flow)+"\n \n"
                        labels[id]="+"+str(node.node_flow)+"\n\n"+(str)(node.node_time-temps_min-1)+"\n\n"
                        labels[id]="+"+str(node.node_flow)

                    else:
                        # labels[id]=str(node.flow)+"\n\n"+labels[id]+"\n\n"
                        labels[id]=str(node.node_flow)
            elif node.node_dist<0:
                labels[id]='source_secondaire'
            elif node.node_type=='skip':
                labels[id]='SS'#+(str)(node.level)
            elif node.node_type=='puit':
                labels[id]=""
            else: 
                labels[id] = (str)(node.node_time-temps_min-1)#(str)(node.level)+","+
                labels[id] = ""

        max_level = 1
        tmp_max = 50
        for l in levels: 
            if l>max_level:
                max_level=l
            if l==1: 
                dist=levels[l][0]
                if (l+1) in levels:
                    diff=levels[l+1][0]-dist
                else:
                    diff=0
                stop_id = levels[l][1]
                G.add_node(j, x=temps_min-temps_min, y=dist+0.1*diff, flow=0,size=1000)
                G.add_node(j+1, x=max_time+tmp_max-temps_min, y=dist+0.1*diff, flow=0,size=1000)
                labels[j]=""#"stop"+ str(l)
                labels[j+1]="stop"+str(l)#+"-id:"+str(stop_id)
                pos[j]=(G.nodes[j]['x'], G.nodes[j]['y'])
                pos[j+1]=(G.nodes[j+1]['x'], G.nodes[j+1]['y'])
                G.nodes[j]['c']='white'
                G.nodes[j+1]['c']='white'
                G.nodes[j]['type']='other'
                G.nodes[j+1]['type']='other'
                G.add_edge(j,j+1,w=1,color=gc['e']['final'][0],type=gc['e']['final'][1],label="")
                ids_to_skip.add(j)
                ids_to_skip.add(j+1)
                j+=2
                G.add_node(j, x=200, y=0.5, flow=0, size=1000)
                labels[j]="\n SOURCE"
                pos[j]=(G.nodes[j]['x'], G.nodes[j]['y'])
                G.nodes[j]['c']='none'
                G.nodes[j]['type']='other'
                for node in tmp_level_one:
                    G.add_edge(j,node, w=1,color='grey',type='-',label="")
                ids_to_skip.add(j)
                j+=1
            if l>1:
                dist=levels[l][0]
                if (l+1) in levels:
                    diff=levels[l+1][0]-dist
                else:
                    diff=0
                diff_min=dist-levels[l-1][0]
                G.add_node(j, x=temps_min-temps_min, y=dist+0.1*diff, flow=0,size=1000)
                G.add_node(j+1, x=max_time+tmp_max-temps_min, y=dist+0.1*diff, flow=0,size=1000)
                G.add_node(j+2, x=temps_min-temps_min, y=dist-0.3*diff_min, flow=0,size=1000)
                G.add_node(j+3, x=max_time+tmp_max-temps_min, y=dist-0.3*diff_min, flow=0,size=1000)
                labels[j]=""#"stop"+ str(l)
                labels[j+1]=""#stop"+str(l)+"-id:"+str(stop_id)
                labels[j+2]=""#"stop"+ str(l)
                labels[j+3]=""#stop"+str(l)+"-id:"+str(stop_id)
                pos[j]=(G.nodes[j]['x'], G.nodes[j]['y'])
                pos[j+1]=(G.nodes[j+1]['x'], G.nodes[j+1]['y'])
                pos[j+2]=(G.nodes[j+2]['x'], G.nodes[j+2]['y'])
                pos[j+3]=(G.nodes[j+3]['x'], G.nodes[j+3]['y'])
                G.nodes[j]['c']='none'
                G.nodes[j+1]['c']='none'
                G.nodes[j+2]['c']='none'
                G.nodes[j+3]['c']='none'
                G.nodes[j]['type']='other'
                G.nodes[j+1]['type']='other'
                G.nodes[j+2]['type']='other'
                G.nodes[j+3]['type']='other'
                G.add_edge(j,j+1,w=1,color=gc['e']['final'][0],type=gc['e']['final'][1],label="")
                G.add_edge(j+2,j+3,w=1,color=gc['e']['final'][0],type=gc['e']['final'][1],label="")
                G.add_edge(j+1,j+3,w=1,color='none',type=gc['e']['final'][1],label="stop"+str(l))
                ids_to_skip.add(j)
                ids_to_skip.add(j+1)
                ids_to_skip.add(j+2)
                ids_to_skip.add(j+3)
                j+=4
        G.add_node(j, x=455, y=3.7,flow=0,size=1000)
        labels[j]="SINK \n"
        pos[j] = (G.nodes[j]['x'], G.nodes[j]['y'])
        G.nodes[j]['c']='none'
        G.nodes[j]['type']='other'
        ids_to_skip.add(j)
        for id in [id for id in G.nodes if (id in ids_to_skip)==False]:
            node = index[id]
            if node.node_level == max_level and node.node_arrival_departure=='d':
                G.add_edge(id, j, w=1,color='grey',type='-',label="")
        j+=1
        dist = levels[max_level][0]
        weights = {(u,v):w for u,v,w in G.edges(data='w')}

        # Get edge attributes
        colors = nx.get_edge_attributes(G,'color').values()
        weights = list(nx.get_edge_attributes(G,'w').values())
        style = list(nx.get_edge_attributes(G,'type').values())
        edge_labels={(u,v):w for u,v,w in G.edges(data='label')}
        w=[]
        i=0
        for we in weights: 
            if style[i]==':':
                k=max(we,2)
            else:
                k=max(we//2, 1)
            w.append(k)
            i+=1
        
        # Get node attributes (separately to be able to have different markers)
        node_colors={}
        nodelist={}
        for type in ['a', 'd', 'puit', 't', 'skip', 'other']:
            node_colors[type]=[]
            nodelist[type]=[]
        nodeshape={}
        nodeshape['a']=(5, 0, 180)#'v'#'H'
        nodeshape['d']='p'#'^'
        nodeshape['puit']='o'
        nodeshape['t']='s'
        nodeshape['skip']='D'
        nodeshape['other']='o'
        node_size={}
        for type in [ 'other','t']:
            node_size[type] = 10#200
        for type in ['puit','a', 'd', 'skip']:
            node_size[type] = 10#200
        for id in G.nodes: 
            if G.nodes[id]['type']=='a':
                nodelist['a'].append(id)
                node_colors['a'].append(G.nodes[id]['c'])
            elif G.nodes[id]['type']=='d':
                nodelist['d'].append(id)
                node_colors['d'].append(G.nodes[id]['c'])
            elif G.nodes[id]['type']=='puit':
                nodelist['puit'].append(id)
                node_colors['puit'].append(G.nodes[id]['c'])
            elif G.nodes[id]['type']=='t':
                nodelist['t'].append(id)
                node_colors['t'].append(G.nodes[id]['c'])
            elif G.nodes[id]['type']=='skip':
                nodelist['skip'].append(id)
                node_colors['skip'].append(G.nodes[id]['c'])
            elif G.nodes[id]['type']=='other':
                nodelist['other'].append(id)
                node_colors['other'].append(G.nodes[id]['c'])
        
        ##Make legend
        markersize=12
        linewidth=3
        legend_elements=[]
        legend_elements.append(Line2D([0], [0], marker=nodeshape['a'], color='w', label='arrival node', markerfacecolor=gc['n']['na'], markersize=markersize))
        legend_elements.append(Line2D([0], [0], marker=nodeshape['d'], color='w', label='departure node', markerfacecolor=gc['n']['nd0'], markersize=markersize))
        if n_d_exo:
            legend_elements.append(Line2D([0], [0], marker=nodeshape['d'], color='w', label='departure node\n with passengers', markerfacecolor=gc['n']['nd1'], markersize=markersize))
        if n_t_exo:
            legend_elements.append(Line2D([0], [0], marker=nodeshape['t'], color='w', label='transfer from feeder line', markerfacecolor=gc['n']['td'], markersize=markersize))
            legend_elements.append(Line2D([0], [0], marker=nodeshape['t'], color='w', label='transfer to feeder line', markerfacecolor=gc['n']['ta'], markersize=markersize))
        if n_ss:
            legend_elements.append(Line2D([0], [0], marker=nodeshape['skip'], color='w', label='skip-stop tactic node', markerfacecolor=gc['n']['s'], markersize=markersize))
        legend_elements =legend_elements+ [
                    Line2D([0], [0], marker=r'$+2$', color='none', label='passenger flow at nodes',markerfacecolor='black',markersize=markersize-2),
                    Line2D([0], [0], marker=r'$470$', color='none', label='time at nodes',markerfacecolor='black',markersize=markersize+2),
                    #    Line2D([0], [0], marker=nodeshape['puit'], color='w', label='sink node', markerfacecolor=gc['n']['p'], markersize=markersize),## attention puit
                    Line2D([0], [0], marker='o', color='w', label='', markerfacecolor='w', markersize=markersize),
                    Line2D([0], [0], color=gc['e']['n0'][0],linestyle=gc['e']['n0'][1], lw=linewidth, label='null flow'),
                    Line2D([0], [0], color=gc['e']['n1'][0],linestyle=gc['e']['n1'][1], lw=linewidth, label='positive flow'),
                    Line2D([0], [0], color=gc['e']['p1'][0], lw=linewidth,linestyle=gc['e']['p1'][1], label='alighting passenger flow')]
        if l_ss:
            legend_elements.append(Line2D([0], [0], color=gc['e']['s1'][0],linestyle=gc['e']['s1'][1], lw=linewidth, label='positive flow in skip-stop tactic'))
        if l_t_nnul:
            legend_elements.append(Line2D([0], [0], color=gc['e']['ta1'][0], lw=linewidth,linestyle=gc['e']['ta1'][1], label='positive flow to feeder line'))
        if l_t_nul:
            legend_elements.append(Line2D([0], [0], color=gc['e']['ta0'][0],linestyle=gc['e']['ta0'][1], lw=linewidth, label='null flow towards feeder line'))
        if lost: 
            legend_elements.append(Line2D([0], [0], color='red',linestyle=':', lw=linewidth, label='passengers without a bus'))
        #Plot everything
        fig, ax = plt.subplots(figsize=figsize, dpi=100)
        nx.draw(G
                ,ax=ax
                ,labels=labels
                ,pos=pos
                ,node_color='none'
                ,edge_color=colors
                ,width=w
                ,style=style
                ,font_size=16
                )
        tmp_edge_labels={}
        labels_to_delete=[]
        for key in edge_labels: 
            if len(edge_labels[key])>0 and edge_labels[key][0]=='s': 
                labels_to_delete.append(key)
                tmp_edge_labels[key]=edge_labels[key]
        for key in labels_to_delete: 
            edge_labels.pop(key, None)
        nx.draw_networkx_edges(G, pos, labels_to_delete, edge_color=gc['e']['final'][0],arrows=True, arrowstyle='<|-|>',arrowsize=15,node_size=500, ax=ax)
        nx.draw_networkx_edge_labels(G,pos,edge_labels=edge_labels,font_color='red',label_pos=0.5,font_size=16, font_weight='bold', ax=ax, bbox=dict(facecolor='white', edgecolor='none', alpha=1,pad=-0.15))
        nx.draw_networkx_edge_labels(G,pos,edge_labels=tmp_edge_labels,font_color='black',rotate=False, label_pos=0.5,font_size=16, font_weight='normal', ax=ax)
        for type in ['a', 'd', 'puit', 't', 'skip', 'other']:
            nx.draw_networkx_nodes(G,pos,nodelist=nodelist[type],node_size=node_size[type], node_color=node_colors[type], node_shape=nodeshape[type],ax=ax)#, labels=labels)
        plt.axis('on')
        plt.xlabel('Time (s)', fontsize=14)
        plt.ylabel('Distance (km)',fontsize=14)
        # plt.subplots_adjust(left=0.0, right=1.0, top=0.96, bottom=0.0)
        # ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True)
        # plt.legend(handles=legend_elements,fontsize=14, loc='upper left')
        plt.legend(handles=legend_elements,fontsize=16, loc='best')
        completenamepng=os.path.join(savepath,"graphe_"+name+".png")
        plt.savefig(completenamepng)
        # plt.show()
        plt.close()
