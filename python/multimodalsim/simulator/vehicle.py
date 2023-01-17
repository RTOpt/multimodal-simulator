import logging
import copy

import multimodalsim.state_machine.state_machine as state_machine

logger = logging.getLogger(__name__)


class Vehicle(object):
    """The ``Vehicle`` class mostly serves as a structure for storing basic
        information about the vehicles.
        Properties
        ----------
        id: int
            unique id
        start_time: int
            time at which the vehicle is ready to start
        start_stop: Stop
            Stop at which the vehicle starts.
        capacity: int
            Maximum number of passengers that can fit in the vehicle
        release_time: int
            time at which the vehicle is added to the environment.
    """

    def __init__(self, veh_id, start_time, start_stop, capacity, release_time,
                 time_positions=None):
        self.__route = None
        self.__id = veh_id
        self.__start_time = start_time
        self.__start_stop = start_stop
        self.__capacity = capacity
        self.__release_time = release_time
        self.__time_positions = time_positions
        self.__current_position = None

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
    def start_time(self):
        return self.__start_time

    @property
    def start_stop(self):
        return self.__start_stop

    @property
    def capacity(self):
        return self.__capacity

    @property
    def release_time(self):
        return self.__release_time

    @property
    def route(self):
        return self.__route

    @route.setter
    def route(self, route):
        if self.__route is not None:
            raise ValueError("Vehicle {} has already a route.".format(self.id))
        self.__route = route

    @property
    def position(self):
        return self.__current_position

    def update_position(self, current_time):
        current_position = None
        if self.__time_positions is not None:
            for time_position in self.__time_positions:
                if time_position.time > current_time:
                    break
                current_position = time_position
        elif self.route is not None and self.route.current_stop is not None:
            # If no time_positions are available, use location of current_stop.
            current_position = self.route.current_stop.location
        elif self.route is not None and len(self.route.previous_stops) > 0:
            # If current_stop is None, use location of the most recent
            # previous_stops.
            current_position = self.route.previous_stops[-1].location

        self.__current_position = current_position

        return current_position


class Route(object):
    """The ``Route`` class serves as a structure for storing basic
    information about the routes.
       Properties
       ----------
       vehicle: Vehicle
            vehicle associated with the route.
       status: int
            represents the different status of route (VehicleStatus(Enum)).
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
        load: int
            Number of passengers on board
    """

    def __init__(self, vehicle, next_stops=None):

        self.__vehicle = vehicle

        self.__state_machine = state_machine.VehicleStateMachine(self)

        self.__current_stop = vehicle.start_stop
        self.__next_stops = next_stops if next_stops is not None else []
        self.__previous_stops = []

        self.__onboard_legs = []
        self.__assigned_legs = []
        self.__alighted_legs = []

        self.__load = 0

    def __str__(self):
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
    def vehicle(self):
        return self.__vehicle

    @property
    def status(self):
        return self.__state_machine.current_state.status

    @property
    def state_machine(self):
        return self.__state_machine

    @property
    def current_stop(self):
        return self.__current_stop

    @current_stop.setter
    def current_stop(self, current_stop):
        self.__current_stop = current_stop

    @property
    def next_stops(self):
        return self.__next_stops

    @next_stops.setter
    def next_stops(self, next_stops):
        self.__next_stops = next_stops

    @property
    def previous_stops(self):
        return self.__previous_stops

    @property
    def onboard_legs(self):
        return self.__onboard_legs

    @property
    def assigned_legs(self):
        return self.__assigned_legs

    @property
    def alighted_legs(self):
        return self.__alighted_legs

    @property
    def load(self):
        return self.__load

    def initiate_boarding(self, trip):
        """Initiate boarding of the passengers who are ready to be picked up"""
        self.current_stop.initiate_boarding(trip)

    def board(self, trip):
        """Boards passengers who are ready to be picked up"""
        if trip is not None:
            self.__assigned_legs.remove(trip.current_leg)
            self.__onboard_legs.append(trip.current_leg)
            self.current_stop.board(trip)
            # Patrick: Should we increase self.load?
            self.__load += 1

    def depart(self):
        """Departs the vehicle"""
        if self.__current_stop is not None:
            self.__previous_stops.append(self.current_stop)
        self.__current_stop = None

    def arrive(self):
        """Arrives the vehicle"""
        self.__current_stop = self.__next_stops.pop(0)

    def alight(self, trip):
        """Alights passengers who reached their destination from the vehicle"""
        self.__onboard_legs.remove(trip.current_leg)
        self.__alighted_legs.append(trip.current_leg)
        self.__current_stop.alight(trip)
        # Patrick: Should we decrease self.load?
        self.__load -= 1

    def nb_free_places(self):
        """Returns the number of places remaining in the vehicle"""
        return self.__vehicle.capacity - self.__load

    def assign_leg(self, leg):
        """Assigns a new leg to the route"""
        self.__assigned_legs.append(leg)

    def requests_to_pickup(self):
        """Updates the list of requests to pick up by the vehicle"""
        return self.__current_stop.passengers_to_board

    def __deepcopy__(self, memo):
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


