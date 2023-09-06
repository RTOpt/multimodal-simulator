import math
import logging

from itertools import groupby

from multimodalsim.optimization.shuttle.constraints_and_objective_function import \
    variables_declaration
from multimodalsim.optimization.shuttle.shuttle_dispatcher import ShuttleDispatcher, \
    OptimizedRoutePlan
from multimodalsim.optimization.shuttle.solution_construction import get_distances, \
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

        routes_with_current_stops = []
        for vehicle in state.vehicles:
            route = state.route_by_vehicle_id[vehicle.id]
            if len(route.onboard_legs) == 0 and len(route.assigned_legs) == 0:
                if route.current_stop is not None:
                    routes_with_current_stops.append(route)

        routes_sorted_by_departure_time = sorted(
            routes_with_current_stops,
            key=lambda x: x.current_stop.departure_time)

        return state.non_assigned_next_legs, routes_sorted_by_departure_time

    def optimize(self, selected_next_legs, selected_routes, current_time,
                 state):

        vehicles = [route.vehicle for route in selected_routes]
        trips = [leg.trip for leg in selected_next_legs]
        next_leg_by_trip_id = {leg.trip.id: leg for leg in selected_next_legs}

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

        route_plans_list = self.__create_route_plans_list(
            veh_trips_assignments_list, next_leg_by_trip_id, current_time,
            state)

        return route_plans_list

    def __create_route_plans_list(self, veh_trips_assignments_list,
                                  next_leg_by_trip_id, current_time, state):
        route_plans_list = []
        for veh_trips_assignment in veh_trips_assignments_list:
            trip_ids = [trip.id for trip in
                        veh_trips_assignment['assigned_requests']]
            next_stop_ids = [stop_id for stop_id, _
                             in groupby(veh_trips_assignment["route"])]
            route = state.route_by_vehicle_id[
                veh_trips_assignment["vehicle"].id]
            route_plan = self.__create_route_plan(route, trip_ids,
                                                  next_stop_ids,
                                                  next_leg_by_trip_id,
                                                  current_time)
            route_plans_list.append(route_plan)

        return route_plans_list

    def __create_route_plan(self, route, trip_ids, next_stop_ids,
                            next_leg_by_trip_id, current_time):

        route_plan = OptimizedRoutePlan(route)

        route_plan.update_current_stop_departure_time(current_time)

        departure_time = current_time
        previous_stop_id = next_stop_ids[0]
        for stop_id in next_stop_ids[1:]:
            distance = \
                self.__network[previous_stop_id][stop_id]['length']
            arrival_time = departure_time + distance
            departure_time = arrival_time + self.__boarding_time \
                if stop_id != next_stop_ids[-1] else math.inf

            route_plan.append_next_stop(stop_id, arrival_time, departure_time)

            previous_stop_id = stop_id

        for trip_id in trip_ids:
            leg = next_leg_by_trip_id[trip_id]
            route_plan.assign_leg(leg)

        return route_plan
