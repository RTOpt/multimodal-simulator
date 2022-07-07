from typing import List, Any

from vehicle import *
from request import *


class Environment(object):

    def __init__(self, network=None):
        self.requests = []
        self.assigned_requests = []
        self.vehicles = []
        self.network = network


    def get_requests(self):
        return self.requests

    def add_request(self, nb_requests, origin, destination, nb_passengers, ready_time, due_time, release_time):
        """ Adds a new request to the requests list"""
        new_req = Request(nb_requests, origin, destination, nb_passengers, ready_time, due_time, release_time)
        self.requests.append(new_req)

    def remove_request(self, request_id):
        """ Removes a request from the requests list based on its id"""
        self.requests = [item for item in self.requests if item.attribute != request_id]


    def get_vehicles(self):
        return self.vehicles

    def add_vehicle(self, veh_id, start_time , start_stop, capacity):
        """ Adds a new vehicle to the vehicles list"""
        new_veh = Vehicle(veh_id, start_time, start_stop, capacity)
        self.vehicles.append(new_veh)

    def remove_vehicle(self, vehicle_id):
        """ Removes a vehicle from the vehicles list based on its id"""
        self.vehicles = [item for item in self.vehicles if item.attribute != vehicle_id]


    def get_non_assigned_requests(self):
        non_assigned_requests = []
        for req in self.requests:
            if req.status == PassengersStatus.RELEASE:
                non_assigned_requests.append(req)
        return non_assigned_requests


    def get_free_vehicles(self):
        free_vehicles = []
        for veh in self.vehicles:
            if veh.status.name == 'INACTIVE':
                free_vehicles.append(veh)

        return free_vehicles


