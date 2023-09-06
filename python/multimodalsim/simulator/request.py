import logging
import copy

from multimodalsim.state_machine.state_machine import PassengerStateMachine

logger = logging.getLogger(__name__)


class Request(object):
    """The ``Request`` class mostly serves as a structure for storing basic
       information about the trip
       Attributes:
       ----------
       id: int
            unique id for each request
       origin: Location
            location of the origin
       destination:  Location
            location of the destination
       nb_passengers: int
            Number of passengers of the trip.
       release_time float
            time and Time at which the trip is appeared in the system.
       ready_time: float
            time at which the trip has to be picked up.
       due_time float
            time at which the trip has to be dropped off.

       """

    def __init__(self, id, origin, destination, nb_passengers, release_time,
                 ready_time, due_time, name=None):
        self.__id = id
        self.__origin = origin
        self.__destination = destination
        self.__nb_passengers = nb_passengers
        self.__ready_time = ready_time
        self.__due_time = due_time
        self.__release_time = release_time
        self.__name = name

    def __str__(self):
        class_string = str(self.__class__) + ": {"
        for attribute, value in self.__dict__.items():
            class_string += str(attribute) + ": " + str(value) + ",\n"
        class_string += "}"
        return class_string

    @property
    def id(self):
        return self.__id

    @property
    def origin(self):
        return self.__origin

    @property
    def destination(self):
        return self.__destination

    @property
    def nb_passengers(self):
        return self.__nb_passengers

    @property
    def ready_time(self):
        return self.__ready_time

    @property
    def due_time(self):
        return self.__due_time

    @property
    def release_time(self):
        return self.__release_time

    @property
    def name(self):
        return self.__name


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

    def __init__(self, id, origin, destination, nb_passengers, release_time,
                 ready_time, due_time, trip=None):
        super().__init__(id, origin, destination, nb_passengers, release_time,
                         ready_time, due_time)
        self.__assigned_vehicle = None
        self.__trip = trip

        self.__boarding_time = None
        self.__alighting_time = None

    @property
    def assigned_vehicle(self):
        return self.__assigned_vehicle

    @assigned_vehicle.setter
    def assigned_vehicle(self, vehicle):
        """Assigns a vehicle to the leg"""
        # The condition self.assigned_vehicle != vehicle has been added
        # for the case where two Optimize(Event) take place at the same time
        # (same event_time). In this case, the environment is not updated
        # between the two Optimize(Event). Therefore, the optimization
        # results of the two Optimize(Event) should be the same and,
        # as a consequence, the same vehicle will be reassigned to the trip.
        if self.__assigned_vehicle is not None \
                and self.__assigned_vehicle.id != vehicle.id:
            raise ValueError(
                "Request ({}) is already assigned to a vehicle ({}).".format(
                    self.id, self.__assigned_vehicle.id))
        self.__assigned_vehicle = vehicle

    @property
    def trip(self):
        return self.__trip

    @property
    def boarding_time(self):
        return self.__boarding_time

    @boarding_time.setter
    def boarding_time(self, boarding_time):
        self.__boarding_time = boarding_time

    @property
    def alighting_time(self):
        return self.__alighting_time

    @alighting_time.setter
    def alighting_time(self, alighting_time):
        self.__alighting_time = alighting_time

    def __str__(self):
        class_string = str(self.__class__) + ": {"
        for attribute, value in self.__dict__.items():
            # To prevent recursion error.
            if "__trip" not in attribute:
                class_string += str(attribute) + ": " + str(value) + ",\n"
        class_string += "}"
        return class_string


class Trip(Request):
    """The ``Trip`` class serves as a structure for storing basic
        information about the trips. This class inherits from Request class
        Properties
        ----------
        status: int
            Represents the different status of the passenger associated with
            the trip (PassengersStatus(Enum)).
        previous_legs: list of Leg objects
            the previous legs of the trip.
        previous_legs: Leg
            the current leg of the trip.
        next_legs: Leg
            the next legs of the trip.
    """

    def __init__(self, id, origin, destination, nb_passengers, release_time,
                 ready_time, due_time, name=None):
        super().__init__(id, origin, destination, nb_passengers, release_time,
                         ready_time, due_time, name)

        self.__previous_legs = []
        self.__current_leg = None
        self.__next_legs = []

        self.__state_machine = PassengerStateMachine(self)

    @property
    def status(self):
        return self.__state_machine.current_state.status

    @property
    def state_machine(self):
        return self.__state_machine

    @property
    def previous_legs(self):
        return self.__previous_legs

    @property
    def current_leg(self):
        return self.__current_leg

    @current_leg.setter
    def current_leg(self, current_leg):
        self.__current_leg = current_leg

    @current_leg.deleter
    def current_leg(self):
        del self.__current_leg

    @property
    def next_legs(self):
        return self.__next_legs

    @next_legs.setter
    def next_legs(self, next_legs):
        self.__next_legs = next_legs

    # @next_legs.deleter
    # def next_legs(self):
    #     del self.__next_legs

    def assign_legs(self, legs):

        self.__next_legs = legs

        # if legs is not None and len(legs) > 1:
        #     # self.__current_leg = legs[0]
        #     # self.__next_legs = legs[1:]
        #
        # elif legs is not None and len(legs) > 0:
        #     self.__current_leg = legs[0]
        #     self.__next_legs = []
        # else:
        #     self.__current_leg = None
        #     self.__next_legs = []

    def finish_current_leg(self):
        self.__previous_legs.append(self.current_leg)
        self.current_leg = None

    def start_next_leg(self):
        if len(self.next_legs) > 0:
            self.current_leg = self.next_legs.pop(0)
        else:
            raise ValueError(
                "Trip ({}) does not have any next leg.".format(self.id))

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == "_Route__previous_legs":
                setattr(result, k, [])
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result


class PassengerUpdate(object):
    def __init__(self, vehicle_id, request_id, next_legs=None):
        self.assigned_vehicle_id = vehicle_id
        self.request_id = request_id
        self.next_legs = next_legs
