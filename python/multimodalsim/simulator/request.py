import logging
import copy
from typing import Optional, List

import multimodalsim.state_machine.state_machine as state_machine
from multimodalsim.simulator.stop import Location
import multimodalsim.simulator.vehicle as vehicle_module
from multimodalsim.state_machine.state_machine import PassengerStateMachine
from multimodalsim.state_machine.status import PassengerStatus


logger = logging.getLogger(__name__)


class Request:
    """The ``Request`` class mostly serves as a structure for storing basic
       information about the passengers.
       Attributes:
       ----------
       id: int
            Unique id for each request
       origin: Location
            Location of the origin
       destination:  Location
            Location of the destination
       nb_passengers: int
            Number of passengers of the trip.
       release_time float
            Time at which the trip appears in the system.
       ready_time: float
            Time at which the trip is available to be picked up.
       due_time: float
            Time at which the trip has to be dropped off.
       name: string
            Name of the passenger.
       """

    def __init__(self, id: str | int, origin: Location, destination: Location,
                 nb_passengers: int, release_time: int, ready_time: int,
                 due_time: int, name: Optional[str] = None):
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
    def id(self) -> str | int:
        return self.__id

    @property
    def origin(self) -> Location:
        return self.__origin

    @property
    def destination(self) -> Location:
        return self.__destination

    @property
    def nb_passengers(self) -> int:
        return self.__nb_passengers

    @property
    def ready_time(self) -> int:
        return self.__ready_time

    @property
    def due_time(self) -> int:
        return self.__due_time

    @property
    def release_time(self) -> int:
        return self.__release_time

    @property
    def name(self) -> Optional[str]:
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

    def __init__(self, id: str | int, origin: Location, destination: Location,
                 nb_passengers: int, release_time: int, ready_time: int,
                 due_time: int, trip: Optional['Trip'] = None):
        super().__init__(id, origin, destination, nb_passengers, release_time,
                         ready_time, due_time)
        self.__assigned_vehicle = None
        self.__trip = trip

        self.__boarding_time = None
        self.__alighting_time = None

    @property
    def assigned_vehicle(self) -> 'vehicle_module.Vehicle':
        return self.__assigned_vehicle

    @assigned_vehicle.setter
    def assigned_vehicle(self, vehicle: 'vehicle_module.Vehicle'):
        """Assigns a vehicle to the leg"""
        self.__assigned_vehicle = vehicle

    @property
    def trip(self) -> 'Trip':
        return self.__trip

    @property
    def boarding_time(self) -> int:
        return self.__boarding_time

    @boarding_time.setter
    def boarding_time(self, boarding_time: int):
        self.__boarding_time = boarding_time

    @property
    def alighting_time(self) -> int:
        return self.__alighting_time

    @alighting_time.setter
    def alighting_time(self, alighting_time: int):
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
            the trip (PassengerStatus(Enum)).
        previous_legs: list of Leg objects
            the previous legs of the trip.
        previous_legs: Leg
            the current leg of the trip.
        next_legs: Leg
            the next legs of the trip.
    """

    def __init__(self, id: str | int, origin: Location, destination: Location,
                 nb_passengers: int, release_time: int, ready_time: int,
                 due_time: int, name: Optional[str] = None):
        super().__init__(id, origin, destination, nb_passengers, release_time,
                         ready_time, due_time, name)

        self.__previous_legs = []
        self.__current_leg = None
        self.__next_legs = []

        self.__state_machine = PassengerStateMachine(self)

    @property
    def status(self) -> PassengerStatus:
        return self.__state_machine.current_state.status

    @property
    def state_machine(self) -> 'state_machine.PassengerStateMachine':
        return self.__state_machine

    @property
    def previous_legs(self) -> List[Leg]:
        return self.__previous_legs

    @property
    def current_leg(self) -> Optional[Leg]:
        return self.__current_leg

    @current_leg.setter
    def current_leg(self, current_leg: Optional[Leg]):
        self.__current_leg = current_leg

    @current_leg.deleter
    def current_leg(self):
        del self.__current_leg

    @property
    def next_legs(self) -> List[Leg]:
        return self.__next_legs

    @next_legs.setter
    def next_legs(self, next_legs: List[Leg]):
        self.__next_legs = next_legs

    def assign_legs(self, legs: List[Leg]):
        self.__next_legs = legs

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


class PassengerUpdate:
    def __init__(self, vehicle_id: str | int, request_id: str | int,
                 next_legs: Optional[List[Leg]] = None):
        self.assigned_vehicle_id = vehicle_id
        self.request_id = request_id
        self.next_legs = next_legs
