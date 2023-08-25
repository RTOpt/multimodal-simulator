import logging
import math

from itertools import cycle

from multimodalsim.optimization.dispatcher import ShuttleDispatcher

logger = logging.getLogger(__name__)


class ShuttleSimpleNetworkDispatcher(ShuttleDispatcher):

    def __init__(self, network, hub_location="0"):
        super().__init__()

        self.__network = network
        self.__hub_location = hub_location

    def prepare_input(self, state):
        # Before optimizing, we extract the trips and the vehicles that we want
        # to optimize.
        # By default, all trips (i.e., state.trips) and all vehicles (i.e.,
        # state.vehicles) existing at the time of optimization will be
        # optimized (see ShuttleDispatcher.prepare_input).

        # We want to optimize only the trips that have not been assigned to
        # any vehicle yet.
        trips = state.non_assigned_trips

        # We want to optimize only the vehicles that are at the hub.
        vehicles = []
        for vehicle in state.vehicles:
            route = state.route_by_vehicle_id[vehicle.id]
            if route.current_stop is not None and route.current_stop.location.label == self.__hub_location:
                vehicles.append(vehicle)

        return trips, vehicles

    def optimize(self, trips, vehicles, current_time, state):

        stops_list_by_vehicle_id = {}
        trip_ids_by_vehicle_id = {}

        vehicles_cyclic_list = cycle(vehicles)
        for trip in trips:

            vehicle = next(vehicles_cyclic_list)
            route = state.route_by_vehicle_id[vehicle.id]

            if route is not None:
                stops_list = self.__assign_trip_to_route(trip, route,
                                                         current_time)
                stops_list_by_vehicle_id[vehicle.id] = stops_list

                if vehicle.id not in trip_ids_by_vehicle_id:
                    trip_ids_by_vehicle_id[vehicle.id] = []

                trip_ids_by_vehicle_id[vehicle.id].append(trip.id)

        return stops_list_by_vehicle_id, trip_ids_by_vehicle_id

    def __assign_trip_to_route(self, trip, route, current_time):

        stops_list = []

        # First stop: initial location of the vehicle (hub)
        initial_arrival_time = current_time
        initial_position_stop_dict = {
            "stop_id": route.current_stop.location.label,
            "arrival_time": None,   # The arrival time of the first stop of the
                                    # list does not matter. It will not be
                                    # modified by the simulator since it is the
                                    # current stop and cannot be altered.
            "departure_time": initial_arrival_time
        }
        stops_list.append(initial_position_stop_dict)

        # Second stop: the origin location of the trip (request)
        hub_to_origin_travel_time = \
            self.__network.get_edge_data(route.current_stop.location.label,
                                         trip.origin.label)["length"]
        logger.warning(hub_to_origin_travel_time)
        origin_stop_arrival_time = initial_arrival_time + hub_to_origin_travel_time
        origin_stop_dict = {
            "stop_id": trip.origin.label,
            "arrival_time": origin_stop_arrival_time,
            "departure_time": origin_stop_arrival_time
        }
        stops_list.append(origin_stop_dict)

        # Third stop: the destination location of the trip (request)
        origin_to_destination_travel_time = \
            self.__network.get_edge_data(trip.origin.label,
                                         trip.destination.label)["length"]
        destination_stop_arrival_time = origin_stop_arrival_time + origin_to_destination_travel_time
        destination_stop_dict = {
            "stop_id": trip.destination.label,
            "arrival_time": destination_stop_arrival_time,
            "departure_time": destination_stop_arrival_time
        }
        stops_list.append(destination_stop_dict)

        # Last stop: the vehicle returns to the hub.
        destination_to_hub_travel_time = \
            self.__network.get_edge_data(trip.destination.label,
                                         self.__hub_location)["length"]
        last_stop_arrival_time = destination_stop_arrival_time + destination_to_hub_travel_time
        last_stop_dict = {
            "stop_id": self.__hub_location,
            "arrival_time": last_stop_arrival_time,
            "departure_time": None  # The departure time of the last stop does
                                    # not matter. It is set to math.inf.
        }
        stops_list.append(last_stop_dict)

        return stops_list
