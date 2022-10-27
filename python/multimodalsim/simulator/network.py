import networkx as nx
import math
from networkx.readwrite import json_graph
import json
from json import JSONEncoder
import networkx as nx

from multimodalsim.optimization.get_paths_osrm import get_path


class Position(object):
    def __init__(self, coordinates):
        self.coordinates = coordinates

class CustomEncoder(json.JSONEncoder):
    def default(self, o):
            return o.__dict__


def get_manhattan_distance(node1, node2):
    dist = abs(int(node1[0]) - int(node2[0])) + abs(int(node1[1]) - int(node2[1]))
    return dist


def get_euclidean_distance(node1, node2):
    dist = math.sqrt((((node1[0] - node2[0]) ** 2) + ((node1[1] - node2[1]) ** 2))).__round__(2)
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

    for i in range(len(nodes)):
        G.add_node(nodes[i].get_node_id(), pos=nodes[i].get_coordinates(), Node=nodes[i])
        for j in range(len(nodes)):
            if i != j:
                # Manhattan Distance OR Euclidean Distance
                # dist = get_euclidean_distance(nodes[i].get_coordinates(), nodes[j].get_coordinates())
                # cost = get_euclidean_distance(nodes[i].get_coordinates(), nodes[j].get_coordinates())

                res = get_path(nodes[i].get_coordinates(), nodes[j].get_coordinates())
                G.add_edge(nodes[i].get_node_id(), nodes[j].get_node_id(), cost=res['duration'][0][1], length=res['distance'][0][1])
                G.add_edge(nodes[j].get_node_id(), nodes[i].get_node_id(), cost=res['duration'][1][0], length=res['distance'][1][0])

    json_data = json_graph.node_link_data(G)

    with open('graph.json', 'w') as json_file:
        json.dump(json_data, json_file, indent=4, cls=CustomEncoder)

    return G

