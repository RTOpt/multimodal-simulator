import sys
sys.path.append('C:/Users/asmam/PycharmProjects/SimulatorMultimodal/data/test')
import itertools
import networkx as nx
from networkx.algorithms.shortest_paths.generic import shortest_path
#from networkx.classes.function import path_weight
import math

def find_shortest_path(G, o, d):

    path = shortest_path(G, source=o, target=d, weight='length')
    #path_length = path_weight(G, path, weight='length')

    return path



class Position(object):
    def __init__(self, coordinates):
        self.coordinates = coordinates


class Node(object):
    def __init__(self, id, coordinates):
        self.id = id
        self.coordinates = coordinates
        self.in_arcs = []
        self._out_arcs = []
        #Position.__init__(self, coordinates)

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def get_node_id(self):
        return self.id

    def get_coordinates(self):
        return self.coordinates




class Distance(Node):
    #def __init__(self, node1, node2):
    #    self.node1 = node1
    #   self.node2 = node2
    pass


class Arc(object):
    def __init__(self, in_node, out_node):
        self.in_node = in_node
        self.out_node = out_node
        self.length = Distance.get_distance(self.in_node, self.out_node)


def get_manhattan_distance(node1, node2):
    dist = abs(int(node1[0]) - int(node2[0])) + abs(int(node2[0]) - int(node2[0]))
    return dist

def get_euclidean_distance(node1, node2):
    dist = math.sqrt(((int(node1[0]) - int(node2[0]))**2 + (int(node2[0]) - int(node2[0]))**2).round(2))
    return dist


def create_graph(nodes):
    G = nx.DiGraph()
    #G.add_edges_from(itertools.permutations(nodes, 2))
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if i != j:
                #Manhattan Distance OR Euclidean Distance
                dist = get_manhattan_distance(nodes[i].get_coordinates(),nodes[j].get_coordinates())
                cost = get_manhattan_distance(nodes[i].get_coordinates(),nodes[j].get_coordinates())
                G.add_edge(nodes[i], nodes[j], cost=cost, legnth=dist)
    return G


def get_path(G, node1, node2):
    for node in G.nodes:
        if node.coordinates == node1:
            origin = node
        if node.coordinates == node2:
            destination = node
    path = find_shortest_path(G, origin, destination)
    #path_cost = get_manhattan_distance(node1, node2)
    return path







