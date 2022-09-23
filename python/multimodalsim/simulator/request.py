import logging

from multimodalsim.simulator.status import PassengersStatus

logger = logging.getLogger(__name__)


class Request(object):
    """The ``Request`` class mostly serves as a structure for storing basic
       information about the trip
       Attributes:
       ----------
       req_id: int
            unique id for each request
       origin: Location
            location of the origin
       destination:  Location
            location of the destination
       nb_passengers: int
            Number of passengers of the trip.
       ready_time: float
            time at which the trip has to be picked up.
       due_time float
            time at which the trip has to be dropped off.
       release_time float
            time and Time at which the trip is appeared in the system.
       """

    def __init__(self, req_id, origin, destination, nb_passengers, ready_time, due_time, release_time):
        self.req_id = req_id
        self.origin = origin
        self.destination = destination
        self.nb_passengers = nb_passengers
        self.ready_time = ready_time
        self.due_time = due_time
        self.release_time = release_time

        # Peut-être enlever
        self.path = None

    def __str__(self):
        class_string = str(self.__class__) + ": {"
        for attribute, value in self.__dict__.items():
            class_string += str(attribute) + ": " + str(value) + ",\n"
        class_string += "}"
        return class_string

    def assign_route(self, path):
        """Assigns a route to the trip"""
        # Patrick: What type of object is path? Is it a Route? If so, why do we need it? Request already has the
        # attribute assigned_vehicle, which contains the Route. If it is just a list of Node objects, I do not think,
        # that we really need it.
        self.path = path


class Leg(Request):
    """The ``Leg`` class serves as a structure for storing basic
        information about the legs. This class inherits from Request class
        Properties
        ----------
        assigned_vehicle: Vehicle
            the vehicle assigned to the leg.
        trip: Trip
            the trip to which belongs the leg.
    """

    def __init__(self, req_id, origin, destination, nb_passengers, ready_time, due_time, release_time, trip):
        super().__init__(req_id, origin, destination, nb_passengers, ready_time, due_time, release_time)
        self.assigned_vehicle = None  # None au moment du split
        self.trip = trip

    def assign_vehicle(self, vehicle):
        """Assigns a vehicle to the leg"""
        # Patrick: I added the condition self.assigned_vehicle != vehicle for the case where two Optimize(Event) take
        # place at the same time (same event_time). In this case, the environment is not updated between the two
        # Optimize(Event). Therefore, the optimization results of the two Optimize(Event) should be the same and, as a
        # consequence, the same vehicle will be reassigned to the trip.
        if self.assigned_vehicle is not None and self.assigned_vehicle.id != vehicle.id:
            raise ValueError("Request ({}) is already assigned to a vehicle ({}).".format(self.req_id,
                                                                                          self.assigned_vehicle.id))
        self.assigned_vehicle = vehicle
        return self.assigned_vehicle

    def __str__(self):
        class_string = str(self.__class__) + ": {"
        for attribute, value in self.__dict__.items():
            # To prevent recursion error.
            if attribute != "trip":
                class_string += str(attribute) + ": " + str(value) + ",\n"
        class_string += "}"
        return class_string


class Trip(Request):
    """The ``Trip`` class serves as a structure for storing basic
        information about the trips. This class inherits from Request class
        Properties
        ----------
        status: int
            Represents the different status of the passenger associated with the trip (PassengersStatus(Enum)).
        previous_legs: list of Leg objects
            the previous legs of the trip.
        previous_legs: Leg
            the current leg of the trip.
        next_legs: Leg
            the next legs of the trip.
    """

    def __init__(self, req_id, origin, destination, nb_passengers, ready_time, due_time, release_time):
        super().__init__(req_id, origin, destination, nb_passengers, ready_time, due_time, release_time)

        self.status = PassengersStatus.RELEASE

        self.previous_legs = []
        self.current_leg = None
        self.next_legs = None

    def update_status(self, status):
        self.status = status

    def assign_legs(self, legs):

        if legs is not None and len(legs) > 1:
            self.current_leg = legs[0]
            self.next_legs = legs[1:]
        elif legs is not None and len(legs) > 0:
            self.current_leg = legs[0]
            self.next_legs = None
        else:
            self.current_leg = None
            self.next_legs = None


class PassengerUpdate(object):
    def __init__(self, vehicle_id, request_id, current_leg, next_legs=None):
        self.assigned_vehicle_id = vehicle_id
        self.request_id = request_id
        self.current_leg = current_leg
        self.next_legs = next_legs