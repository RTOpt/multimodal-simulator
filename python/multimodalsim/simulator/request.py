import logging
import copy
from typing import Optional

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
        tags: list[str]
            List of tags associated with the request.
    """

    def __init__(self, id: str | int, origin: Location, destination: Location,
                 nb_passengers: int, release_time: float, ready_time: float,
                 due_time: float, name: Optional[str] = None,
                 tags: Optional[list[str]] = None) -> None:
        self.__id = id
        self.__origin = origin
        self.__destination = destination
        self.__nb_passengers = nb_passengers
        self.__ready_time = ready_time
        self.__due_time = due_time
        self.__release_time = release_time
        self.__name = name
        self.__tags = [] if tags is None else tags

    def __str__(self) -> str:
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

    @origin.setter
    def origin(self, location: Location) -> None:
        self.__origin = location

    @property
    def destination(self) -> Location:
        return self.__destination

    @destination.setter
    def destination(self, location: Location) -> None:
        self.__destination = location

    @property
    def nb_passengers(self) -> int:
        return self.__nb_passengers

    @property
    def ready_time(self) -> float:
        return self.__ready_time

    @property
    def due_time(self) -> float:
        return self.__due_time

    @property
    def release_time(self) -> float:
        return self.__release_time

    @property
    def name(self) -> Optional[str]:
        return self.__name

    @property
    def tags(self) -> list[str]:
        return self.__tags


class Leg(Request):
    """The ``Leg`` class serves as a structure for storing basic
        information about the legs. This class inherits from Request class
        Properties
        ----------
        assigned_vehicle: Vehicle
            Vehicle assigned to the leg.
        trip: Trip
            Trip to which belongs the leg.
        boarding_time: float
            Time at which the leg boarded the assigned vehicle.
        alighting_time: float
            Time at which the leg alighted from the assigned vehicle.
    """

    def __init__(self, id: str | int, origin: Location, destination: Location,
                 nb_passengers: int, release_time: float, ready_time: float,
                 due_time: float, trip: Optional['Trip'] = None):
        super().__init__(id, origin, destination, nb_passengers, release_time,
                         ready_time, due_time)
        self.__assigned_vehicle = None
        self.__trip = trip

        self.__boarding_time = None
        self.__alighting_time = None

    @property
    def assigned_vehicle(self) -> Optional['vehicle_module.Vehicle']:
        return self.__assigned_vehicle

    @assigned_vehicle.setter
    def assigned_vehicle(self,
                         vehicle: Optional['vehicle_module.Vehicle']) -> None:
        """Assigns a vehicle to the leg"""
        self.__assigned_vehicle = vehicle

    @property
    def trip(self) -> Optional['Trip']:
        return self.__trip

    @trip.setter
    def trip(self, trip: Optional['Trip']) -> None:
        self.__trip = trip

    @property
    def boarding_time(self) -> Optional[float]:
        return self.__boarding_time

    @boarding_time.setter
    def boarding_time(self, boarding_time: Optional[float]) -> None:
        self.__boarding_time = boarding_time

    @property
    def alighting_time(self) -> Optional[float]:
        return self.__alighting_time

    @alighting_time.setter
    def alighting_time(self, alighting_time: Optional[float]) -> None:
        self.__alighting_time = alighting_time

    def __str__(self) -> str:
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
                 nb_passengers: int, release_time: float, ready_time: float,
                 due_time: float, name: Optional[str] = None) -> None:
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
    def previous_legs(self) -> list[Leg]:
        return self.__previous_legs

    @property
    def current_leg(self) -> Optional[Leg]:
        return self.__current_leg

    @current_leg.setter
    def current_leg(self, current_leg: Optional[Leg]):
        self.__current_leg = current_leg

    @current_leg.deleter
    def current_leg(self) -> None:
        del self.__current_leg

    @property
    def next_legs(self) -> list[Leg]:
        return self.__next_legs

    @next_legs.setter
    def next_legs(self, next_legs: list[Leg]) -> None:
        self.__next_legs = next_legs

    def assign_legs(self, legs: list[Leg]) -> None:
        self.__next_legs = legs

    def finish_current_leg(self) -> None:
        self.__previous_legs.append(self.current_leg)
        self.current_leg = None

    def start_next_leg(self) -> None:
        if len(self.next_legs) > 0:
            self.current_leg = self.next_legs.pop(0)
        else:
            raise ValueError(
                "Trip ({}) does not have any next leg.".format(self.id))

    def __deepcopy__(self, memo: dict) -> 'Trip':
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
    def __init__(self, request_id: str | int, vehicle_id: Optional[str | int],
                 current_leg: Optional[Leg] = None,
                 next_legs: Optional[list[Leg]] = None) -> None:
        self.request_id = request_id
        self.assigned_vehicle_id = vehicle_id
        self.current_leg = current_leg
        self.next_legs = next_legs
