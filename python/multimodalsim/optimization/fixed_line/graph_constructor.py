
import operator
import fnmatch
import matplotlib.pyplot as plt
from collections import defaultdict
from operator import itemgetter
import networkx as nx
from pathlib import Path
import numpy as np
import os 
from mip import *
from matplotlib.lines import Line2D
import time 
import timeit
import operator 
import pandas as pd
from matplotlib.font_manager import FontProperties
from os import listdir
from typing import List
import matplotlib
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
    def __init__(self, stop_id, ad, time=0, real_time=0, type='normal', flow=0, level=-1, dist=0, bus=-1):
        self.stop_id=stop_id
        self.type=type
        self.time=time
        self.rt=real_time
        self.ad=ad
        self.flow=flow
        if level==-1:
            self.level=stop_id
        else:
            self.level=level
        self.dist=dist
        self.bus=bus

    def __eq__(self, other):
        """Overrides the default implementation of =="""
        if isinstance(other, Graph_Node):
            return (self.stop_id == other.stop_id and self.type==other.type and self.time==other.time and self.ad==other.ad and self.flow==other.flow)
        return False

    def __ne__(self, other):
        """Overrides the default implementation (unnecessary in Python 3)"""
        return not self.__eq__(other)
    
    def __lt__(self, other):
        return((self.time<=other.time))

    def __hash__(self):
        return hash((self.stop_id, self.type, self.time, self.ad,self.flow))
    
    def get_node_id(self):
        return(self.stop_id)
    
    def get_node_time(self):
        return(self.time)
    
    def get_node_real_time(self):
        return(self.rt)
    
    def get_node_arrival_departure(self):
        return(self.ad)
    
    def get_node_type(self):
        return(self.type)
    
    def get_node_flow(self):
        return(self.flow)
    
    def get_node_level(self):
        return(self.level)
    
    def get_node_dist(self):
        return(self.dist)
    
    def get_node_bus(self):
        return(self.bus)

    def set_node_flow(self, flow):
        self.flow = flow
    
    def set_node_type(self, type):
        self.type = type
    
    def set_node_time(self, time):  
        self.time = time
    
    def show_node(self):
        print('***NODE***')
        print("stop id:", self.stop_id) 
        print("       time:",self.get_node_time())
        print("       arrival or dep:", self.get_node_arrival_departure())
        print("       node type: ", self.get_node_type())
        print("       exogenous flow: ", self.get_node_flow())
        print("       level:  ", self.get_node_level())
        print("       bus:  ", self.get_node_bus())
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
        self.o = origin
        self.d = dest
        self.w = weight
        self.c = capacity
        self.sp = sp
        self.ss = ss 
    
    def __eq__(self, other):
        """Overrides the default implementation of =="""
        if isinstance(other, Graph_Edge):
            return (self.o == other.o and self.d == other.d and self.w == other.w and self.c == other.c)
        return False

    def __ne__(self, other):
        """Overrides the default implementation (unnecessary in Python 3)"""
        return not self.__eq__(other)
    
    def __hash__(self):
        return hash((self.o, self.d, self.w, self.c))
    
    def get_origin(self):
        return(self.o)
    
    def get_destination(self):
        return(self.d)
    
    def get_weight(self):
        return(self.w)
    
    def get_speedup(self):
        return(self.sp)
    
    def get_skip_stop(self):
        return(self.ss)
    
    def show_edge(self):
        print('***EDGE***')
        print("origin: stop_id-", self.get_origin().get_node_id(),
              ", arrival/dparture-", self.get_origin().get_node_arrival_departure,
              ", time-", self.get_origin().get_node_time(),
              ", type-", self.get_origin().get_node_type(),
              ", flow-", self.get_origin().get_node_flow(),
              ", level-", self.get_origin().get_node_level(),
              ", bus-", self.get_origin().get_node_bus())
        print("destination: stop_id-", self.get_destination().get_node_id(),
                ", arrival/dparture-", self.get_destination().get_node_arrival_departure,
                ", time-", self.get_destination().get_node_time(),
                ", type-", self.get_destination().get_node_type(),
                ", flow-", self.get_destination().get_node_flow(),
                ", level-", self.get_destination().get_node_level(),
                ", bus-", self.get_destination().get_node_bus())
        print("weight: ", self.get_weight())
        print("speedup: ", self.sp, "skip-stop: ", self.ss)
        print('***EDGE***')

class Graph:
    """ Classe définissant la structure des graphes. 
    Un graphe a un nom "name". 
    Un graphe comprend une liste de noeuds "nodes" de la classe Node et une liste d'arcs "edges" de la classe Edge. 
    De plus, chaque graphe a un noeud source "source" et un noeud puit "target" définit dès le départ.
    """
    def __init__(self,name: str, nodes: List[Graph_Node], edges: List[Graph_Edge], source: Graph_Node, target: Graph_Node):
        self.name=name
        if (source in nodes) == False: 
            nodes.insert(0, source)
        if (target in nodes) == False: 
            nodes.insert(1, target)
        self.nodes = nodes
        self.edges = edges
        self.s = source
        self.t = target
 
    def get_edges(self):
        return(self.edges)
    
    def get_nodes(self):
        return(self.nodes)
    
    def get_source(self):
        return(self.s)
    
    def get_target(self):
        return(self.t)
    
    def nb_nodes(self):
        return(len(self.nodes))
    
    def nb_edges(self):
        return(len(self.edges))
    
    def get_node(self, stop_id, ad, time, type):
        tmp=[]
        for node in self.get_nodes():
            if node.stop_id==stop_id and node.ad==ad and node.time==time and node.type==type:
                tmp.append(node)
        if len(tmp)==1:
            return(tmp[0])
        return(False)
    
    def contains_node(self, node):
        return(node in self.nodes)
    
    def add_node(self, node):
        if self.contains_node(node) == False:
            self.nodes.append(node)

    def contains_edge(self, origin, dest, weight: int):
        edges=[edge for edge in self.get_edges() if edge.get_origin()==origin and edge.get_destination()==dest and edge.get_weight()==weight]
        if len(edges)>0:
            return(True)
        else: return(False)
    
    def add_edge(self, origin, dest, weight = -1, sp=0, ss=0):
        if weight==-1:
            if dest==self.get_target():
                weight=0
            else:
                weight = dest.get_time()-origin.get_time()
        if weight>=0:
            if self.contains_edge(origin, dest, weight)==False: 
                if self.contains_node(origin) == False:
                    print("pb origin not in nodes", origin.show_node())
                    print(self.get_edges())
                    self.add_node(origin)
                if self.contains_node(dest) == False:
                    print("pb dest not in nodes", dest.show_node())
                    self.add_node(dest)
                    print(self.get_edges())
                edge = Graph_Edge(origin, dest, weight, sp=sp, ss=ss)
                self.edges.append(edge)

