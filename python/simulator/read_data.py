
import csv
import ast
import networkx

from network import Node
from request import Request
from vehicle import Vehicle
from statuts import *
from environment import *


def read_file_requests(file_name, env):
    """ read request from a file
           format:
           requestId, origin, destination, nb_passengers, ready_date, due_date, release_date
    """
    '''
    requests = {}
    with open(file_name, 'r') as rFile:
        reader = csv.reader(rFile, delimiter=';')
        next(reader, None)
        nb_request = 0
        for row in reader:
            requests.update({nb_request:Request(nb_request, ast.literal_eval(row[0]), ast.literal_eval(row[1]), int(row[2]),
                                    int(row[3]), int(row[4]), int(row[5]))})
            nb_request += 1
    '''
    with open(file_name, 'r') as rFile:
        reader = csv.reader(rFile, delimiter=';')
        next(reader, None)
        nb_requests = 1
        for row in reader:
            env.add_request(nb_requests, ast.literal_eval(row[0]), ast.literal_eval(row[1]), int(row[2]),
                                    int(row[3]), int(row[4]), int(row[5]))
            nb_requests += 1

def read_file_vehicles(file_name, env):
    with open(file_name, 'r') as rFile:
        reader = csv.reader(rFile, delimiter=';')
        next(reader, None)

        for row in reader:
            env.add_vehicle( int(row[0]), int(row[1]), ast.literal_eval(row[2]), int(row[3]))


def read_file_nodes(file_name):
    nodes = []
    with open(file_name, 'r') as rFile:
        reader = csv.reader(rFile, delimiter=';')
        next(reader, None)
        for row in reader:
            nodes.append(Node(row[0], ast.literal_eval(row[1])))

    return nodes