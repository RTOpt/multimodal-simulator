import sys
sys.path.append('C:/Users/asmam/PycharmProjects/SimulatorMultimodal/data/test')

import numpy as np
from enum import Enum
from config import *
from statuts import *

class VehicleStatus(Enum):
    """Represents the different status of Vehicles"""
    ACTIVE = 1
    INACTIVE = 2
    BOARDING = 3
    ALIGHTING = 5




class Vehicle(object):
    """The ``Vehicle`` class mostly serves as a structure for storing basic
        information about the vehicles.
        Properties
        ----------
        vehicle_id: int
            unique id
        vehicle_status: int
            If the vehicle is in circulation between the two terminals it is active.
            If the vehicle did not start its run or reached the last terminal and
            emptied all its passengers, it is inactive.
        vehicle start_time: int
            time when the vehicle is ready to start
        start_stop: tuple of floats (x,y)
            GPS coordinates of the start position of the vehicle
        capacity: int
            Maximum number of passengers that can fit the vehicle
    """

    def __init__(self, veh_id, start_time, start_stop, capacity):
        self.id = veh_id
        self.start_time = start_time
        self.start_stop = start_stop
        self.capacity = capacity
        self.route = None

    def new_route(self):
        if self.route is not None:
            raise ValueError("Vehicle (%d) has already route." % self.id)
        self.route = Route(self)
        return self.route


class Route(object):
    """The ``Route`` class serves as a structure for storing basic
    information about the routes. This class inherits from Vehicle class.
       Properties
       ----------
        onboard_requests: list
            Ids of requests currently on board.
        current_stops: list of tuples of floats (x,y)
           each element of the list corresponds to the GPS coordinates of a current stop of the vehicle.
        next_stops: list of tuples of floats (x,y)
           each element of the list corresponds to the GPS coordinates of a next stop to reach by the vehicle.
        previous_stops: list of tuples of floats (x,y)
           ach element of the list corresponds to the GPS coordinates of a previous stop visited by the vehicle.
        load: int
            Number of passengers on board
        picking_requests: list
            Ids of requests currently waiting for this vehicle to pick
    """

    def __init__(self, vehicle):
        self.vehicle = vehicle
        self.status = VehicleStatus.BOARDING
        self.current_stop = vehicle.start_stop
        self.next_stops = []
        self.previous_stops = []
        self.onboard_requests = []
        self.assigned_requests = []
        self.alighted_requests = []
        self.load = 0

    def update_vehicle_status(self, status):
        self.status = status

    def board(self, request):
        """Boards passengers who are ready to pick up"""
        self.onboard_requests.append(request)

    def depart(self, request):
        """Departs the vehicle"""
        self.previous_stops.append(self.current_stop)
        self.current_stop = request.origin
        self.next_stops.append(request.destination)

    def arrive(self, request):
        """Arrives the vehicle"""
        self.previous_stops.append(self.current_stop)
        self.current_stop = request.destination
        self.next_stops = []

    def alight(self):
        """Alights passengers who reached their destination from the vehicle"""
        alighted_requests = [request for request in self.onboard_requests if request.destination == self.current_stop]
        for request in alighted_requests:
            self.onboard_requests.remove(request)

    def nb_free_places(self):
        """Returns the number of places remaining in the vehicle"""
        return self.capacity - self.load

    def assign(self, request):
        """Assigns a new request to the vehicle"""
        self.assigned_requests.append(request)

    def request_to_pickup(self):
        """Updates the list of request to pick up by the vehicle"""
        next_request_to_pickup = self.assigned_requests[0]
        return next_request_to_pickup

class Stop(object):
    """A stop is located somewhere along the network.  New requests
    arrive at the stop.
    ----------
    StopType
    arrival_time: int
        Date and time at which the vehicle arrives the stop
    departure_time: int
        Date and time at which the vehicle leaves the stop
    passengers_to_board: list
        list of passengers who are boarding
    boarded_passengers: list
        list of passengers who are already boarded
    passengers_to_alight: list
        list of passengers who are alighted
    """

    def __init__(self, stop_type, arrival_time, departure_time):
        self.stop_type = stop_type
        self.arrival_time = arrival_time
        self.departure_time = departure_time
        self.passengers_to_board = [] #mettre a jour
        self.boarded_passengers = []
        self.passengers_to_alight = []

    def board(self, request):
        """Passengers who are ready to pick up in the stop get in the vehicle"""
        self.passengers_to_board.append(request)

    def alight(self, request):
        """Passengers who reached their stop leave the vehicle"""
        self.passengers_to_alight.append(request)
        self.boarded_passengers.append(request)

class RouteUpdate(object):
    def __init__(self, passengers_to_board, next_stops, route_id):
        #current stop de la route ne jamais le modifier
        self.passengers_to_board_at_current_stop = passengers_to_board
        self.next_stops = next_stops
        self.route_id = route_id

