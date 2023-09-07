import copy
import logging

from multimodalsim.optimization.state import State
from multimodalsim.state_machine.status import VehicleStatus, PassengersStatus

logger = logging.getLogger(__name__)


class Environment(object):
    """The ``Environment`` class mostly serves as a structure for storing basic
    information about the environment
        Attributes:
        ----------
        current_time: int
            The date and time of the current event.
        trips: list of Trip objects
            All the trips that were added to the environment.
        assigned_trips: list of Trip objects
            The trips that are assigned to a route.
        non_assigned_trips: list of Trip objects
            The trips that are not assigned to a route yet.
        vehicles: list of Vehicle objects
            All the vehicles that were added to the environment.
        routes_by_vehicle_id: dictionary associating an id (string) with a
        Route object.
            The route of each vehicle in the environment (key: Vehicle.id,
            value: associated Route)
        network: graph
            Graph corresponding to the network.
        optimization: Optimization
            The optimization algorithm used by the simulation.
        coordinates: Coordinates
            The coordinates of the vehicles.
        travel_times: TravelTimes
            The actual travel times of the vehicles.
        """

    def __init__(self, optimization, network=None, coordinates=None,
                 travel_times=None):
        self.__current_time = 0
        self.__trips = []
        self.__assigned_trips = []
        self.__non_assigned_trips = []
        self.__vehicles = []
        self.__routes_by_vehicle_id = {}

        self.__network = network
        self.__optimization = optimization
        self.__coordinates = coordinates
        self.__travel_times = travel_times

    @property
    def current_time(self):
        return self.__current_time

    @current_time.setter
    def current_time(self, current_time):
        if current_time < self.__current_time:
            logger.warning(
                "{} < {}".format(current_time, self.__current_time))
            raise ValueError("The attribute current_time of Environment "
                             "cannot decrease.")
        self.__current_time = current_time

    @property
    def trips(self):
        return self.__trips

    def get_trip_by_id(self, trip_id):
        found_trip = None
        for trip in self.trips:
            if trip.id == trip_id:
                found_trip = trip
                break
        return found_trip

    def add_trip(self, trip):
        """ Adds a new trip to the trips list"""
        self.__trips.append(trip)

    def remove_trip(self, trip_id):
        """ Removes a trip from the requests list based on its id"""
        self.__trips = [trip for trip in self.__trips if trip.id != trip_id]

    def get_leg_by_id(self, leg_id):
        # Look for the leg in the legs of all trips.
        found_leg = None
        for trip in self.__trips:
            # Current leg
            if trip.current_leg is not None and trip.current_leg.id == leg_id:
                found_leg = trip.current_leg
            # Previous legs
            for leg in trip.previous_legs:
                if leg.id == leg_id:
                    found_leg = leg
            # Next legs
            if trip.next_legs is not None:
                for leg in trip.next_legs:
                    if leg.id == leg_id:
                        found_leg = leg

        return found_leg

    @property
    def assigned_trips(self):
        return self.__assigned_trips

    def add_assigned_trip(self, trip):
        """ Adds a new trip to the list of assigned trips"""
        self.__assigned_trips.append(trip)

    def remove_assigned_trip(self, trip_id):
        """ Removes a trip from the list of assigned trips based on its id"""
        self.__assigned_trips = [trip for trip in self.__assigned_trips
                                 if trip.id != trip_id]

    @property
    def non_assigned_trips(self):
        return self.__non_assigned_trips

    def add_non_assigned_trip(self, trip):
        """ Adds a new trip to the list of non-assigned trips"""
        self.__non_assigned_trips.append(trip)

    def remove_non_assigned_trip(self, trip_id):
        """ Removes a trip from the list of non-assigned trips based on its
        id """
        self.__non_assigned_trips = [trip for trip in self.__non_assigned_trips
                                     if trip.id != trip_id]

    @property
    def vehicles(self):
        return self.__vehicles

    def get_vehicle_by_id(self, vehicle_id):
        found_vehicle = None
        for vehicle in self.vehicles:
            if vehicle.id == vehicle_id:
                found_vehicle = vehicle
        return found_vehicle

    def add_vehicle(self, vehicle):
        """ Adds a new vehicle to the vehicles list"""
        self.__vehicles.append(vehicle)

    def remove_vehicle(self, vehicle_id):
        """ Removes a vehicle from the vehicles list based on its id"""
        self.__vehicles = [item for item in self.__vehicles
                           if item.attribute != vehicle_id]

    @property
    def route_by_vehicle_id(self):
        return self.__routes_by_vehicle_id

    def get_route_by_vehicle_id(self, vehicle_id):
        route = None
        if vehicle_id in self.__routes_by_vehicle_id:
            route = self.__routes_by_vehicle_id[vehicle_id]

        return route

    def add_route(self, route, vehicle_id):
        self.__routes_by_vehicle_id[vehicle_id] = route

    def get_environment_statistics(self):

        env_stats = EnvironmentStatistics(self)

        return env_stats

    def get_new_state(self):
        state_copy = copy.copy(self)
        state_copy.__network = None
        state_copy.__optimization = None
        state_copy.__coordinates = None
        state_copy.__travel_times = None

        state_copy.__vehicles = \
            self.__get_non_complete_vehicles(state_copy.__vehicles)

        state_copy.__trips = self.__get_non_complete_trips(state_copy.__trips)
        state_copy.__assigned_trips = \
            self.__get_non_complete_trips(state_copy.__assigned_trips)

        state_deepcopy = State(copy.deepcopy(state_copy))

        return state_deepcopy

    def __get_non_complete_vehicles(self, vehicles):
        non_complete_vehicles = []
        for vehicle in vehicles:
            if vehicle.status != VehicleStatus.COMPLETE:
                veh_copy = copy.copy(vehicle)
                veh_copy.polylines = None
                non_complete_vehicles.append(veh_copy)
        return non_complete_vehicles

    def __get_non_complete_trips(self, trips):
        non_complete_trips = []
        for trip in trips:
            if trip.status != PassengersStatus.COMPLETE:
                non_complete_trips.append(trip)
        return non_complete_trips

    @property
    def network(self):
        return self.__network

    @property
    def optimization(self):
        return self.__optimization

    @property
    def coordinates(self):
        return self.__coordinates

    @property
    def travel_times(self):
        return self.__travel_times


class EnvironmentStatistics:

    def __init__(self, env):
        self.__nb_vehicles = len(env.vehicles)
        self.__nb_trips = len(env.trips)

    @property
    def nb_vehicles(self):
        return self.__nb_vehicles

    @property
    def nb_trips(self):
        return self.__nb_trips

