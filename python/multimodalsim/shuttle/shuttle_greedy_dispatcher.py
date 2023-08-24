import math
import logging

from itertools import groupby

from multimodalsim.optimization.dispatcher import ShuttleDispatcher
from multimodalsim.shuttle.constraints_and_objective_function import \
    variables_declaration
from multimodalsim.shuttle.solution_construction import \
    cvrp_pdp_tw_he_obj_cost, get_distances, get_durations, update_data, \
    set_initial_solution, improve_solution, get_routes_dict
from multimodalsim.simulator.vehicle import Stop, LabelLocation

logger = logging.getLogger(__name__)

class ShuttleGreedyDispatcher(ShuttleDispatcher):

    def __init__(self, network):
        super().__init__()
        self.__network = network

        # The time difference between the arrival and the departure time (10
        # seconds).
        self.__boarding_time = 10

    def optimize(self, trips, vehicles, current_time, state):

        route_by_vehicle_id, trip_ids_by_vehicle_id = self.__optimize(
            trips, vehicles, current_time)

        return route_by_vehicle_id, trip_ids_by_vehicle_id

    def __optimize(self, non_assigned_requests, vehicles, current_time):

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
                                                        non_assigned_requests,
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

        route_stop_ids_by_vehicle_id = self.__extract_next_stops_by_vehicle(
            veh_trips_assignments_list)

        trip_ids_by_vehicle_id = self.__extract_trips_by_vehicle(
            veh_trips_assignments_list)

        route_by_vehicle_id = self.__extract_route_by_vehicle_id(
            route_stop_ids_by_vehicle_id, current_time)

        return route_by_vehicle_id, trip_ids_by_vehicle_id

    def __extract_next_stops_by_vehicle(self, veh_trips_assignments_list):
        route_stop_ids_by_vehicle_id = {}
        for veh_trips_assignment in veh_trips_assignments_list:
            next_stop_ids = [stop_id for stop_id, _
                             in groupby(veh_trips_assignment["route"])]
            route_stop_ids_by_vehicle_id[
                veh_trips_assignment["vehicle"].id] = next_stop_ids

        return route_stop_ids_by_vehicle_id

    def __extract_route_by_vehicle_id(self, route_stop_ids_by_vehicle_id,
                                      current_time):

        route_by_vehicle_id = {}
        for vehicle_id, route_stop_ids \
                in route_stop_ids_by_vehicle_id.items():
            route = self.__extract_route(route_stop_ids, current_time)
            route_by_vehicle_id[vehicle_id] = route

        return route_by_vehicle_id

    def __extract_route(self, route_stop_ids, current_time):
        route = [{
            "stop_id": route_stop_ids[0],
            "arrival_time": None,
            "departure_time": current_time
        }]

        departure_time = current_time
        previous_stop_id = route_stop_ids[0]
        for stop_id in route_stop_ids[1:]:
            logger.warning(previous_stop_id)
            logger.warning(stop_id)
            distance = \
                self.__network[previous_stop_id][stop_id]['length']
            arrival_time = departure_time + distance
            departure_time = arrival_time + self.__boarding_time \
                if stop_id != route_stop_ids[-1] else math.inf

            stop_info = {
                "stop_id": stop_id,
                "arrival_time": arrival_time,
                "departure_time": departure_time
            }

            route.append(stop_info)
            previous_stop_id = stop_id

        return route

    def __extract_trips_by_vehicle(self, veh_trips_assignments_list):
        trip_ids_by_vehicle_id = {}
        for veh_trips_assignment in veh_trips_assignments_list:
            trip_ids = [trip.id for trip in
                        veh_trips_assignment['assigned_requests']]
            trip_ids_by_vehicle_id[
                veh_trips_assignment["vehicle"].id] = trip_ids

        return trip_ids_by_vehicle_id
