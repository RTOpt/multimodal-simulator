import logging

logger = logging.getLogger(__name__)


class State:

    def __init__(self, env_deep_copy):
        """The ``State`` class is a partial deep copy of the environment where
        only the data necessary for optimization is copied.
                Attributes:
                ----------
                current_time: int
                    The date and time of the current event.
                trips: list of Trip objects
                    A deep copy of all the trips that were added to the
                    environment.
                assigned_trips: list of Trip objects
                    A deep copy of the trips for which the next leg is assigned
                    to a route.
                non_assigned_trips: list of Trip objects
                    A deep copy of the trips for which the next leg has not
                    been assigned to a route yet.
                vehicles: list of Vehicle objects
                    A deep copy of all the vehicles that were added to the
                    environment.
                routes_by_vehicle_id: dictionary associating an id (string)
                with a Route object.
                    A deep copy of the route of each vehicle in the
                    environment (key: Vehicle.id, value: associated Route)
                next_legs: list of Leg objects
                    A deep copy of the first next leg of each trip of the
                    environment.
                next_legs: list of Leg objects
                    A deep copy of the first next leg of each unassigned trip
                    of the environment.
                """

        self.current_time = env_deep_copy.current_time
        self.trips = env_deep_copy.trips
        self.assigned_trips = env_deep_copy.assigned_trips
        self.non_assigned_trips = env_deep_copy.non_assigned_trips
        self.vehicles = env_deep_copy.vehicles
        self.route_by_vehicle_id = \
            {veh.id: env_deep_copy.route_by_vehicle_id[veh.id]
             for veh in self.vehicles}
        self.next_legs = self.__get_next_legs(self.trips)
        self.non_assigned_next_legs = self.__get_next_legs(
            self.non_assigned_trips)
        self.main_line = env_deep_copy.main_line
        self.next_main_line = env_deep_copy.next_main_line

    def get_trip_by_id(self, trip_id):
        found_trip = None
        for trip in self.trips:
            if trip.id == trip_id:
                found_trip = trip
                break
        return found_trip

    def get_vehicle_by_id(self, vehicle_id):
        found_vehicle = None
        for vehicle in self.vehicles:
            logger.warning("vehicle.id={}".format(vehicle.id))
            if vehicle.id == vehicle_id:
                found_vehicle = vehicle
                break
        return found_vehicle

    def get_leg_by_id(self, leg_id):
        # Look for the leg in the legs of all trips.
        found_leg = None
        for trip in self.trips:
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

    def freeze_routes_for_time_interval(self, time_interval):

        self.current_time = self.current_time + time_interval

        self.__move_stops_backward()

    def unfreeze_routes_for_time_interval(self, time_interval):

        self.current_time = self.current_time - time_interval

        self.__move_stops_forward()

    def __get_next_legs(self, trips):
        next_legs = []
        for trip in trips:
            if len(trip.next_legs) > 0:
                next_legs.append(trip.next_legs[0])

        return next_legs

    def __move_stops_backward(self):

        for vehicle in self.vehicles:
            route = self.route_by_vehicle_id[vehicle.id]
            self.__move_current_stop_backward(route)
            self.__move_next_stops_backward(route)

    def __move_current_stop_backward(self, route):

        if route.current_stop is not None and \
                route.current_stop.departure_time <= self.current_time:
            route.previous_stops.append(route.current_stop)
            route.current_stop = None

    def __move_next_stops_backward(self, route):

        stops_to_be_removed = []
        for stop in route.next_stops:
            if stop.departure_time <= self.current_time:
                route.previous_stops.append(stop)
                stops_to_be_removed.append(stop)
            elif stop.arrival_time <= self.current_time:
                route.current_stop = stop
                stops_to_be_removed.append(stop)

        for stop in stops_to_be_removed:
            route.next_stops.remove(stop)

    def __move_stops_forward(self):

        for vehicle in self.vehicles:
            route = self.route_by_vehicle_id[vehicle.id]
            self.__move_current_stop_forward(route, vehicle.start_stop)
            self.__move_previous_stops_forward(route, vehicle.start_stop)

    def __move_current_stop_forward(self, route, start_stop):

        if route.current_stop is not None \
                and route.current_stop != start_stop and \
                route.current_stop.arrival_time > self.current_time:
            # The first stop of a route (i.e., vehicle.start_stop) can have an
            # arrival time greater than current time.
            route.next_stops.insert(0, route.current_stop)
            route.current_stop = None

    def __move_previous_stops_forward(self, route, start_stop):

        stops_to_be_removed = []
        for stop in route.previous_stops:
            if stop.departure_time > self.current_time \
                    and (stop == start_stop
                         or stop.arrival_time <= self.current_time):
                # stop is either the start stop of the vehicle (in which case,
                # arrival time does not matter) or the
                # current stop.
                route.current_stop = stop
                stops_to_be_removed.append(stop)
            elif stop.departure_time > self.current_time:
                # stop is a next stop.
                route.next_stops.insert(0, stop)
                stops_to_be_removed.append(stop)

        for stop in stops_to_be_removed:
            route.previous_stops.remove(stop)