def GraphConstructorWithTactics(bus_trips: dict, 
                                transfers: dict,
                                prev_times: dict,
                                initial_flows: dict,
                                time_step = 20,
                                price = 3600,
                                speedup_gen = 1,
                                ss_gen = False,
                                od_dict = {},
                                simu=False,
                                last_stop = 0):
    """
    This function takes as input the data on two consecutive bus trips on the same line and returns a graph on which a flow optimization must be performed.
    Inputs: 
        - bus_trips: dictionary of bus trips containing the data on the two trips' stops, travel times, dwell times, number of boarding/alighting passengers etc.
        - transfers: dictionary containing the transfer data for passengers transferring on the two bus trips: transfer time, number of transfers, stops, etc.
            The format of the transfers dictionary is as follows:
            transfers[trip_id][stop_id]['boarding'/'alighting'] = [(transfer_time : int, nbr_passengers : int), ...]
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
    if time_step<2 and ss_gen: 
        return()
    #Initialize graph and parameters
    order = sorted([(prev_times[trip_id], trip_id) for trip_id in bus_trips])
    time_min=order[0][0]
    second_bus = order[-1][1]
    last_stop_second_bus = bus_trips[second_bus][-1]
    time_max = 100 + max( [last_stop_second_bus.departure_time()]+[time for (time, nbr_passengers) in transfers[second_bus][int(last_stop_second_bus.location.label)]['boarding']+transfers[second_bus][int(last_stop_second_bus.location.label)]['alighting']])
    if time_max-time_min>price: 
        price = time_max-time_min
    global_source_node = Graph_Node(-1, "d", order[0][0]-2, order[0][0]-2, "normal", 0, 0, -0.1) # General source node for all buses. Need a non-zero time difference between source nodes to avoid MIP constraints.
    global_target_node = Graph_Node(0, "a", 0, 0, "normal", 0)
    G = Graph('G', [], [], global_source_node, global_target_node) 

    # Create a dict with all stops in the two bus trips
    stop_id_and_dist = []
    for trip_id in bus_trips:
        for stop in bus_trips[trip_id]:
            stop_id_and_dist.append((int(stop.location.label), stop.cumulative_distance))
    stop_id_and_dist=np.unique(stop_id_and_dist,axis=0)
    stop_id_and_dist=sorted(stop_id_and_dist, key=itemgetter(1))
    stops_level = {}
    stops_dist = {}
    targets={}
    level=1
    for i in range(len(stop_id_and_dist)):
        stop_id = int(stop_id_and_dist[i][0])
        if (stop_id in stops_level) == False:
            stops_level[stop_id] = level
            stops_dist[stop_id] = stop_id_and_dist[i][1]
            target_node_for_level = Graph_Node(id, "d", 0, 0, 'puit', 0 ,level, stop_id_and_dist[i][1])
            targets[id] = target_node_for_level
            G.add_node(target_node_for_level)
            level += 1

    # Initialize variables
    sources = {}
    last_exo = {}
    od_m_dict = {}
    od_d_dict = {}
    targets = {}
    # Create nodes and edges for each bus trip
    for (start_time, trip_id) in order:
        bus = trip_id
        od_m_dict[trip_id] = []
        od_m = []
        od_d_dict[trip_id] = []
        targets[trip_id] = {}
        ss = ss_gen
        speedup = speedup_gen
        source = Graph_Node(0, "d", start_time-1, start_time-1, "normal", initial_flows[trip_id], 0, -0.05, trip_id)
        G.add_node(source)
        G.add_edge(global_source_node, source, 1) # Add edge from global source to bus source, the weight is non-zero to avoid MIP constraints.
        sources[trip_id] = source 
        target = global_target_node

        # Create transfer nodes and get transfer data
        transfer_nodes = {} # dict of transfer nodes for each stop, contains transfer nodes for passenger going to other lines.
        transfer_passengers = defaultdict(lambda : defaultdict(dict)) # dict containing the time and number of passengers arriving from other lines at each stop
        l=-1 #level of the stop
        for stop_id in transfers[trip_id]: 
            level = stops_level[stop_id]
            dist = stops_dist[stop_id]
            # Passengers aligting and transfering to other lines
            for (time, nbr_passengers) in transfers[trip_id][stop_id]['alighting']:
                if stop_id not in transfer_nodes:
                    transfer_nodes[stop_id] = []
                bool=True
                for node in transfer_nodes[stop_id]:
                    if node.get_node_time() == time and node.get_node_real_time()==get_passage_cost(p):
                        node.set_node_flow(node.get_node_flow() - nbr_passengers)
                        bool=False 
                        od_d_dict[trip_id].append((stop_id, node))
                if bool: 
                    transfer_node = Graph_Node(stop_id,"a",time, get_passage_cost(p), "transfer", -nbr_passengers, level, dist, trip_id)
                    transfer_nodes[stop_id].append(transfer_node)
                    G.add_node(transfer_node)
                    od_d_dict[trip_id].append((stop_id, transfer_node))
            # Passengers transfering from other lines and boarding main line.
            if stop_id not in transfer_passengers: 
                    transfer_passengers[stop_id] = {}
            for (time, nbr_passengers) in transfers[trip_id][stop_id]['boarding']:
                transfer_passengers[stop_id][time] = nbr_passengers # all transfer times are unique
                od_m.append((nbr_passengers, stop_id, time))
        if last_stop == 0:
            last = l
        elif last_stop == -1:
            last = 0
        else: 
            last=stops_level[int(last_stop)]
        departs_prev = {}
        departs_prev[source.time] = source
        departs_current = {}
        exo_current = {}
        prev_departure_time = prev_times[trip_id]
        skips = {}
        # Create nodes and edges for each stop
        for j in range(len(bus_trips[trip_id])):
            stop = bus_trips[trip_id][j]
            stop_id = int(stop.location.label)
            l = stops_level[stop_id]
            d = stop.cumulative_distance
            if l > last:
                speedup = 1
                ss = False
            travel_time = max(1, stop.arrival_time - prev_departure_time) #dwell at previous stop. Besoin que le temps de voyage soit non-nul pour le MIP par la suite
            dwell = stop.departure_time - stop.arrival_time
            prev_departure_time = stop.departure_time

            # Add target node and the flow corresponding to passengers alighting at this stop without a transfer
            target = Graph_Node(stop_id, "a", start_time, start_time, "puit", -stop.passengers_to_alight[0], l, d, trip_id)
            G.add_node(target)
            targets[trip_id][id] = target
            od_d_dict[trip_id].append((stop, target))

            # In this modelization we want to separate transfers and normal alighting passengers
            #  *** TRANSFER PASSENGERS ARE NOT INCLUDED IN THE NUMBER OF ALIGHTING PASSENGERS ***
            # ***
            # if stop_id in transfer_nodes: 
            #     for node in transfer_nodes[stop_id]:
            #         target.flow += -node.get_node_flow()
            # *** 
            
            dict_prev = departs_prev
            # *** Add all possible paths from previous stop to current stop, givent the current existing paths***
            for node_time in dict_prev:
                cur_arr = {}
                prev_node = dict_prev[node_time]
                time_prev = prev_node.get_node_time()

                # Add speedup tactic nodes and edges
                if speedup != 1 and travel_time > 30:
                    speedup_arrival_time = int(time_prev + travel_time * speedup)
                    speedup_departure_time = (speedup_arrival_time + dwell + time_step - 1)//time_step * time_step
                    if speedup_departure_time >= stop.planned_arrival_time - 60:
                        if speedup_arrival_time in cur_arr:
                            speedup_arrival_node = cur_arr[speedup_arrival_time]
                        else: 
                            speedup_arrival_node = Graph_Node(stop_id, 'a', speedup_arrival_time, 0,'normal', 0, l, d, trip_id)
                            G.add_node(speedup_arrival_node)
                            G.add_edge(G, speedup_arrival_node, target, 0) # arc for alighting passengers to reach target node
                            cur_arr[speedup_arrival_time] = speedup_arrival_node
                        if speedup_departure_time in departs_current: 
                            speedup_departure_node = departs_current[speedup_departure_time]
                        else:
                            speedup_departure_node = Graph_Node(stop_id, "d", speedup_departure_time, 0, "normal", 0, l, d, trip_id)
                            G.add_node(G, speedup_departure_node)
                            departs_current[speedup_departure_time] = speedup_departure_node
                        G.add_edge(G, prev_node, speedup_arrival_node, sp=1) # speedup arc
                        G.add_edge(G, speedup_arrival_node, speedup_departure_node) # dwell time arc

                #  Add no tactics nodes and edges
                arrival_time = time_prev + travel_time    
                if arrival_time in cur_arr:
                    no_tactics_arrival_node=cur_arr[arrival_time]
                else: 
                    no_tactics_arrival_node = Graph_Node(stop_id,'a', arrival_time, 0, 'normal', 0, l, d, trip_id)
                    cur_arr[arrival_time]=no_tactics_arrival_node
                    G.add_node(no_tactics_arrival_node)
                    G.add_edge(no_tactics_arrival_node, target, 0)
                departure_time = (arrival_time + dwell + time_step-1) //time_step*time_step
                if departure_time in departs_current:
                    no_tactics_departure_node = departs_current[departure_time]
                else: 
                    no_tactics_departure_node = Graph_Node(stop_id, "d", departure_time, 0, "normal", 0, l, d, trip_id)
                    departs_current[departure_time]=no_tactics_departure_node
                    G.add_node(no_tactics_departure_node)
                G.add_edge(no_tactics_arrival_node, no_tactics_departure_node)
                G.add_edge(prev_node, no_tactics_arrival_node)

                # Alighting transferring passengers going to other lines: nodes with negative flows
                if stop_id in transfer_nodes:
                    for alighting_transfer_node in transfer_nodes[stop_id]:
                        alighting_transfer_node_time=alighting_transfer_node.get_node_time()
                        # Link to speedup path
                        if speedup !=1  and travel_time>30 and speedup_departure_time >= stop.planned_arrival_time-60: #there is a speedup tactic
                            if alighting_transfer_node_time - speedup_arrival_time > 0:
                                G.add_edge(G,speedup_arrival_node, alighting_transfer_node)
                            else:
                                alighting_transfer_node_time = alighting_transfer_node.get_node_time() - speedup_arrival_time
                                while alighting_transfer_node_time <= 0:
                                    alighting_transfer_node_time += alighting_transfer_node.get_node_real_time()
                                G.add_edge(speedup_arrival_node, alighting_transfer_node, alighting_transfer_node_time)### si on rate la correspondance, le temps de correspondance est d'un intervalle
                        # Link to no tactics path
                        if alighting_transfer_node_time - arrival_time > 0:
                            G.add_edge(no_tactics_arrival_node, alighting_transfer_node)
                        else:
                            alighting_transfer_node_time = alighting_transfer_node.get_node_time() - arrival_time
                            while alighting_transfer_node_time <= 0:
                                alighting_transfer_node_time += alighting_transfer_node.get_node_real_time()
                            G.add_edge(no_tactics_arrival_node, alighting_transfer_node, alighting_transfer_node_time)
                        # If stop is skipped, the passengers cannot alight here.

                # Add skip-stop tactic nodes and edges
                elif l < last and ss and (id in transfer_passengers) == False: 
                    walking_time = int(max(0, (d-prev_node.get_node_dist())/4*3600-travel_time))
                    skip_stop_time = (arrival_time + time_step - 1)//time_step*time_step #here arrival and departure time are the same
                    if skip_stop_time > stop.planned_arrival_time-60:
                        if skip_stop_time in skips: 
                            skip_node = skips[skip_stop_time]
                            # skip_node.type='skip'
                        else:
                            skip_node = Graph_Node(stop_id, "d", skip_stop_time, 0, "skip", 0, l, d, trip_id)
                            skips[skip_stop_time] = skip_node
                            G.add_node(skip_node)
                        if skip_stop_time > time_prev:
                            G.add_edge(G, prev_node, skip_node, ss=1)
                        else:
                            G.add_edge(G, prev_node, skip_node, travel_time, ss=1)
                        G.add_edge(skip_node, target, walking_time, ss=1) #for passengers that need to walk to their destination
            # *** All bus paths are added, now we need to add remaining passengers ***

            # Add passengers boarding without a transfer at this stop
            min_departure_time = min([time for time in departs_current])
            no_transfer_boarding = False
            planned_departure_time = stop.planned_arrival_time - 60
            if stop.passengers_to_board[0] > 0:
                no_transfer_boarding = True
                planned_departure_node_tmp = Graph_Node(stop_id, "d", planned_departure_time, 0, "normal", stop.passengers_to_board[0], l, d, trip_id)
                G.add_node(planned_departure_node_tmp)
                if planned_departure_time in departs_current:
                    planned_departure_node = departs_current[planned_departure_time]
                else: 
                    planned_departure_node=Graph_Node(stop_id, "d", planned_departure_time, 0, "normal", 0, l, d, trip_id)
                    G.add_node(planned_departure_node)
                    if planned_departure_node.get_node_time() > min_departure_time:
                        departs_current[planned_departure_time] = planned_departure_node
                edge_dep_plan = Graph_Edge(planned_departure_node_tmp, planned_departure_node, 1)
                G.add_edge(planned_departure_node_tmp, planned_departure_node, 1)
                exo_current[planned_departure_time] = planned_departure_node_tmp
                if planned_departure_node.get_node_time() > min_departure_time:
                    departs_current[planned_departure_time] = planned_departure_node
                od_m_dict[trip_id].append((stop.passengers_to_board[0], stop, edge_dep_plan))
                for skip_node in skips:
                    skip_edge_time = skips[skip_node].get_node_time()-(walking_time + planned_departure_time) # there is enough time for passengers to walk from the previous stop to the skipped stop
                    if skip_edge_time > 0:
                        G.add_edge(planned_departure_node, skips[skip_node], skip_edge_time, ss=1)

            # Add passengers boarding with a transfer at this stop
            times = []
            if stop_id in transfer_passengers:
                tmp = []
                for transfer_time in transfer_passengers[stop_id]:
                    transfer_time_discrete = (transfer_time + time_step - 1)//time_step * time_step
                    # There are two possibilities: transfer happens at the same time as the normal boarding or not
                    if transfer_time_discrete == planned_departure_time: 
                        planned_departure_node_tmp.set_node_flow(planned_departure_node_tmp.get_node_flow() + transfer_passengers[stop_id][transfer_time])
                        planned_departure_node_tmp.set_node_type('transfer')
                        od_m_dict[trip_id].append((transfer_passengers[id][transfer_time], stop, edge_dep_plan))
                    else:
                        # All transfer times are unique so we only need to check for the planned departure time
                        transfer_departure_node = Graph_Node(id, "d", transfer_time_discrete, 0, "transfer", 0, l, d, trip_id)
                        transfer_departure_node_tmp = Graph_Node(id, "d", transfer_time_discrete, 0, "transfer", transfer_passengers[id][transfer_time], l, d, trip_id)
                        G.add_node(transfer_departure_node)
                        G.add_node(transfer_departure_node_tmp)
                        edge_deb = Graph_Edge(transfer_departure_node_tmp, transfer_departure_node, 1)
                        G.add_edge(transfer_departure_node_tmp, transfer_departure_node, 1)
                        exo_current[transfer_time_discrete] = transfer_departure_node_tmp
                        tmp.append(transfer_departure_node)
                        od_m_dict[trip_id].append((transfer_passengers[id][transfer_time], stop, edge_deb)) 
                for new_transfer_node in tmp: 
                    if new_transfer_node.get_node_time() > min_departure_time:
                        departs_current[new_transfer_node.get_node_time()] = new_transfer_node # The bus can depart from this node after some holding time
                    else: 
                        times.append((new_transfer_node.get_node_time(), new_transfer_node)) # The bus cannot depart from this node as it is before the first path arrival at the stop
            
            # Connect all consecutive nodes after the first possible arrival time at the stop to allow for holding
            for time in departs_current:
                times.append((time, departs_current[time]))
            if no_transfer_boarding and (planned_departure_time in departs_current) == False:
                times.append((planned_departure_time, planned_departure_node))
            times=sorted(times, key=itemgetter(0))
            for time in skips: 
                if (time in departs_current) == False:
                    departs_current[time] = skips[time]
                elif (time+1 in departs_current)==False:
                    departs_current[time+1]=skips[time]
            if stop_id in last_exo: # add arc for when passengers missed the previous bus
                for node_exo in last_exo[stop_id]: 
                    if node_exo.get_node_time() <= times[0][0]: 
                        G.add_edge(node_exo, times[0][1])
                    elif node_exo.get_node_time() > times[-1][0]:
                        node_dep = [edge for edge in G.get_edges() if edge.o == node_exo][0].get_destination()
                        times.append((node_dep.get_node_time(), node_dep))
                        while node_dep.get_node_time() in departs_current:
                            node_dep.set_node_time(node_dep.get_node_time + 1)
                        departs_current[node_dep.get_node_time()] = node_dep
                    else: 
                        i=1
                        node_exo_test = True
                        while i < len(times) and node_exo_test:
                            if node_exo.time<=times[i][0]:
                                G.add_edge(node_exo, times[i][1])
                                node_exo_test = False
                            i+=1
                last_exo.pop(id, None)
            if j != len(bus_trips[trip_id])-1:
                for k in range(len(times)-1):
                    G.add_edge(times[k][1], times[k+1][1])
                if ss==False and speedup==1:
                    last_exo[id]=[exo_current[key] for key in exo_current if key >= departure_time] # any earlier departures are impossible
                else: 
                    last_exo[id]=[exo_current[key] for key in exo_current]
            else:
                for k in range(len(times)):
                    G.add_edge(times[k][1], target, 0)
                for node in skips: 
                    G.add_edge(skips[node], target, 0)
                for node_exo in exo_current: 
                    G.add_edge(exo_current[node_exo], target, 0)
                if (start_time, trip_id) == order[-1]:
                    for id in last_exo: 
                        target_niveau = targets[trip_id]
                        for node_exo in last_exo[trip_id]:
                            if node_exo.get_node_bus()==str(trip_id):
                                G.add_edge(node_exo, target_niveau, price)
            departs_prev=departs_current
            departs_current={}
            skips={}
            exo_current={}
        if simu: 
            ss_gen=False
            speedup_gen=1
    return(G)

def build_noopt_multiple_buses_hash(passages_multiple: dict, flot_initial:int,pas=20,price=3600,od_dict={}):
    """
    Fonction qui prend en entree des donnees de passages d'un bus et qui renvoie un graphe sur lequel il faut realiser
    une optimisation de flot. Le graphe propose le chemin reel des bus. 

    Entrees: 
    passages-liste de passages aux arrets.Les passages sont ordonnés dans l'ordre de passage
    temps-temps actuel au debut de la reoptimisation. On prend generalement le temps de passage reel du premier passage. 
    flot_initial-nombre de passagers dans le bus 
    price-cout de retard d'un passager qui rate son bus (non egal a l'intervalle du bus !!!)

    Sorties: 
    G- graphe construit """

    # if pas<2 and ss_gen: 
    #     print('le pas est trop petit !!!! RECOMMENCER')
    #     return()
    order=sorted([(passages_multiple[p][0].ha-passages_multiple[p][0].cost,p) for p in passages_multiple],key=itemgetter(0))
    # order=sorted([(passages_multiple[p][0].hp-passages_multiple[p][0].cost,p) for p in passages_multiple],key=itemgetter(0))
    time_min=order[0][0]
    time_max=max( [get_passage_heure_act(p)+100 for p in passages_multiple[order[-1][1]] ])
    if time_max-time_min>price: 
        price=time_max-time_min
    bus=len(order)
    # print('nombre de bus',bus)
    if isinstance(flot_initial, int):
        source_gen=Node(-1,"d",order[0][0]-2,order[0][0]-2,"normal",flot_initial,0,-0.1)###Besoin d'une diff de temps entre les sources
    else:
        source_gen=Node(-1,"d",order[0][0]-2,order[0][0]-2,"normal",0,0,-0.1)###Besoin d'une diff de temps entre les sources
    target_gen=Node(0,"a",0,0,"normal",0)
    G=Graph('G',[],[],source_gen,target_gen) 
    ### Creer dict des arrets dans tous les passages 
    tmp=[]
    for trip_id in passages_multiple:
        for passage in passages_multiple[trip_id]:
            tmp.append((int(get_passage_stop_id(passage)), get_passage_dist(passage)))
    tmp=np.unique(tmp,axis=0)
    tmp=sorted(tmp, key=itemgetter(1))
    stops_level={}
    targets={}
    departs={}
    level=1
    for i in range(len(tmp)):
        id=int(tmp[i][0])
        if (id in stops_level)==False:
            stops_level[id]=level
            target_niveau=Node(id,"d",0,0,'puit',0,level,tmp[i][1])
            targets[id]=target_niveau
            add_node(G, target_niveau)
            add_edge(G,target_niveau,target_gen,0)
            level+=1
    sources={}
    last_prec={}
    last_exo={}
    od_m_dict={}
    od_d_dict={}
    targets = {}
    prev_transfers=[]
    for (temps_depart,passage_trip_id) in order:
        bus=str(passage_trip_id)
        departs[bus]={}
        od_m_dict[bus]=[]
        od_m=[]
        od_d_dict[bus]=[]
        targets[bus]={}
        # print('depart:', temps_depart, ', trip_id:',passage_trip_id, ', nbr arrets:', len([p for p in passages_multiple[passage_trip_id] if get_passage_transfer(p)==False]))
        if isinstance(flot_initial, int):
            source=Node(0,"d",temps_depart-1,temps_depart-1,"normal",0,0,-0.05,bus)
        else: 
            source=Node(0,"d",temps_depart-1,temps_depart-1,"normal",flot_initial[bus],0,-0.05,bus)
        add_node(G,source)
        add_edge(G, source_gen, source,1)### weight!=0 pour que les contraintes dans MIP soient valables 
        sources[passage_trip_id]=source
        target=target_gen
        passages=passages_multiple[passage_trip_id]
        transfers={}#dictionnaire qui pour un id donne renvoie les noeuds de transfert correspondant pour les passager allant vers d<autres lignes
        transfer_passengers=defaultdict(lambda : defaultdict(dict))#dictionnaire qui pour un id donné renvoie les temps et nombre de passagers provenant de correspondance
        l=0
        ###Noeuds de transfert
        ### On estime ici que les donnees sont traitees avant d'etre rentrees dans la fonction build_graph
        for p in [passage for passage in passages if get_passage_transfer(passage)==True]: 
            id=int(get_passage_stop_id(p))
            l=stops_level[id]
            d=get_passage_dist(p)
            #Flux sortant de la ligne principale et allant vers d'autres lignes
            time=get_passage_heure_act(p)+get_passage_dwell_time(p)
            if get_passage_nb_desc(p)>0:
                transfer_node=Node(id,"a",time, get_passage_cost(p),"transfer", -get_passage_nb_desc(p),l,d,bus)
                if id in transfers:
                    bool=True
                    for node in transfers[id]:
                        if get_time(node)==time and get_real_time(node)==get_passage_cost(p):
                            node.flow+=transfer_node.flow
                            bool=False
                            od_d_dict[bus].append((p, node))
                    if bool:
                        transfers[id].append(transfer_node)
                        add_node(G, transfer_node)
                        od_d_dict[bus].append((p, transfer_node))
                else: 
                    transfers[id]=[transfer_node]
                    add_node(G, transfer_node)
                    od_d_dict[bus].append((p, transfer_node))

            #Flux entrant depuis d'autres lignes vers la ligne principale
            ### faire en sorte que si 2 transferts differents arrivent a la meme heure on merge les flots !!!
            time=get_passage_heure_act(p)
            if get_passage_nb_montant(p)>0:
                if id in transfer_passengers:#flots allant vers la ligne principale 
                    if time in transfer_passengers[id]:
                        transfer_passengers[id][time]+=get_passage_nb_montant(p)
                    else:
                        transfer_passengers[id][time]=get_passage_nb_montant(p)
                else: 
                    transfer_passengers[id]={}
                    transfer_passengers[id][time]=get_passage_nb_montant(p)
                od_m.append((p, id, time))
        extras=[]
        if prev_transfers!=[] and od_dict!={}:
            for (p, transfer_node) in [(p, transfer_node) for (p, transfer_node) in prev_transfers if get_passage_transfer(p)==True and get_passage_nb_desc(p)>0]:
                id=get_passage_stop_id(p)
                l=stops_level[id]
                d=get_passage_dist(p) 
                #Flux sortant de la ligne principale et allant vers d'autres lignes
                time=get_passage_heure_act(p)+get_passage_dwell_time(p)
                temporary=next( (p for p in passages if get_passage_transfer(p)==False and get_passage_stop_id(p)==id),-1)
                if temporary==-1: 
                    print('noeud de transfert')
                    show_passage_short(p)
                    print('bus suivant', bus)
                    for p in passages: 
                        show_passage_short(p)
                hp=get_passage_heure_plan(temporary)
                while time<hp-60: 
                # while time<hp: 
                    time+=get_passage_cost(p)
                if id in transfers:
                    bool=True
                    times=[get_time(node) for node in transfers[id]]
                    while (time in times)==True: 
                        time+=1
                    transfer_node=Node(id,"a",time,get_passage_cost(p),"transfer", 0,l,d,bus)
                    transfers[id].append(transfer_node)
                    add_node(G, transfer_node)
                    extras.append((p, transfer_node))
                else: 
                    transfer_node=Node(id,"a",time,get_passage_cost(p),"transfer", 0,l,d,bus)
                    transfers[id]=[transfer_node]
                    add_node(G, transfer_node)
                    extras.append((p, transfer_node))
        passages_normaux=[passage for passage in passages if get_passage_transfer(passage)==False]
        departs_prev={}
        departs_prev[source.time]=source
        departs_current={}
        exo_current={}
        dwell=-1
        ###Noeuds puits et noeuds normaux
        for j in range(len(passages_normaux)):
            p=passages_normaux[j]
            id=int(get_passage_stop_id(p))
            l=stops_level[id]
            d=get_passage_dist(p)
            travel_time=max(1,get_passage_cost(p)-dwell)### dwell at previous stop. Besoin que le travel time soit non nul pour la suite.
            dwell=get_passage_dwell_time(p)
            puit=Node(id,"a",temps_depart,temps_depart,"puit",-get_passage_nb_desc(p),l,d,bus)
            if id in transfers:
                for node in transfers[id]:
                    puit.flow+=-node.get_node_flow()
            #avec la nouvelle modelisation on veut toujours le puit
            add_node(G, puit)
            puit_existe=True
            targets[bus][id]=puit
            od_d_dict[bus].append((p,puit))
            dict_prev=departs_prev
            node=list(dict_prev.keys())[0]
            dist_prev=0
            for stops_id in targets: 
                if targets[stops_id].level==l-1:
                    dist_prev=targets[stops_id].dist
            walking_time=int(max(0, (d-dist_prev)/4*3600-travel_time))
            passage_skip=int(get_passage_ss(p))
            passage_speedup=int(get_passage_sp(p))
            for node in dict_prev:
                cur_arr={}
                time_prev=dict_prev[node].time
                a_time=time_prev+travel_time
                ###Normal option
                walking_time=int(max(0, (d-dist_prev)/4*3600-travel_time))
                if a_time in cur_arr:
                    slow=cur_arr[a_time]
                else: 
                    slow=Node(id,'a',a_time,0,'normal',0,l,d,bus)
                    cur_arr[a_time]=slow
                d_time=(a_time+dwell+pas-1)//pas*pas
                if d_time in departs_current:
                    slow_d=departs_current[d_time]
                else: 
                    slow_d=Node(id,"d",d_time,0,"normal",0,l,d,bus)
                    departs_current[d_time]=slow_d
                departs[bus][l]=slow_d
                if passage_skip==1: 
                    slow.type='skip'
                add_node(G, slow)
                add_node(G,slow_d)
                add_edge(G,dict_prev[node],slow, sp=passage_speedup, ss=passage_skip)
                add_edge(G,slow,slow_d)

                ###Passagers qui descendent 
                if puit_existe and passage_skip==0:
                    add_edge(G,slow,puit,0)
                if puit_existe and passage_skip==1:### minutes de marche a cause du Skip
                    add_edge(G,slow,puit,walking_time, ss=1)
                ### Passagers allant vers d'autres lignes 
                if id in transfers and passage_skip==0:
                    for node1 in transfers[id]:
                        if get_time(node1)-a_time>0:
                            add_edge(G,slow,node1)
                        else: 
                            node1_time=get_time(node1)-a_time
                            while node1_time<=0:
                                node1_time+=int(get_real_time(node1))
                            add_edge(G,slow,node1,node1_time)
                if id in transfers and passage_skip==1:### minutes de marche a cause du skip
                    for node1 in transfers[id]:
                        if get_time(node1)-(a_time+walking_time)>0:
                            add_edge(G,slow,node1,get_time(node1)-(a_time+walking_time),ss=1)
                        else: 
                            node1_time=get_time(node1)-(a_time+walking_time)
                            while node1_time<=0:
                                node1_time+=int(get_real_time(node1))
                            add_edge(G,slow,node1,node1_time, ss=1)
            #Passagers montant a l'arret (sans transfert)
            #premier flux exogene positif a ajouter ici
            # tmps_min=min([time for time in departs_current])
            depart=False
            heure_dep_plan=get_passage_heure_plan(p)-60
            # heure_dep_plan=get_passage_heure_plan(p)+dwell
            if heure_dep_plan in exo_current:
            # if heure_dep_plan in departs_current:
                print('on devrait jamais etre la')
                dep_plan=departs_current[heure_dep_plan]
                dep_plan_tmp=exo_current[heure_dep_plan]
                dep_plan_tmp.flow+=get_passage_nb_montant(p)
                # depart=True
                # for (pdeb,edge_deb) in od_m_dict[bus]:
                #     if edge_deb.o==dep_plan_tmp:
                #         od_m_dict[bus].append((p, edge_deb))
                #### groooossse erreur
            else: 
                if get_passage_nb_montant(p)>0:
                    depart=True
                    if passage_skip==0:
                        dep_plan_tmp=Node(id,"d",heure_dep_plan,0,"normal",get_passage_nb_montant(p),l,d,bus)
                        dep_plan=Node(id,"d",heure_dep_plan,0,"normal",0,l,d,bus)
                        add_node(G,dep_plan)
                        add_node(G,dep_plan_tmp)
                        edge_dep_plan=Edge(dep_plan_tmp,dep_plan,1)
                        add_edge(G, dep_plan_tmp, dep_plan,1)
                    else: 
                        # dep_plan_tmp=Node(id,"d",heure_dep_plan+walking_time,0,"normal",get_passage_nb_montant(p),l,d,bus)
                        dep_plan_tmp=Node(id,"d",heure_dep_plan+walking_time,0,"normal",get_passage_nb_montant(p),l,d,bus)
                        dep_plan=Node(id,"d",heure_dep_plan+walking_time,0,"normal",0,l,d,bus)
                        add_node(G,dep_plan)
                        add_node(G,dep_plan_tmp)
                        edge_dep_plan=Edge(dep_plan_tmp,dep_plan,walking_time, ss=1)
                        add_edge(G, dep_plan_tmp, dep_plan,walking_time,ss=1)
                        heure_dep_plan=heure_dep_plan+walking_time
                    exo_current[heure_dep_plan]=dep_plan_tmp
                    od_m_dict[bus].append((p, edge_dep_plan))
                    ####Ici on sait que le depart sera a l'heure actuelle, pas de depart possible depuis ces arrets
                    # if dep_plan.time>=tmps_min: 
                    #     print('dep plan  plus grand que temps min')
                    #     departs_current[dep_plan.time]=dep_plan
            
            # Passagers provenant d'autres lignes
            times=[]
            if id in transfer_passengers:
                tmp=[]
                for transfer_t in transfer_passengers[id]:
                    t=(transfer_t+pas-1)//pas*pas
                    test=True
                    for i in exo_current:
                        # node1=departs_current[i]
                        node1=exo_current[i]
                        if get_time(node1)==t:
                            node1.flow+=transfer_passengers[id][transfer_t]
                            test=False
                            node1.type='transfer'
                            to_add=[]
                            for (pdeb1,edge_deb) in od_m_dict[bus]:
                                if edge_deb.o==node1:
                                    edge_deb.d.type='transfer'
                                    for (pdeb, id_deb, time_deb) in [(pdeb, id_deb, time_deb) for (pdeb, id_deb, time_deb) in od_m if id_deb==id and time_deb==transfer_t]:
                                        to_add.append((pdeb,edge_deb))
                            for (pdeb, edge_deb) in to_add:
                                od_m_dict[bus].append((pdeb,edge_deb))
                    if test: 
                        if transfer_passengers[id][transfer_t]>0:
                            # print('on est la')
                            if passage_skip==0:
                                dep=Node(id,"d",t,0,"transfer",0,l,d,bus)
                                dep_tmp=Node(id,"d",t,0,"transfer",transfer_passengers[id][transfer_t],l,d,bus)
                                add_node(G,dep)
                                add_node(G, dep_tmp)
                                edge_deb=Edge(dep_tmp,dep,1)
                                add_edge(G, dep_tmp, dep,1)
                            else: 
                                while (t+walking_time in exo_current)==True:
                                    t+=1
                                dep=Node(id,"d",t,0,"transfer",0,l,d,bus)#minutes de marche en plus
                                dep_tmp=Node(id,"d",t+walking_time,0,"transfer",transfer_passengers[id][transfer_t],l,d,bus)
                                add_node(G,dep)
                                add_node(G, dep_tmp)
                                edge_deb=Edge(dep_tmp,dep,walking_time, ss=1)
                                add_edge(G, dep_tmp, dep,walking_time, ss=1)
                            exo_current[t]=dep_tmp
                            tmp.append(dep)
                            for (pdeb, id_deb, time_deb) in [(pdeb, id_deb, time_deb) for (pdeb, id_deb, time_deb) in od_m if id_deb==id and time_deb==transfer_t]:
                                od_m_dict[bus].append((pdeb,edge_deb))
                for node1 in tmp: 
                    #Ici on sait que le depart sera a l'heure actuelle, pas de depart possible depuis ces arrets
                    # if node1.time>=tmps_min:
                    #     departs_current[node1.time]=node1 #depart possible depuis ces arrets
                    # else: 
                    times.append((node1.time,node1))#pas de depart possible depuis ces arrets, on prend uniquement en compte le flux
            #Connection des temps possibles de departs (equivaut aux dwell times)
            for time in departs_current:
                times.append((time, departs_current[time]))
            if depart:
                times.append((heure_dep_plan,dep_plan))
            times=sorted(times, key=itemgetter(0))
            if id in last_prec:
                # add_edge(G, last_prec[id],times[0][1])
                last_prec.pop(id, None)
            if id in last_exo:
                for node_exo in last_exo[id]:
                    if node_exo.time<=times[0][0]:
                        add_edge(G, node_exo,times[0][1])
                    elif node_exo.time>times[-1][0]:
                        # print('GROS PROBLEME')
                        # print('node exo')
                        # show_node(node_exo)
                        # print()
                        node_dep=[edge for edge in get_edges(G) if edge.o==node_exo][0].d
                        times.append((node_dep.time,node_dep))
                        exo_current[node_exo.time]=node_exo
                        #### On est dans le cas NoOpt, le bus part forcement du noeud slow_d. 
                        ### Donc pas besoin de rajouter ces noeuds a departs current comme ils sont apres slow_d

                        # while (node_dep.time in departs_current)==True:
                        #     node_dep.time+=1
                        # departs_current[node_dep.time]=node_dep   
                    else: 
                        i=1
                        node_exo_test=True
                        while i<len(times) and node_exo_test:
                            if node_exo.time<=times[i][0]:
                                add_edge(G, node_exo,times[i][1])
                                node_exo_test=False
                            i+=1
                last_exo.pop(id,None)
            if p!=passages_normaux[-1]:
                for k in range(len(times)-1):
                    # if times[k][1]!=slow_d:
                    if times[k][0]<slow_d.time:
                        add_edge(G,times[k][1], times[k+1][1])
                if times[len(times)-1][1]!=slow_d or (temps_depart,passage_trip_id)==order[-1]:
                    # last_prec[id]=times[len(times)-1][1]
                    last_exo[id]=[exo_current[key] for key in exo_current if key>=slow_d.time]
            else:
                for k in range(len(times)):
                    add_edge(G, times[k][1],target,0)
                for node_exo in exo_current: 
                    add_edge(G,exo_current[node_exo], target,0)
                if (temps_depart,passage_trip_id)==order[-1]:
                    for id in last_prec:
                        target_niveau=targets[id]
                        # add_edge(G, last_prec[id],target_niveau,price)
                    for id in last_exo: 
                        target_niveau=targets[id]
                        for node_exo in last_exo[id]:
                            exo_edge=False
                            if node_exo.bus==str(passage_trip_id): #noeud non pris en compte de ce bus
                                add_edge(G, node_exo,target_niveau,price)
                                exo_edge=True
                            else: 
                                print('ON NE DEVRAIT PLUS JAMAIS ETRE LA')
                            if exo_edge==False: 
                                print('probleme de flux')
            departs_prev=departs_current
            departs_current={}
            exo_current={}
            prev_transfers=od_d_dict[bus]
    od,stats_od,extras=convert_od(od_m_dict, od_d_dict,extras, od_dict)
    return(G, bus,departs,od,stats_od,extras)

