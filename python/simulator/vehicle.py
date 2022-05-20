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
        self.status = VehicleStatus.INACTIVE
        self.start_time = start_time
        self.start_stop = start_stop
        self.capacity = capacity


class Route(Vehicle):
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

    def __init__(self, id, start_time, current_stop, capacity, next_stops=[], previous_stops=[]):
        Vehicle.__init__(self, id, start_time, current_stop, capacity)
        self.id = id
        self.current_stop = current_stop
        self.next_stops = next_stops
        self.previous_stops = previous_stops
        self.onboard_requests = []
        self.pickup_requests = []
        self.alighted_requests = []
        self.load = 0

    def board(self):
        """Passengers that are ready to pick up in the stop get in the vehicle"""
        for request in self.pickup_requests:
            self.onboard_requests.append(request)

    def depart(self):
        """Departs the vehicle"""
        self.previous_stops.append(self.current_stop)
        self.current_stop = self.next_stops[0]
        self.next_stops = self.next_stops.pop(0)

    def arrive(self):
        """Arrives the vehicle"""
        self.previous_stops.append(self.current_stop)
        self.current_stop = self.next_stops[0]
        self.next_stops = self.next_stops.pop(0)

    def alight(self):
        """Passengers that reached their destination leave the vehicle"""
        alighted_requests = [request for request in self.onboard_requests if request.destination == self.current_stop]
        for request in alighted_requests:
            self.onboard_requests.remove(request)

    def nb_free_places(self):
        """Returns the number of places remaining in the vehicle"""
        return self.capacity - self.load

    def assign(self, request):
        self.pickup_requests.append(request)






