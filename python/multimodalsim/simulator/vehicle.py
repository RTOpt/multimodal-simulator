import logging
import copy
from typing import Optional

import multimodalsim.state_machine.state_machine as state_machine
import multimodalsim.simulator.request as request
from multimodalsim.simulator.stop import Stop, Location
from multimodalsim.state_machine.status import PassengerStatus, VehicleStatus

logger = logging.getLogger(__name__)


class Vehicle:
    """The ``Vehicle`` class mostly serves as a structure for storing basic
        information about the vehicles.
        Properties
        ----------
        id: int
            Unique id
        start_time: float
            Time at which the vehicle is ready to start
        start_stop: Stop
            Stop at which the vehicle starts.
        capacity: int
            Maximum number of passengers that can fit in the vehicle
        release_time: int
            Time at which the vehicle is added to the environment.
        mode: string
            The name of the vehicle mode.
        reusable: Boolean
            Specifies whether the vehicle can be reused after it has traveled
            the current route (i.e., its route has no more next stops).
        position: Location
            Most recent location of the vehicle. Note that the position is not
            updated at every time unit; it is updated only when the event
            VehicleUpdatePositionEvent is processed.
        polylines: dict
            A dictionary that specifies for each stop id (key),
            the polyline until the next stop.
        status: int
            Represents the different status of the vehicle
            (VehicleStatus(Enum)).
    """

    MAX_TIME = 7 * 24 * 3600

    def __init__(self, veh_id: str | int, start_time: float, start_stop: Stop,
                 capacity: int, release_time: float,
                 end_time: Optional[float] = None,
                 mode: Optional[str] = None, reusable: bool = False) -> None:
        self.__id = veh_id
        self.__start_time = start_time
        self.__end_time = end_time if end_time is not None else self.MAX_TIME
        self.__start_stop = start_stop
        self.__capacity = capacity
        self.__release_time = release_time
        self.__mode = mode
        self.__reusable = reusable
        self.__position = None
        self.__polylines = None
        self.__state_machine = state_machine.VehicleStateMachine(self)

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
    def start_time(self) -> float:
        return self.__start_time

    @property
    def end_time(self) -> float:
        return self.__end_time

    @property
    def start_stop(self) -> Stop:
        return self.__start_stop

    @property
    def capacity(self) -> int:
        return self.__capacity

    @property
    def release_time(self) -> float:
        return self.__release_time

    @property
    def mode(self) -> Optional[str]:
        return self.__mode

    @property
    def reusable(self) -> bool:
        return self.__reusable

    @property
    def position(self) -> Location:
        return self.__position

    @position.setter
    def position(self, position: Location) -> None:
        self.__position = position

    @property
    def polylines(self) -> Optional[dict[str, tuple[str, list[float]]]]:
        return self.__polylines

    @polylines.setter
    def polylines(
            self,
            polylines: Optional[dict[str, tuple[str, list[float]]]]) -> None:
        self.__polylines = polylines

    @property
    def status(self) -> VehicleStatus:
        return self.__state_machine.current_state.status

    @property
    def state_machine(self) -> 'state_machine.VehicleStateMachine':
        return self.__state_machine

    def __deepcopy__(self, memo: dict) -> 'Vehicle':
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == "_Vehicle__polylines":
                setattr(result, k, [])
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result


