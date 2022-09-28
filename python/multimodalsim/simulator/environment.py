import copy


class Environment(object):
    """The ``Environment`` class mostly serves as a structure for storing basic information about the environment
        Attributes:
        ----------
        current_time: int
            The date and time of the current event.
        trips: list of Trip objects
            All the trips that were added to the environment.
        assigned_trips: list of Trip objects
            the trips that are assigned to a route.
        non_assigned_trips: list of Trip objects
            the trips that are not assigned to a route yet.
        vehicles: list of Vehicle objects
            All the vehicles that were added to the environment.
        assigned_vehicles: list of Vehicle objects
            the vehicles that are assigned at least one trip.
        non_assigned_vehicles: list of Vehicle objects
            the vehicles that are not assigned any trip yet.
        network: graph
            graph corresponding to the network.
        optimization: Optimization
            the optimization algorithm used by the simulation.
        """

    def __init__(self, optimization, network=None):
        self.current_time = 0
        self.__trips = []
        self.__assigned_trips = []
        self.__non_assigned_trips = []
        self.__vehicles = []
        self.__assigned_vehicles = []
        self.__non_assigned_vehicles = []
        self.__network = network
        self.__optimization = optimization

    @property
    def trips(self):
        return self.__trips

    def get_trip_by_id(self, id):
        found_trip = None
        for trip in self.trips:
            if trip.id == id:
                found_trip = trip
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
        self.__assigned_trips = [trip for trip in self.__assigned_trips if trip.id != trip_id]

    @property
    def non_assigned_trips(self):
        return self.__non_assigned_trips

    def add_non_assigned_trip(self, trip):
        """ Adds a new trip to the list of non-assigned trips"""
        self.__non_assigned_trips.append(trip)

    def remove_non_assigned_trip(self, trip_id):
        """ Removes a trip from the list of non-assigned trips based on its id"""
        self.__non_assigned_trips = [trip for trip in self.__non_assigned_trips if trip.id != trip_id]

    @property
    def vehicles(self):
        return self.__vehicles

    def get_vehicle_by_id(self, veh_id):
        for veh in self.__vehicles:
            if veh.id == veh_id:
                return veh

    def add_vehicle(self, vehicle):
        """ Adds a new vehicle to the vehicles list"""
        self.__vehicles.append(vehicle)

    def remove_vehicle(self, vehicle_id):
        """ Removes a vehicle from the vehicles list based on its id"""
        self.__vehicles = [item for item in self.__vehicles if item.attribute != vehicle_id]

    @property
    def assigned_vehicles(self):
        return self.__assigned_vehicles

    def add_assigned_vehicle(self, vehicle):
        """ Adds a new vehicle to the list of assigned vehicles"""
        self.__assigned_vehicles.append(vehicle)

    def remove_assigned_vehicle(self, vehicle_id):
        """ Removes a vehicle from the list of assigned vehicles based on its id"""
        self.__assigned_vehicles = [veh for veh in self.__assigned_vehicles if veh.id != vehicle_id]

    @property
    def non_assigned_vehicles(self):
        return self.__non_assigned_vehicles

    def add_non_assigned_vehicle(self, vehicle):
        """ Adds a new vehicle to the list of non-assigned vehicles"""
        self.__non_assigned_vehicles.append(vehicle)

    def remove_non_assigned_vehicle(self, vehicle_id):
        """ Removes a vehicle from the list of non-assigned vehicles based on its id"""
        self.__non_assigned_vehicles = [veh for veh in self.__non_assigned_vehicles if veh.id != vehicle_id]

    def get_state_copy(self):
        state_copy = copy.copy(self)
        state_copy.__network = None
        state_copy.__optimization = None

        return state_copy

    @property
    def network(self):
        return self.__network

    @property
    def optimization(self):
        return self.__optimization
