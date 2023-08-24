import logging

logger = logging.getLogger(__name__)


class State:

    def __init__(self, env_deep_copy):
        self.current_time = env_deep_copy.current_time
        self.trips = env_deep_copy.trips
        self.assigned_trips = env_deep_copy.assigned_trips
        self.non_assigned_trips = env_deep_copy.non_assigned_trips
        self.vehicles = env_deep_copy.vehicles
        self.route_by_vehicle_id = env_deep_copy.route_by_vehicle_id

    def get_trip_by_id(self, id):
        found_trip = None
        for trip in self.trips:
            if trip.id == id:
                found_trip = trip
        return found_trip

    def get_vehicle_by_id(self, veh_id):
        for veh in self.vehicles:
            if veh.id == veh_id:
                return veh

    def freeze_routes_for_time_interval(self, time_interval):

        self.current_time = self.current_time + time_interval

        self.__move_stops_backward()

    def unfreeze_routes_for_time_interval(self, time_interval):

        self.current_time = self.current_time - time_interval

        self.__move_stops_forward()

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
