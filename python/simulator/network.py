import networkx as nx
import math


class Position(object):
    def __init__(self, coordinates):
        self.coordinates = coordinates


def get_manhattan_distance(node1, node2):
    dist = abs(int(node1[0]) - int(node2[0])) + abs(int(node2[0]) - int(node2[0]))
    return dist


def get_euclidean_distance(node1, node2):
    dist = math.sqrt(((int(node1[0]) - int(node2[0])) ** 2 + (int(node2[0]) - int(node2[0])) ** 2).round(2))
    return dist


class Node(object):
    def __init__(self, node_id, coordinates):
        self.id = node_id
        self.coordinates = coordinates
        self.in_arcs = []
        self._out_arcs = []
        # Position.__init__(self, coordinates)

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def get_node_id(self):
        return self.id

    def get_coordinates(self):
        return self.coordinates


class Arc(object):
    def __init__(self, in_node, out_node):
        self.in_node = in_node
        self.out_node = out_node
        self.length = get_manhattan_distance(self.in_node.get_coordinates(), self.out_node.get_coordinates())


def create_graph(nodes):
    G = nx.DiGraph()
    # G.add_edges_from(itertools.permutations(nodes, 2))
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if i != j:
                # Manhattan Distance OR Euclidean Distance
                dist = get_manhattan_distance(nodes[i].get_coordinates(), nodes[j].get_coordinates())
                cost = get_manhattan_distance(nodes[i].get_coordinates(), nodes[j].get_coordinates())
                G.add_edge(nodes[i], nodes[j], cost=cost, legnth=dist)
    return G