class Route:
    """The ``Route`` class serves as a structure for storing basic
    information about the routes.
       Properties
       ----------
       vehicle: Vehicle
            vehicle associated with the route.
        current_stop: Stop
           current stop of the associated vehicle.
        next_stops: list of Stop objects
           the next stops to be visited by the vehicle.
        previous_stops: list of Stop objects
           the stops previously visited by the vehicle.
        onboard_legs: list of Leg objects
            legs associated with the passengers currently on board.
        assigned_legs: list of Leg objects
            legs associated with the passengers assigned to the associated
            vehicle.
        alighted_legs: list of Leg objects
            legs associated with the passengers that alighted from the
            corresponding vehicle.
    """

    def __init__(self, vehicle: Vehicle,
                 next_stops: Optional[list[Stop]] = None) -> None:

        self.__vehicle = vehicle

        self.__current_stop = vehicle.start_stop
        self.__next_stops = next_stops if next_stops is not None else []
        self.__previous_stops = []

        self.__onboard_legs = []
        self.__assigned_legs = []
        self.__alighted_legs = []

    def __str__(self) -> str:
        class_string = str(self.__class__) + ": {"
        for attribute, value in self.__dict__.items():
            if "__vehicle" in attribute:
                class_string += str(attribute) + ": " + str(value.id) + ", "
            elif "__next_stops" in attribute:
                class_string += str(attribute) + ": ["
                for stop in value:
                    class_string += str(stop) + ", "
                class_string += "], "
            elif "__previous_stops" in attribute:
                class_string += str(attribute) + ": ["
                for stop in value:
                    class_string += str(stop) + ", "
                class_string += "], "
            else:
                class_string += str(attribute) + ": " + str(value) + ", "
        class_string += "}"
        return class_string

    @property
    def vehicle(self) -> Vehicle:
        return self.__vehicle

    @property
    def current_stop(self) -> Stop:
        return self.__current_stop

    @current_stop.setter
    def current_stop(self, current_stop: Stop) -> None:
        self.__current_stop = current_stop

    @property
    def next_stops(self) -> list[Stop]:
        return self.__next_stops

    @next_stops.setter
    def next_stops(self, next_stops: list[Stop]) -> None:
        self.__next_stops = next_stops

    @property
    def previous_stops(self) -> list[Stop]:
        return self.__previous_stops

    @property
    def onboard_legs(self) -> list['request.Leg']:
        return self.__onboard_legs

    @property
    def assigned_legs(self) -> list['request.Leg']:
        return self.__assigned_legs

    @property
    def alighted_legs(self) -> list['request.Leg']:
        return self.__alighted_legs

    def initiate_boarding(self, trip: 'request.Trip') -> None:
        """Initiate boarding of the passengers who are ready to be picked up"""
        self.current_stop.initiate_boarding(trip)

    def board(self, trip: 'request.Trip') -> None:
        """Boards passengers who are ready to be picked up"""
        if trip is not None:
            self.__assigned_legs.remove(trip.current_leg)
            self.__onboard_legs.append(trip.current_leg)
            self.current_stop.board(trip)

    def depart(self) -> None:
        """Departs the vehicle"""
        if self.__current_stop is not None:
            self.__previous_stops.append(self.current_stop)
        self.__current_stop = None

    def arrive(self) -> None:
        """Arrives the vehicle"""
        self.__current_stop = self.__next_stops.pop(0)

    def initiate_alighting(self, trip: 'request.Trip') -> None:
        """Initiate alighting of the passengers who are ready to alight"""
        self.current_stop.initiate_alighting(trip)

    def alight(self, leg: 'request.Leg') -> None:
        """Alights passengers who reached their destination from the vehicle"""
        self.__onboard_legs.remove(leg)
        self.__alighted_legs.append(leg)
        self.__current_stop.alight(leg.trip)

    def assign_leg(self, leg: 'request.Leg') -> None:
        """Assigns a new leg to the route"""
        self.__assigned_legs.append(leg)

    def requests_to_pickup(self) -> list['request.Trip']:
        """Returns the list of requests ready to be picked up by the vehicle"""
        trips_to_pickup = []
        for trip in self.__current_stop.passengers_to_board:
            if trip.status == PassengerStatus.READY:
                trips_to_pickup.append(trip)

        return trips_to_pickup

    def __deepcopy__(self, memo: dict) -> 'Route':
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == "_Route__previous_stops":
                setattr(result, k, [])
            elif k == "_Route__alighted_legs":
                setattr(result, k, [])
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result


class RouteUpdate:
    def __init__(
            self, vehicle_id: str | int,
            current_stop_modified_passengers_to_board:
            Optional[list['request.Trip']] = None,
            next_stops: Optional[list[Stop]] = None,
            current_stop_departure_time: Optional[int] = None,
            modified_assigned_legs: Optional[
                list['request.Leg']] = None) -> None:
        self.vehicle_id = vehicle_id
        self.current_stop_modified_passengers_to_board = \
            current_stop_modified_passengers_to_board
        self.next_stops = next_stops
        self.current_stop_departure_time = current_stop_departure_time
        self.modified_assigned_legs = modified_assigned_legs
