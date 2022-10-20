import copy
import logging

logger = logging.getLogger(__name__)


class State(object):

    def __init__(self, env):
        env_deep_copy = copy.deepcopy(env)

        self.current_time = env_deep_copy.current_time
        self.trips = env_deep_copy.trips
        self.assigned_trips = env_deep_copy.assigned_trips
        self.non_assigned_trips = env_deep_copy.non_assigned_trips
        self.vehicles = env_deep_copy.vehicles
        self.assigned_vehicles = env_deep_copy.assigned_vehicles
        self.non_assigned_vehicles = env_deep_copy.non_assigned_vehicles

    def fix_routes_for_time_interval(self, time_interval):

        self.current_time = self.current_time + time_interval

        self.__move_stops_backward()

    def unfix_routes_for_time_interval(self, time_interval):

        self.current_time = self.current_time - time_interval

        self.__move_stops_forward()

    def __move_stops_backward(self):

        for vehicle in self.vehicles:
            self.__move_current_stop_backward(vehicle)
            self.__move_next_stops_backward(vehicle)

    def __move_current_stop_backward(self, vehicle):

        if vehicle.route.current_stop is not None and \
                vehicle.route.current_stop.departure_time <= self.current_time:
            vehicle.route.previous_stops.append(vehicle.route.current_stop)
            vehicle.route.current_stop = None

    def __move_next_stops_backward(self, vehicle):

        stops_to_be_removed = []
        for stop in vehicle.route.next_stops:
            if stop.departure_time <= self.current_time:
                vehicle.route.previous_stops.append(stop)
                stops_to_be_removed.append(stop)
            elif stop.arrival_time <= self.current_time:
                vehicle.route.current_stop = stop
                stops_to_be_removed.append(stop)

        for stop in stops_to_be_removed:
            vehicle.route.next_stops.remove(stop)

    def __move_stops_forward(self):

        for vehicle in self.vehicles:
            self.__move_current_stop_forward(vehicle)
            self.__move_previous_stops_forward(vehicle)

    def __move_current_stop_forward(self, vehicle):

        if vehicle.route.current_stop is not None \
                and vehicle.route.current_stop != vehicle.start_stop and \
                vehicle.route.current_stop.arrival_time > self.current_time:
            # The first stop of a route (i.e., vehicle.start_stop) can have an
            # arrival time greater than current time.
            vehicle.route.next_stops.insert(0, vehicle.route.current_stop)
            vehicle.route.current_stop = None

    def __move_previous_stops_forward(self, vehicle):

        stops_to_be_removed = []
        for stop in vehicle.route.previous_stops:
            if stop.departure_time > self.current_time \
                    and (stop == vehicle.start_stop
                         or stop.arrival_time <= self.current_time):
                # stop is either the start stop of the vehicle (in which cast,
                # arrival time does not matter) or the
                # current stop.
                vehicle.route.current_stop = stop
                stops_to_be_removed.append(stop)
            elif stop.departure_time > self.current_time:
                # stop is a next stop.
                vehicle.route.next_stops.insert(0, stop)
                stops_to_be_removed.append(stop)

        for stop in stops_to_be_removed:
            vehicle.route.previous_stops.remove(stop)
