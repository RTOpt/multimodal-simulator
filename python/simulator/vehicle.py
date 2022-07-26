import sys

sys.path.append('C:/Users/asmam/PycharmProjects/SimulatorMultimodal/data/test')

import numpy as np
from enum import Enum
from config import *
from status import *


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
        # Patrick: Can we add a route here?
        self.id = veh_id
        self.start_time = start_time
        self.start_stop = start_stop
        self.capacity = capacity

    # Patrick: Added
    def __str__(self):
        class_string = str(self.__class__) + ": {"
        for attribute, value in self.__dict__.items():
            class_string += str(attribute) + ": " + str(value) + ",\n"
        class_string += "}"
        return class_string

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

    def __init__(self, vehicle, next_stops=[]):
        # Patrick: Added next_stops
        self.vehicle = vehicle
        # Patrick: Why is the vehicle status BOARDING and not RELEASE (or READY)?
        # OLD
        # self.status = VehicleStatus.BOARDING
        self.status = VehicleStatus.RELEASE
        self.current_stop = vehicle.start_stop
        self.next_stops = next_stops
        self.previous_stops = []
        self.onboard_requests = []
        self.assigned_requests = []
        self.alighted_requests = []
        self.load = 0

    # Patrick: Added
    def __str__(self):
        class_string = str(self.__class__) + ": {"
        for attribute, value in self.__dict__.items():
            if attribute == "vehicle":
                class_string += str(attribute) + ": " + str(value.id) + ", "
            elif attribute == "next_stops":
                class_string += str(attribute) + ": ["
                for stop in value:
                    class_string += str(stop) + ", "
                class_string += str(attribute) + ": ] "
            else:
                class_string += str(attribute) + ": " + str(value) + ", "
        class_string += "}"
        return class_string

    def update_vehicle_status(self, status):
        self.status = status

    def board(self, request):
        """Boards passengers who are ready to pick up"""

        self.onboard_requests.append(request)
        self.current_stop.board(request)
        # Patrick: Should we increase self.load?
        self.load += 1

    # OLD:
    # def depart(self, request):
    def depart(self):
        """Departs the vehicle"""
        # Patrick: Why do we have request as argument?
        # Patrick: current_stop has already been added to previous_stops when the vehicle arrived (see below).
        # If we add it here as well, won't we have it twice?
        self.previous_stops.append(self.current_stop)

        # Patrick: Is this OK?
        self.current_stop = None
        # Patrick: OLD
        # self.current_stop = request.origin

        # Patrick: Shouldn't the list of next stops be already known (i.e., right after optimizing?)
        # self.next_stops.append(request.destination)

    # OLD:
    # def arrive(self, request):
    def arrive(self):
        """Arrives the vehicle"""
        # Patrick: Why did we have request as argument? (Now removed)

        # Patrick: OLD (now, only in depart)
        # self.previous_stops.append(self.current_stop)

        # Patrick: Is this OK?
        self.current_stop = self.next_stops.pop(0)
        # Patrick: OLD
        # self.current_stop = request.destination

        # Patrick: Why did we reinitialize next_stops when the vehicle arrives?
        # OLD:
        # self.next_stops = []

    def alight(self, request):
        """Alights passengers who reached their destination from the vehicle"""
        # OLD:
        # alighted_requests = [request for request in self.onboard_requests if request.destination == self.current_stop]

        self.onboard_requests.remove(request)
        self.alighted_requests.append(request)
        self.current_stop.alight(request)
        # Patrick: Should we decrease self.load?
        self.load -= 1

    def nb_free_places(self):
        """Returns the number of places remaining in the vehicle"""
        # Patrick: Should self.load == len(self.onboard_requests)
        return self.capacity - self.load

    def assign(self, request):
        """Assigns a new request to the vehicle"""
        self.assigned_requests.append(request)

    # Patrick: OLD
    # def request_to_pickup(self):
    #     """Updates the list of request to pick up by the vehicle"""
    #     next_request_to_pickup = self.current_stop.passengers_to_board
    #     return next_request_to_pickup

    def requests_to_pickup(self):
        """Updates the list of requests to pick up by the vehicle"""
        return self.current_stop.passengers_to_board


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
        list of passengers who need to board
    boarding_passengers: list
        list of passengers who are boarding
    boarded_passengers: list
        list of passengers who are already boarded
    passengers_to_alight: list
        list of passengers to alight
        OLD: list of passengers who are alighted
    alighted_passengers: list
        list of passengers who are alighted
    location: Location
        Object of type Location referring to the location of the stop (e.g., GPS coordinates)
    """

    def __init__(self, stop_type, arrival_time, departure_time, location):
        # NEW: alighted_passengers, location
        self.stop_type = stop_type
        self.arrival_time = arrival_time
        self.departure_time = departure_time
        self.passengers_to_board = []  # mettre a jour
        self.boarding_passengers = []  # Why is it required?
        self.boarded_passengers = []
        self.passengers_to_alight = []
        self.alighted_passengers = []
        self.location = location

    # Patrick: Added
    def __str__(self):
        class_string = str(self.__class__) + ": {"
        for attribute, value in self.__dict__.items():
            if attribute == "passengers_to_board":
                class_string += str(attribute) + ": " + str(list(str(x.req_id) for x in value)) + ", "
            elif attribute == "boarding_passengers":
                class_string += str(attribute) + ": " + str(list(str(x.req_id) for x in value)) + ", "
            elif attribute == "boarded_passengers":
                class_string += str(attribute) + ": " + str(list(str(x.req_id) for x in value)) + ", "
            elif attribute == "passengers_to_alight":
                class_string += str(attribute) + ": " + str(list(str(x.req_id) for x in value)) + ", "
            elif attribute == "alighted_passengers":
                class_string += str(attribute) + ": " + str(list(str(x.req_id) for x in value)) + ", "
            else:
                class_string += str(attribute) + ": " + str(value) + ", "

        class_string += "}"
        return class_string

    def initiate_boarding(self, request):
        """Passengers who are ready to pick up in the stop get in the vehicle"""

        self.passengers_to_board.remove(request)
        self.boarding_passengers.append(request)

    def board(self, request):
        """Passenger who is boarding becomes boarded"""
        # OLD:
        # self.passengers_to_board.append(request)

        self.boarding_passengers.remove(request)
        self.boarded_passengers.append(request)

    def alight(self, request):
        """Passengers who reached their stop leave the vehicle"""
        # OLD:
        # self.passengers_to_alight.append(request)
        # self.boarded_passengers.append(request)

        self.passengers_to_alight.remove(request)
        self.alighted_passengers.append(request)


class Location(object):
    def __init__(self):
        pass


class GPSLocation(Location):
    def __init__(self, gps_coordinates):
        super().__init__()
        self.gps_coordinates = gps_coordinates

    def __str__(self):
        return self.gps_coordinates


class LabelLocation(Location):
    def __init__(self, label):
        super().__init__()
        self.label = label

    def __str__(self):
        return self.label


class RouteUpdate(object):
    def __init__(self, vehicle_id, current_stop_passengers_to_board=None, next_stops=None,
                 current_stop_departure_time=None):
        # Patrick: route_id replaced with vehicle_id
        # current stop de la route ne jamais le modifier
        self.current_stop_passengers_to_board = current_stop_passengers_to_board
        self.next_stops = next_stops
        self.current_stop_departure_time = current_stop_departure_time

        # Patrick: There is no route_id in Route. Is it vehicle_id?
        self.vehicle_id = vehicle_id

        # OLD
        # self.route_id = route_id
