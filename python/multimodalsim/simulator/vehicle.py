import logging
import copy

from multimodalsim.simulator.status import VehicleStatus

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

    def __init__(self, veh_id, start_time, start_stop, capacity, release_time):
        self.route = None
        self.id = veh_id
        self.start_time = start_time
        self.start_stop = start_stop
        self.capacity = capacity
        self.release_time = release_time

    def __deepcopy__(self, memo_dict={}):

        cls = self.__class__
        new_cls = cls.__new__(cls)
        memo_dict[id(self)] = new_cls
        for attribute, value in self.__dict__.items():
            setattr(new_cls, attribute, copy.deepcopy(value, memo_dict))
        return new_cls

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
            legs associated with the passengers assigned to the associated vehicle.
        alighted_legs: list of Leg objects
            legs associated with the passengers that alighted from the corresponding vehicle.
        load: int
            Number of passengers on board
    """

    def __init__(self, vehicle, next_stops=[]):
        self.vehicle = vehicle
        self.status = VehicleStatus.RELEASE
        self.current_stop = vehicle.start_stop
        self.next_stops = next_stops
        self.previous_stops = []

        self.onboard_legs = []
        self.assigned_legs = []
        self.alighted_legs = []

        self.load = 0

    def __str__(self):
        class_string = str(self.__class__) + ": {"
        for attribute, value in self.__dict__.items():
            if attribute == "vehicle":
                class_string += str(attribute) + ": " + str(value.id) + ", "
            elif attribute == "next_stops":
                class_string += str(attribute) + ": ["
                for stop in value:
                    class_string += str(stop) + ", "
                class_string += "], "
            elif attribute == "previous_stops":
                class_string += str(attribute) + ": ["
                for stop in value:
                    class_string += str(stop) + ", "
                class_string += "], "
            else:
                class_string += str(attribute) + ": " + str(value) + ", "
        class_string += "}"
        return class_string

    def update_vehicle_status(self, status):
        self.status = status

    def board(self, trip):
        """Boards passengers who are ready to pick up"""
        if trip is not None:
            self.assigned_legs.remove(trip.current_leg)
            self.onboard_legs.append(trip.current_leg)
            self.current_stop.board(trip)
            # Patrick: Should we increase self.load?
            self.load += 1

    def depart(self):
        """Departs the vehicle"""
        if self.current_stop is not None:
            self.previous_stops.append(self.current_stop)
        self.current_stop = None

    def arrive(self):
        """Arrives the vehicle"""
        self.current_stop = self.next_stops.pop(0)

    def alight(self, trip):
        """Alights passengers who reached their destination from the vehicle"""
        self.onboard_legs.remove(trip.current_leg)
        self.alighted_legs.append(trip.current_leg)
        self.current_stop.alight(trip)
        # Patrick: Should we decrease self.load?
        self.load -= 1

    def nb_free_places(self):
        """Returns the number of places remaining in the vehicle"""
        return self.capacity - self.load

    def assign_leg(self, leg):
        """Assigns a new leg to the route"""
        self.assigned_legs.append(leg)

    def requests_to_pickup(self):
        """Updates the list of requests to pick up by the vehicle"""
        return self.current_stop.passengers_to_board


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
        Object of type Location referring to the location of the stop (e.g., GPS coordinates)
    """

    def __init__(self, stop_type, arrival_time, departure_time, location):
        self.arrival_time = arrival_time
        self.departure_time = departure_time
        self.passengers_to_board = []
        self.boarding_passengers = []
        self.boarded_passengers = []
        self.passengers_to_alight = []
        self.alighted_passengers = []
        self.location = location

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

        self.boarding_passengers.remove(request)
        self.boarded_passengers.append(request)

    def alight(self, request):
        """Passengers who reached their stop leave the vehicle"""

        self.passengers_to_alight.remove(request)
        self.alighted_passengers.append(request)


class Location(object):
    """The ``Location`` class is a base class that mostly serves as a structure for storing basic information about the
    location of a vehicle or a passenger (i.e., Request)."""
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
        return "({},{})".format(self.gps_coordinates.get_coordinates()[0], self.gps_coordinates.get_coordinates()[1])

    def __eq__(self, other):
        if isinstance(other, GPSLocation):
            return self.gps_coordinates == other.gps_coordinates
        return False


class LabelLocation(Location):
    def __init__(self, label):
        super().__init__()
        self.label = label

    def __str__(self):
        return self.label

    def __eq__(self, other):
        if isinstance(other, LabelLocation):
            return self.label == other.label
        return False


class RouteUpdate(object):
    def __init__(self, vehicle_id, current_stop_modified_passengers_to_board=None, next_stops=None,
                 current_stop_departure_time=None, modified_assigned_legs=None):
        self.vehicle_id = vehicle_id
        self.current_stop_modified_passengers_to_board = current_stop_modified_passengers_to_board
        self.next_stops = next_stops
        self.current_stop_departure_time = current_stop_departure_time
        self.modified_assigned_legs = modified_assigned_legs
