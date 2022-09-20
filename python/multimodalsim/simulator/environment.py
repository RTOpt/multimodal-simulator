from multimodalsim.simulator.request import Trip
from multimodalsim.simulator.status import PassengersStatus, VehicleStatus
from multimodalsim.simulator.vehicle import Vehicle


class Environment(object):

    def __init__(self, optimization, network=None):
        # Patrick: Added optimization, status
        self.non_assigned_trips = None
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
        for trip in self.trips:
            if trip.req_id == req_id:
                return trip

    def add_trip(self, trip):
        """ Adds a new trip to the trips list"""
        self.trips.append(trip)

    def remove_trip(self, trip_id):
        """ Removes a trip from the requests list based on its id"""
        self.trips = [item for item in self.trips if item.attribute != trip_id]

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

    def get_non_assigned_trips(self):
        # Patrick: OLD
        # for req in self.requests:
        #     if req.status == PassengersStatus.RELEASE:
        #         self.non_assigned_trips.append(req)

        self.update_non_assigned_trips()

        return self.non_assigned_trips

    def get_non_assigned_vehicles(self):
        # Patrick: OLD
        # for veh in self.vehicles:
        #     if veh.route.status == VehicleStatus.BOARDING:
        #         self.non_assigned_vehicles.append(veh)

        self.update_non_assigned_vehicles()

        return self.non_assigned_vehicles

    def update_non_assigned_trips(self):
        self.non_assigned_trips = []
        self.assigned_trips = []

        # À faire par les événements
        for trip in self.trips:
            # Shouldn't we consider a trip with PassengersStatus.ASSIGNMENT a non-assigned trip as well?
            if trip.status == PassengersStatus.RELEASE:
                self.non_assigned_trips.append(trip)
            else:
                self.assigned_trips.append(trip)
            # OLD
            # if req.status == PassengersStatus.RELEASE:
            #     self.non_assigned_trips.append(req)
        return self.non_assigned_trips

    def update_non_assigned_vehicles(self):
        # Patrick: Shouldn't we reinitialize the list non_assigned_vehicles every time?
        self.non_assigned_vehicles = []  # Was not there before
        self.assigned_vehicles = []  # Was not there before

        for veh in self.vehicles:
            # Patrick: Shouldn't the vehicle status be RELEASE (or READY)?
            # if veh.route.status == VehicleStatus.RELEASE or veh.route.status == VehicleStatus.COMPLETE:
            if veh.route.status == VehicleStatus.RELEASE or veh.route.status == VehicleStatus.BOARDING:
                self.non_assigned_vehicles.append(veh)
            else:
                self.assigned_vehicles.append(veh)
            # OLD
            # if veh.route.status == VehicleStatus.BOARDING:
            #     self.non_assigned_vehicles.append(veh)