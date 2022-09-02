from status import *


class Request(object):
    """The ``Request`` class mostly serves as a structure for storing basic
       information about the request
       Attributes:
       ----------
       requestId: int
            unique id for each request
       status: category
            Request status : {PENDING:1, PICKING:2, ONBOARD:3, COMPLET:4}
       origin: tuple of floats (x,y)
            GPS coordinates of the origin point of the request.
       destination:  tuple of floats (x,y)
            GPS coordinates of the destination point of the request.
       travel_duration: float
            Travel time between the origin and destination
       travel_distance: float
            Travel distance between the origin and destination
       nb_passengers: int
            Number of passengers of the request.
       ready_time: float
            time at which the request has to be picked up.
       due_time float
            time at which the request has to be dropped off.
       release_time float
            time and Time at which the request is appeared in the system.
       """

    def __init__(self, req_id, origin, destination, nb_passengers, ready_time, due_time, release_time):
        self.req_id = req_id
        self.status = PassengersStatus.RELEASE
        self.origin = origin
        self.destination = destination
        self.nb_passengers = nb_passengers
        self.ready_time = ready_time
        self.due_time = due_time
        self.release_time = release_time
        self.assigned_vehicle = None
        self.next_vehicles = None
        self.previous_vehicles = []
        self.path = None

    def __str__(self):
        class_string = str(self.__class__) + ": {"
        for attribute, value in self.__dict__.items():
            class_string += str(attribute) + ": " + str(value) + ",\n"
        class_string += "}"
        return class_string

    def update_passenger_status(self, status):
        self.status = status

    def assign_vehicle(self, vehicle):
        """Assigns a vehicle to transport the passengers of the request"""
        # Patrick: I added the condition self.assigned_vehicle != vehicle for the case where two Optimize(Event) take
        # place at the same time (same event_time). In this case, the environment is not updated between the two
        # Optimize(Event). Therefore, the optimization results of the two Optimize(Event) should be the same and, as a
        # consequence, the same vehicle will be reassigned to the request.
        if self.assigned_vehicle is not None and self.assigned_vehicle != vehicle:
            raise ValueError("Request (%d) is already assigned to a vehicle." % self.req_id)
        self.assigned_vehicle = vehicle
        self.status = PassengersStatus.ASSIGNED
        return self.assigned_vehicle

    def assign_route(self, path):
        """Assigns a route to the request"""
        # Patrick: What type of object is path? Is it a Route? If so, why do we need it? Request already has the
        # attribute assigned_vehicle, which contains the Route. If it is just a list of Node objects, I do not think,
        # that we really need it.
        self.path = path


class PassengerUpdate(object):
    def __init__(self, vehicle_id, request_id, next_vehicles_ids=None):
        self.assigned_vehicle_id = vehicle_id
        self.request_id = request_id
        self.next_vehicles_ids = next_vehicles_ids


class Trip(Request):
    """The ``Trip`` class serves as a structure for storing basic
        information about the trips. This class inherits from Request class
        Properties
        ----------
        affected_vehicle:int
            Id of affected vehicle to run the request.
        origin_affected_request: tuple of floats (x,y)
            GPS coordinates of the origin point of the affected request.
        destination_affected_request: tuple of floats (x,y)
            GPS coordinates of the destination point of the affected request.
    """

    def __init__(self):
        self.affected_vehicle = 0
        self.origin_affected_request = 0
        self.destination_affected_request = 0
