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

def read_file_bus_requests(file_name):
    request_data_list = []
    with open(file_name, 'r') as rFile:
        reader = csv.reader(rFile, delimiter=';')
        next(reader, None)
        nb_requests = 1
        for row in reader:
            # À faire dans PassengerRelease
            # env.add_request(nb_requests, str(row[0]), str(row[1]), int(row[2]),
            #                 int(row[3]), int(row[4]), int(row[5]))

            request_data_dict = {
                'nb_requests': nb_requests,
                'origin': LabelLocation(str(row[0])),
                'destination': LabelLocation(str(row[1])),
                'nb_passengers': int(row[2]),
                'ready_time': int(row[3]),
                'due_time': int(row[4]),
                'release_time': int(row[5])
            }

            request_data_list.append(request_data_dict)

            nb_requests += 1

    return request_data_list


def read_file_bus_vehicles(file_name):
    BOARDING_TIME = 1
    TRAVEL_TIME = 2

    vehicle_data_list = []

    with open(file_name, 'r') as rFile:
        reader = csv.reader(rFile, delimiter=';')
        next(reader, None)

        for row in reader:
            vehicle_id = int(row[0])
            start_time = int(row[1])

            # stop_ids_list = list(map(lambda x: str(x), list(ast.literal_eval(row[2]))))
            stop_ids_list = list(str(x) for x in list(ast.literal_eval(row[2])))
            start_stop_location = LabelLocation(stop_ids_list[0])

            stop_arrival_time = start_time
            stop_departure_time = stop_arrival_time + BOARDING_TIME
            start_stop = Stop(None, start_time, stop_departure_time, start_stop_location)

            next_stops = []
            for next_stop_id in stop_ids_list[1:]:
                next_stop_location = LabelLocation(next_stop_id)
                # Ajouter les temps de départ et d'arrivée

                stop_arrival_time = stop_departure_time + TRAVEL_TIME
                stop_departure_time = stop_arrival_time + BOARDING_TIME
                next_stop = Stop(None, stop_arrival_time, stop_departure_time, next_stop_location)
                next_stops.append(next_stop)

            capacity = int(row[3])

            # À faire dans VehicleReady
            # env.add_vehicle(vehicle_id, vehicle_start_time, vehicle_start_stop, vehicle_capacity, vehicle_next_stops)

            vehicle_data_dict = {
                'vehicle_id': vehicle_id,
                'start_time': start_time,
                'start_stop': start_stop,
                'capacity': capacity,
                'next_stops': next_stops
            }

            vehicle_data_list.append(vehicle_data_dict)

    return vehicle_data_list
