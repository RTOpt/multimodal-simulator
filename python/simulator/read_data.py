import csv
import ast
import networkx

from network import Node
from request import Request
from vehicle import Vehicle
from status import *
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
            vehicle_id = int(row[0])
            vehicle_start_time = int(row[1])
            start_stop_location = GPSLocation(ast.literal_eval(row[2]))
            vehicle_capacity = int(row[3])

            vehicle_start_stop = Stop(None, vehicle_start_time, None, start_stop_location)
            env.add_vehicle(vehicle_id, vehicle_start_time, vehicle_start_stop, vehicle_capacity)


def read_file_nodes(file_name):
    nodes = []
    with open(file_name, 'r') as rFile:
        reader = csv.reader(rFile, delimiter=';')
        next(reader, None)
        for row in reader:
            nodes.append(Node(row[0], ast.literal_eval(row[1])))

    return nodes


####### BUS ######

def read_file_bus_requests(file_name, env):
    with open(file_name, 'r') as rFile:
        reader = csv.reader(rFile, delimiter=';')
        next(reader, None)
        nb_requests = 1
        for row in reader:
            env.add_request(nb_requests, str(row[0]), str(row[1]), int(row[2]),
                            int(row[3]), int(row[4]), int(row[5]))
            nb_requests += 1


def read_file_bus_vehicles(file_name, env):
    with open(file_name, 'r') as rFile:
        reader = csv.reader(rFile, delimiter=';')
        next(reader, None)

        for row in reader:
            vehicle_id = int(row[0])
            vehicle_start_time = int(row[1])

            stop_ids_list = list(map(lambda x: str(x), list(ast.literal_eval(row[2]))))
            start_stop_location = LabelLocation(stop_ids_list[0])
            vehicle_start_stop = Stop(None, vehicle_start_time, None, start_stop_location)

            vehicle_next_stops = []
            for next_stop_id in stop_ids_list[1:]:
                next_stop_location = LabelLocation(next_stop_id)
                vehicle_next_stop = Stop(None, None, None, next_stop_location)
                vehicle_next_stops.append(vehicle_next_stop)

            vehicle_capacity = int(row[3])

            env.add_vehicle(vehicle_id, vehicle_start_time, vehicle_start_stop, vehicle_capacity, vehicle_next_stops)


def read_file_bus_stops(file_name):
    # Patrick: Do we actually need it?
    pass
