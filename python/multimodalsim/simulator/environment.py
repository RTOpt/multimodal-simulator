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
        self.trips = []
        self.assigned_trips = []
        self.non_assigned_trips = []
        self.vehicles = []
        self.assigned_vehicles = []
        self.non_assigned_vehicles = []
        self.network = network
        self.optimization = optimization

    def get_trips(self):
        return self.trips

    def get_trip_by_id(self, req_id):
        found_trip = None
        for trip in self.trips:
            if trip.req_id == req_id:
                found_trip = trip
        return found_trip

    def get_leg_by_id(self, leg_id):
        # Look for the leg in the legs of all trips.
        found_leg = None
        for trip in self.trips:
            # Current leg
            if trip.current_leg is not None and trip.current_leg.req_id == leg_id:
                found_leg = trip.current_leg
            # Previous legs
            for leg in trip.previous_legs:
                if leg.req_id == leg_id:
                    found_leg = leg
            # Next legs
            if trip.next_legs is not None:
                for leg in trip.next_legs:
                    if leg.req_id == leg_id:
                        found_leg = leg

        return found_leg

    def add_trip(self, trip):
        """ Adds a new trip to the trips list"""
        self.trips.append(trip)

    def remove_trip(self, trip_id):
        """ Removes a trip from the requests list based on its id"""
        self.trips = [trip for trip in self.trips if trip.req_id != trip_id]

    def add_assigned_trip(self, trip):
        """ Adds a new trip to the list of assigned trips"""
        self.assigned_trips.append(trip)

    def remove_assigned_trip(self, trip_id):
        """ Removes a trip from the list of assigned trips based on its id"""
        self.assigned_trips = [trip for trip in self.assigned_trips if trip.req_id != trip_id]

    def add_non_assigned_trip(self, trip):
        """ Adds a new trip to the list of non-assigned trips"""
        self.non_assigned_trips.append(trip)

    def remove_non_assigned_trip(self, trip_id):
        """ Removes a trip from the list of non-assigned trips based on its id"""
        self.non_assigned_trips = [trip for trip in self.non_assigned_trips if trip.req_id != trip_id]

    def get_vehicles(self):
        return self.vehicles

    def get_vehicle_by_id(self, veh_id):
        for veh in self.vehicles:
            if veh.id == veh_id:
                return veh

    def add_vehicle(self, vehicle):
        """ Adds a new vehicle to the vehicles list"""
        self.vehicles.append(vehicle)

    def remove_vehicle(self, vehicle_id):
        """ Removes a vehicle from the vehicles list based on its id"""
        self.vehicles = [item for item in self.vehicles if item.attribute != vehicle_id]

    def add_assigned_vehicle(self, vehicle):
        """ Adds a new vehicle to the list of assigned vehicles"""
        self.assigned_vehicles.append(vehicle)

    def remove_assigned_vehicle(self, vehicle_id):
        """ Removes a vehicle from the list of assigned vehicles based on its id"""
        self.assigned_vehicles = [veh for veh in self.assigned_vehicles if veh.id != vehicle_id]

    def add_non_assigned_vehicle(self, vehicle):
        """ Adds a new vehicle to the list of non-assigned vehicles"""
        self.non_assigned_vehicles.append(vehicle)

    def remove_non_assigned_vehicle(self, vehicle_id):
        """ Removes a vehicle from the list of non-assigned vehicles based on its id"""
        self.non_assigned_vehicles = [veh for veh in self.non_assigned_vehicles if veh.id != vehicle_id]

    def get_non_assigned_trips(self):
        return self.non_assigned_trips

    def get_non_assigned_vehicles(self):
        return self.non_assigned_vehicles

    def get_state_copy(self):
        state_copy = copy.copy(self)
        state_copy.network = None
        state_copy.optimization = None

        return state_copy