class Stop(object):
    """A stop is located somewhere along the network.  New requests
    arrive at the stop.
    ----------
    arrival_time: int
        Date and time at which the vehicle arrives the stop
    departure_time: int
        Date and time at which the vehicle leaves the stop
    passengers_to_board: list of Trip objects
        list of passengers who need to board
    boarding_passengers: list of Trip objects
        list of passengers who are boarding
    boarded_passengers: list of Trip objects
        list of passengers who are already boarded
    passengers_to_alight: list of Trip objects
        list of passengers to alight
        OLD: list of passengers who are alighted
    alighted_passengers: list of Trip objects
        list of passengers who are alighted
    location: Location
        Object of type Location referring to the location of the stop
        (e.g., GPS coordinates)
    """

    def __init__(self, arrival_time, departure_time, location,
                 cumulative_distance=None):
        super().__init__()

        self.__arrival_time = arrival_time
        self.__departure_time = departure_time
        self.__passengers_to_board = []
        self.__boarding_passengers = []
        self.__boarded_passengers = []
        self.__passengers_to_alight = []
        self.__alighted_passengers = []
        self.__location = location
        self.__cumulative_distance = cumulative_distance

    def __str__(self):
        class_string = str(self.__class__) + ": {"
        for attribute, value in self.__dict__.items():
            if "__passengers_to_board" in attribute:
                class_string += str(attribute) + ": " \
                                + str(list(str(x.id) for x in value)) + ", "
            elif "__boarding_passengers" in attribute:
                class_string += str(attribute) + ": " \
                                + str(list(str(x.id) for x in value)) + ", "
            elif "__boarded_passengers" in attribute:
                class_string += str(attribute) + ": " \
                                + str(list(str(x.id) for x in value)) + ", "
            elif "__passengers_to_alight" in attribute:
                class_string += str(attribute) + ": " \
                                + str(list(str(x.id) for x in value)) + ", "
            elif "alighted_passengers" in attribute:
                class_string += str(attribute) + ": " \
                                + str(list(str(x.id) for x in value)) + ", "
            else:
                class_string += str(attribute) + ": " + str(value) + ", "

        class_string += "}"

        return class_string

    @property
    def arrival_time(self):
        return self.__arrival_time

    @property
    def departure_time(self):
        return self.__departure_time

    @departure_time.setter
    def departure_time(self, departure_time):
        self.__departure_time = departure_time

    @property
    def passengers_to_board(self):
        return self.__passengers_to_board

    @passengers_to_board.setter
    def passengers_to_board(self, passengers_to_board):
        self.__passengers_to_board = passengers_to_board

    @property
    def boarding_passengers(self):
        return self.__boarding_passengers

    @boarding_passengers.setter
    def boarding_passengers(self, boarding_passengers):
        self.__boarding_passengers = boarding_passengers

    @property
    def boarded_passengers(self):
        return self.__boarded_passengers

    @boarded_passengers.setter
    def boarded_passengers(self, boarded_passengers):
        self.__boarded_passengers = boarded_passengers

    @property
    def passengers_to_alight(self):
        return self.__passengers_to_alight

    @passengers_to_alight.setter
    def passengers_to_alight(self, passengers_to_alight):
        self.__passengers_to_alight = passengers_to_alight

    @property
    def alighted_passengers(self):
        return self.__alighted_passengers

    @property
    def location(self):
        return self.__location

    @property
    def cumulative_distance(self):
        return self.__cumulative_distance

    def initiate_boarding(self, trip):
        """Passengers who are ready to be picked up in the stop get in the
        vehicle """
        self.passengers_to_board.remove(trip)
        self.boarding_passengers.append(trip)

    def board(self, trip):
        """Passenger who is boarding becomes boarded"""
        self.boarding_passengers.remove(trip)
        self.boarded_passengers.append(trip)

    def alight(self, trip):
        """Passengers who reached their stop leave the vehicle"""
        self.passengers_to_alight.remove(trip)
        self.alighted_passengers.append(trip)


class Location(object):
    """The ``Location`` class is a base class that mostly serves as a
    structure for storing basic information about the location of a vehicle
    or a passenger (i.e., Request). """

    def __init__(self):
        pass

    def __eq__(self, other):
        pass


class GPSLocation(Location):
    def __init__(self, gps_coordinates):
        # gps_coordinates is an object of type Node
        super().__init__()
        self.gps_coordinates = gps_coordinates

    def __str__(self):
        return "({},{})".format(self.gps_coordinates.get_coordinates()[0],
                                self.gps_coordinates.get_coordinates()[1])

    def __eq__(self, other):
        if isinstance(other, GPSLocation):
            return self.gps_coordinates == other.gps_coordinates
        return False


class LabelLocation(Location):
    def __init__(self, label, lon=None, lat=None):
        super().__init__()
        self.label = label
        self.lon = lon
        self.lat = lat

    def __str__(self):
        return self.label

    def __eq__(self, other):
        if isinstance(other, LabelLocation):
            return self.label == other.label
        return False


class TimeCoordinatesLocation(Location):
    def __init__(self, time, lon, lat):
        super().__init__()
        self.time = time
        self.lon = lon
        self.lat = lat

    def __str__(self):
        return "{}: ({},{})".format(self.time, self.lon, self.lat)

    def __eq__(self, other):
        if isinstance(other, TimeCoordinatesLocation):
            return self.time == other.time and self.lon == other.lon \
                   and self.lat == other.lat
        return False


class RouteUpdate(object):
    def __init__(self, vehicle_id,
                 current_stop_modified_passengers_to_board=None,
                 next_stops=None, current_stop_departure_time=None,
                 modified_assigned_legs=None):
        self.vehicle_id = vehicle_id
        self.current_stop_modified_passengers_to_board = \
            current_stop_modified_passengers_to_board
        self.next_stops = next_stops
        self.current_stop_departure_time = current_stop_departure_time
        self.modified_assigned_legs = modified_assigned_legs
