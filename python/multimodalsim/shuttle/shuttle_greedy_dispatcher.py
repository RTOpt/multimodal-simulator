import math
import logging

from itertools import groupby

from multimodalsim.optimization.dispatcher import ShuttleDispatcher
from multimodalsim.shuttle.constraints_and_objective_function import \
    variables_declaration
from multimodalsim.shuttle.solution_construction import get_distances, \
    get_durations, update_data, set_initial_solution, improve_solution

logger = logging.getLogger(__name__)


class ShuttleGreedyDispatcher(ShuttleDispatcher):

    def __init__(self, network):
        super().__init__()
        self.__network = network

        # The time difference between the arrival and the departure time (10
        # seconds).
        self.__boarding_time = 10

    def prepare_input(self, state):
        # Extract from the state the trips and the vehicles that should be used for optimization.

        non_assigned_vehicles = []
        vehicles_with_current_stops = []
        for vehicle in state.vehicles:
            route = state.route_by_vehicle_id[vehicle.id]
            if len(route.onboard_legs) == 0 and len(route.assigned_legs) == 0:
                non_assigned_vehicles.append(vehicle)
                if route.current_stop is not None:
                    vehicles_with_current_stops.append(vehicle)

        vehicles_sorted_by_departure_time = sorted(
            vehicles_with_current_stops,
            key=lambda x:
            state.route_by_vehicle_id[x.id].current_stop.departure_time)

        return state.non_assigned_trips, \
               vehicles_sorted_by_departure_time

    def optimize(self, trips, vehicles, current_time, state):

        max_travel_time = 7200
        distances = get_distances(self.__network)
        # service duration for costumer i
        # it will be considered as 0
        # d = [0 for i in range(len(self.__network.nodes))]
        d = {i: 0 for i in self.__network.nodes}

        # travel time between vertices
        # let's assume that it depends just on the distance between vertices
        t = get_durations(self.__network)

        P, D, q, T, non_assigned_requests = update_data(self.__network,
                                                        trips,
                                                        vehicles)

        V_p = set([req.destination.label for req in P]).union(
            set([req.origin.label for req in D]))
        # V_p = non_assigned_requests

        X, Y, U, W, R = variables_declaration(self.__network.nodes, vehicles,
                                              non_assigned_requests)
        X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org, veh_trips_assignments_list = \
            set_initial_solution(self.__network, non_assigned_requests,
                                 vehicles, X, Y,
                                 U, W, R,
                                 distances, d, t, V_p, P, D, q, T,
                                 max_travel_time)
        X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org, veh_trips_assignments_list = \
            improve_solution(self.__network, non_assigned_requests, vehicles,
                             X, Y, U,
                             W, R, X_org, Y_org, U_org, W_org, R_org,
                             distances, d, t, V_p, veh_trips_assignments_list,
                             P,
                             D, q, T, max_travel_time)

        stop_ids_by_vehicle_id = self.__extract_next_stops_by_vehicle(
            veh_trips_assignments_list)

        trip_ids_by_vehicle_id = self.__extract_trips_by_vehicle(
            veh_trips_assignments_list)

        stops_list_by_vehicle_id = self.__extract_stops_list_by_vehicle_id(
            stop_ids_by_vehicle_id, current_time)

        return stops_list_by_vehicle_id, trip_ids_by_vehicle_id

    def __extract_next_stops_by_vehicle(self, veh_trips_assignments_list):
        stop_ids_by_vehicle_id = {}
        for veh_trips_assignment in veh_trips_assignments_list:
            next_stop_ids = [stop_id for stop_id, _
                             in groupby(veh_trips_assignment["route"])]
            stop_ids_by_vehicle_id[
                veh_trips_assignment["vehicle"].id] = next_stop_ids

        return stop_ids_by_vehicle_id

    def __extract_stops_list_by_vehicle_id(self, stop_ids_by_vehicle_id,
                                      current_time):

        stops_list_by_vehicle_id = {}
        for vehicle_id, stop_ids \
                in stop_ids_by_vehicle_id.items():
            stops_list = self.__extract_stops_list(stop_ids, current_time)
            stops_list_by_vehicle_id[vehicle_id] = stops_list

        return stops_list_by_vehicle_id

    def __extract_stops_list(self, stop_ids, current_time):
        stops_list = [{
            "stop_id": stop_ids[0],
            "arrival_time": None,
            "departure_time": current_time
        }]

        departure_time = current_time
        previous_stop_id = stop_ids[0]
        for stop_id in stop_ids[1:]:
            distance = \
                self.__network[previous_stop_id][stop_id]['length']
            arrival_time = departure_time + distance
            departure_time = arrival_time + self.__boarding_time \
                if stop_id != stop_ids[-1] else math.inf

            stop_dict = {
                "stop_id": stop_id,
                "arrival_time": arrival_time,
                "departure_time": departure_time
            }

            stops_list.append(stop_dict)
            previous_stop_id = stop_id

        return stops_list

    def __extract_trips_by_vehicle(self, veh_trips_assignments_list):
        trip_ids_by_vehicle_id = {}
        for veh_trips_assignment in veh_trips_assignments_list:
            trip_ids = [trip.id for trip in
                        veh_trips_assignment['assigned_requests']]
            trip_ids_by_vehicle_id[
                veh_trips_assignment["vehicle"].id] = trip_ids

        return trip_ids_by_vehicle_id
