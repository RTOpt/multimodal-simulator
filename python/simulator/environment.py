from vehicle import *
from request import *


class Environment(object):

    def __init__(self, optimization, network=None):
        # Patrick: Added optimization, status
        self.current_time = 0
        self.requests = []
        self.assigned_requests = []
        self.non_assigned_requests = []
        self.vehicles = []
        self.assigned_vehicles = []
        self.non_assigned_vehicles = []
        self.network = network
        self.optimization = optimization

    def get_requests(self):
        return self.requests

    def get_request_by_id(self, req_id):
        for req in self.requests:
            if req.req_id == req_id:
                return req

    def add_request(self, nb_requests, origin, destination, nb_passengers, ready_time, due_time, release_time):
        """ Adds a new request to the requests list"""
        # new_req = Request(nb_requests, origin, destination, nb_passengers, ready_time, due_time, release_time)
        new_req = Trip(nb_requests, origin, destination, nb_passengers, ready_time, due_time, release_time)
        self.requests.append(new_req)

        return new_req

    def remove_request(self, request_id):
        """ Removes a request from the requests list based on its id"""
        self.requests = [item for item in self.requests if item.attribute != request_id]

    def get_vehicles(self):
        return self.vehicles

    def get_vehicle_by_id(self, veh_id):
        for veh in self.vehicles:
            if veh.id == veh_id:
                return veh

    def add_vehicle(self, veh_id, start_time, start_stop, capacity):
        """ Adds a new vehicle to the vehicles list"""
        new_veh = Vehicle(veh_id, start_time, start_stop, capacity)
        self.vehicles.append(new_veh)

        return new_veh

    def remove_vehicle(self, vehicle_id):
        """ Removes a vehicle from the vehicles list based on its id"""
        self.vehicles = [item for item in self.vehicles if item.attribute != vehicle_id]

    def get_non_assigned_requests(self):
        # Patrick: OLD
        # for req in self.requests:
        #     if req.status == PassengersStatus.RELEASE:
        #         self.non_assigned_requests.append(req)

        self.update_non_assigned_requests()

        return self.non_assigned_requests

    def get_non_assigned_vehicles(self):
        # Patrick: OLD
        # for veh in self.vehicles:
        #     if veh.route.status == VehicleStatus.BOARDING:
        #         self.non_assigned_vehicles.append(veh)

        self.update_non_assigned_vehicles()

        return self.non_assigned_vehicles

    def update_non_assigned_requests(self):
        # Patrick: Shouldn't we reinitialize the list non_assigned_requests every time?
        self.non_assigned_requests = []  # Was not there before
        self.assigned_requests = []  # Was not there before

        # À faire par les événements
        for req in self.requests:
            # Shouldn't we consider a request with PassengersStatus.ASSIGNMENT a non-assigned request as well?
            if req.status == PassengersStatus.RELEASE:
                self.non_assigned_requests.append(req)
            else:
                self.assigned_requests.append(req)
            # OLD
            # if req.status == PassengersStatus.RELEASE:
            #     self.non_assigned_requests.append(req)
        return self.non_assigned_requests

    def update_non_assigned_vehicles(self):
        # Patrick: Shouldn't we reinitialize the list non_assigned_vehicles every time?
        self.non_assigned_vehicles = []  # Was not there before
        self.assigned_vehicles = []  # Was not there before

        for veh in self.vehicles:
            # Patrick: Shouldn't the vehicle status be RELEASE (or READY)?
            # if veh.route.status == VehicleStatus.RELEASE or veh.route.status == VehicleStatus.COMPLETE:
            if veh.route.status == VehicleStatus.RELEASE or veh.route.status == VehicleStatus.BOARDING:
                self.non_assigned_vehicles.append(veh)
            else:
                self.assigned_vehicles.append(veh)
            # OLD
            # if veh.route.status == VehicleStatus.BOARDING:
            #     self.non_assigned_vehicles.append(veh)