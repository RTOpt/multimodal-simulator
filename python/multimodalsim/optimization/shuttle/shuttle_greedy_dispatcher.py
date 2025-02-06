import math
import logging
import random
from typing import List, Any, Dict, Tuple

from multimodalsim.optimization.dispatcher import Dispatcher, \
    OptimizedRoutePlan
from multimodalsim.optimization.state import State
from multimodalsim.simulator.request import Trip, Leg
from multimodalsim.simulator.vehicle import Vehicle, Route

logger = logging.getLogger(__name__)


class ShuttleGreedyDispatcher(Dispatcher):
    """Optimize the vehicle routing and the trip-route assignment. This method relies on three other methods:
            1. prepare_input
            2. optimize
            3. create_route_plans_list
    """

    def __init__(self,
                 network: Any,
                 vehicles: List[Vehicle],
                 time_window: float) -> None:
        """
        Input:
        ------------
            network: The transport network over which the dispatching occurs.
            vehicles: Set of input vehicles.
            time_window: Maximum time allowed to serve a request.
        """

        super().__init__()
        self.__network = network
        self.__rejected_trips = []
        self.__durations = self.__get_durations()
        self.__vehicle_request_assign = {}

        self.__time_window = time_window

        for vehicle in vehicles:
            self.__vehicle_request_assign[vehicle.id] = {
                'vehicle': vehicle,  # Vehicle object
                'assigned_requests': [],  # List of assigned requests
                'departure_stop': None,  # Last stop point of the previous
                # iteration (current route plan)
                'departure_time': 0,  # Departure time from the departure_stop
                'last_stop': None,  # Last stop assigned to the vehicle in
                # the current solution
                'last_stop_time': 0,  # Departure time from the stop in the
                # current solution
                'assign_possible': False,  # Determine the possibility of
                # assigning a trip to the vehicle
                'reach_time': math.inf  # Time required for the vehicle to
                # reach the request
            }

    def prepare_input(self, state: State) -> Tuple[list[Leg], list[Route]]:
        """ Function: Extract from the state the next legs and the routes that
            are sent as input to the optimize method (i.e. the legs and the
            routes that you want to optimize).

            All next legs and all routes existing in the environment at
            the time of optimization will be optimized.

            Input:
            ------------
                state: An object of type State that corresponds to a partial
                deep copy of the environment.

            Output:
            ------------
                selected_next_legs: A list of objects of type Trip that
                correspond to the trips (i.e., passengers or requests) that
                should be considered by the optimize method.

                selected_routes: A list of objects of type Route that
                correspond to the routes associated with the vehicles that
                should be considered by the optimize method.

            Note that if selected_next_legs or selected_routes is empty, no
            optimization will be done.
            """

        selected_route = []
        self.__rejected_trips = [
            leg.trip for leg in state.non_assigned_next_legs
            if leg.trip.ready_time + self.__time_window < state.current_time
        ]
        rejected_ids = {trip.id for trip in self.__rejected_trips}

        # remove rejected trips from the list of non-assigned trips
        selected_next_legs = [
            leg for leg in state.non_assigned_next_legs
            if leg.trip.id not in rejected_ids
        ]

        if selected_next_legs:
            for vehicle in state.vehicles:
                route = state.route_by_vehicle_id[vehicle.id]
                selected_route.append(route)
        current_routes = [state.route_by_vehicle_id[vehicle.id] for vehicle in
                          state.vehicles]
        self.__update_vehicle_state(current_routes, state.current_time)
        return selected_next_legs, selected_route

    def optimize(
            self,
            selected_next_legs: List[Leg],
            selected_routes: List[Route],
            current_time: float,
            state: State
    ) -> List[OptimizedRoutePlan]:

        """
        Function: Determine the vehicle routing and the trip-route assignment
            according to an optimization algorithm. The optimization algorithm
            should be called in this method.

            Input:
            ------------
                selected_next_legs: List[Leg]
                    List of the next legs to be optimized.
                selected_routes: List[Route]
                    List of the routes to be optimized.
                current_time: int
                    Current time of the simulation.
                state: Any
                An object of type State that corresponds to a partial deep copy of the environment.

            Output:
            ------------
                optimized_route_plans: List of the optimized route plans. Each route
                plan is an object of type OptimizedRoutePlan.
        """

        # non-assigned requests
        trips = [leg.trip for leg in selected_next_legs]
        trips = sorted(trips, key=lambda x: x.ready_time)
        next_leg_by_trip_id = {leg.trip.id: leg for leg in selected_next_legs}

        # Assign the requests to a vehicle according to a greedy algorithm.
        sorted_requests = sorted(trips, key=lambda x: x.ready_time)
        self.__greedy_assign(sorted_requests, self.__rejected_trips)

        veh_trips_assignments_list = list(
            self.__vehicle_request_assign.values())

        # Remove the vehicles without any changes in request-assign
        veh_trips_assignments_list = [temp_dict for temp_dict
                                      in veh_trips_assignments_list if
                                      temp_dict['assigned_requests']]
        route_plans_list = \
            self.__create_route_plans_list(veh_trips_assignments_list,
                                           next_leg_by_trip_id,
                                           current_time, state)
        return route_plans_list

    def __create_route_plans_list(self, veh_trips_assignments_list,
                                  next_leg_by_trip_id, current_time, state) \
            -> List[OptimizedRoutePlan]:
        """
            Function: Constructs a list of optimized route plans based on vehicle assignments and current state.

                Input:
                ------------
                    veh_trips_assignments_list: A list of dictionaries, each
                    representing a vehicle's assigned trips and its last stop.
                    next_leg_by_trip_id: A dictionary mapping trip IDs to their
                    corresponding next legs.
                    current_time: The current time of the simulation.
                    state: The current state of the environment, containing
                    information about vehicles and routes.

                Output:
                ------------
                    route_plans_list : A list of OptimizedRoutePlan instances,
                    each representing an optimized route for a vehicle.
        """
        route_plans_list = []
        for veh_trips_assignment in veh_trips_assignments_list:
            trip_ids = [trip.id for trip
                        in veh_trips_assignment['assigned_requests']]

            route = state.route_by_vehicle_id[
                veh_trips_assignment["vehicle"].id]

            if len(route.next_stops) <= 1:
                route_plan = self.__create_route_plan(
                    route, trip_ids, veh_trips_assignment['departure_stop'],
                    next_leg_by_trip_id, current_time)
                route_plans_list.append(route_plan)

        return route_plans_list

    def __create_route_plan(self, route, trip_ids, departure_stop_id,
                            next_leg_by_trip_id, current_time) \
            -> OptimizedRoutePlan:
        """
            Function: Creates an optimized route plan for a vehicle based on
            assigned trips and current state.

                Input:
                ------------
                route: The current route of the vehicle.
                trip_ids: A list of trip IDs assigned to the vehicle.
                departure_stop_id: The ID of the location from which the
                vehicle will depart.
                next_leg_by_trip_id: A dictionary mapping trip IDs to their
                corresponding next legs.
                current_time: The current time of the simulation.

                Output:
                ------------
                OptimizedRoutePlan : An optimized route plan for the vehicle.
        """

        route_plan = OptimizedRoutePlan(route)

        if len(route.next_stops) == 0:
            # If the current route has no stops, update the departure time of
            # the current stop to the current time.
            last_stop = route.previous_stops[
                -1] if route.current_stop is None else route.current_stop
            if last_stop.departure_time < current_time or last_stop.departure_time == math.inf:
                last_stop.departure_time = current_time
            departure_time = last_stop.departure_time
            # route_plan.update_current_stop_departure_time(departure_time)
            route_plan.update_current_stop_departure_time(current_time)
        else:
            # If there are existing stops, set the departure time of the last
            # stop to its arrival time.
            route.next_stops[-1].departure_time = route.next_stops[
                -1].arrival_time
            departure_time = route.next_stops[-1].departure_time
            route_plan.copy_route_stops()

        for index, trip_id in enumerate(trip_ids):
            if len(route_plan.assigned_legs) > 0:
                break

            leg = next_leg_by_trip_id[trip_id]

            # Calculate and add pick-up stop.
            travel_time_to_pick = \
                self.__network.nodes[departure_stop_id]['shortest_paths'][
                    leg.trip.origin.label]['total_duration']
            arrival_time = departure_time + travel_time_to_pick
            if arrival_time < leg.trip.ready_time:
                break
            departure_time = arrival_time
            origin_lon = leg.trip.origin.lon
            origin_lat = leg.trip.origin.lat
            route_plan.append_next_stop(leg.trip.origin.label, arrival_time,
                                        departure_time, lon=origin_lon,
                                        lat=origin_lat, legs_to_board=[leg])
            route_plan.assign_leg(leg)

            # Calculate and add drop-off stop.
            travel_time = self.__network.nodes[leg.trip.origin.label][
                'shortest_paths'][leg.trip.destination.label]['total_duration']
            arrival_time = departure_time + travel_time
            departure_time = arrival_time if index != len(
                trip_ids) - 1 else math.inf
            destination_lon = leg.trip.destination.lon
            destination_lat = leg.trip.destination.lat
            route_plan.append_next_stop(leg.trip.destination.label,
                                        arrival_time, departure_time,
                                        lon=destination_lon,
                                        lat=destination_lat,
                                        legs_to_alight=[leg])
            departure_stop_id = leg.trip.destination.label

        return route_plan

    def __determine_available_vehicles(self, trip: Trip) -> None:
        """ Function: determine the possibility of assigning a trip to vehicles

            Input:
            ------------
                trip : request to serve
        """

        for veh_id, veh_info in self.__vehicle_request_assign.items():
            reach_time = self.__calc_reach_time(veh_info, trip)

            veh_info['assign_possible'] = (reach_time <= trip.ready_time
                                           + self.__time_window)
            veh_info['reach_time'] = reach_time \
                if reach_time <= trip.ready_time + self.__time_window \
                else math.inf

    def __greedy_assign(self, non_assigned_trips: List[Trip],
                        rejected_trips: List[Trip]) -> List[Trip]:
        """
        Function: find a solution based on greedy method to assign ride
        requests to vehicles after arrival

            Input:
            ------------
                non_assigned_trips : set of customers that are not assigned to
                be served
                rejected_trips: List of trips that are rejected in the
                optimization process.

            Output:
            ------------
                assigned_requests: List of assigned requests
        """
        # for each request find the best insertion position
        assigned_requests = []
        for trip in non_assigned_trips:
            self.__determine_available_vehicles(trip)
            # filter available vehicles

            available_vehicles = {veh_id: temp_dict for veh_id, temp_dict in
                                  self.__vehicle_request_assign.items()
                                  if temp_dict['assign_possible']}

            if available_vehicles:
                # Select the vehicle with the smallest reach time
                selected_vehicle_id = min(available_vehicles.items(),
                                          key=lambda x: x[1]["reach_time"])[0]

                selected_vehicle_info = available_vehicles[selected_vehicle_id]

                # Assign the trip to the selected vehicle
                self.__assign_trip_to_vehicle(selected_vehicle_info, trip)
                assigned_requests.append(trip)
                logger.debug(
                    f"Greedy: Assigned trip {trip.id} to vehicle "
                    f"{selected_vehicle_id}.")
            else:
                rejected_trips.append(trip)
                logger.debug(
                    f"Greedy: Rejected trip {trip.id} as no vehicle can serve "
                    f"it.")

        return assigned_requests

    def __update_vehicle_state(self, selected_routes: List[Route],
                               current_time: float) -> None:
        """
            Function: Update departure time and point for the vehicles based
            on the current routes
            Input:
            ------------
                selected_routes : current vehicle routes
                current_time : current time of the simulation
        """
        for route in selected_routes:
            vehicle_id = route.vehicle.id
            vehicle_info = self.__vehicle_request_assign.get(vehicle_id, {})
            vehicle_info['assigned_requests'] = []

            if not route.next_stops:
                # vehicle route is empty
                last_stop = route.previous_stops[-1] \
                    if route.current_stop is None else route.current_stop
                departure_time = last_stop.departure_time \
                    if last_stop.departure_time != math.inf \
                    else last_stop.arrival_time
                if departure_time < current_time:
                    departure_time = current_time
                vehicle_info.update({
                    'departure_time': departure_time,
                    'departure_stop': last_stop.location.label,
                    'last_stop_time': departure_time,
                    'last_stop': last_stop.location.label,
                })
            else:
                last_stop = route.next_stops[-1]
                vehicle_info.update({
                    'departure_time': last_stop.arrival_time,
                    'departure_stop': last_stop.location.label,
                    'last_stop_time': last_stop.arrival_time,
                    'last_stop': last_stop.location.label,
                })

            self.__vehicle_request_assign[vehicle_id] = vehicle_info

    def __calc_reach_time(self, vehicle_info: Dict, trip: Any) -> float:
        """
        Function: Calculate the time required for a vehicle to reach the trip
        origin.

        Input:
            ------------
                vehicle_info : dictionary of the selected vehicle to assign the
                request
                trip : request to be assigned
        Output:
            ------------
                trip_reach_time: the time required for a vehicle to reach the
                trip origin
        """
        reach_time = (vehicle_info['last_stop_time']
                      + self.__durations[vehicle_info['last_stop']][
                          trip.origin.label])

        trip_reach_time = max(reach_time, trip.ready_time)

        return trip_reach_time

    def __assign_trip_to_vehicle(self, vehicle_info: Dict, trip: Trip) -> None:
        """
        Function: Assign trip to a vehicle

        Input:
        ------------
            vehicle_info : dictionary of the selected vehicle to assign the
            request
            trip : request to be assigned
        """
        vehicle_info['assigned_requests'].append(trip)
        reach_time_to_pickup = self.__calc_reach_time(vehicle_info, trip)

        travel_time = \
            self.__network.nodes[trip.origin.label]['shortest_paths'][
                trip.destination.label]['total_duration']
        vehicle_info['last_stop_time'] = reach_time_to_pickup + travel_time

        vehicle_info['last_stop'] = trip.destination.label

    def __get_durations(self) -> Dict[Any, Dict]:
        """
        Function: calculate the shortest travel time between each pair of
        stop nodes in the network graph
        """

        durations = {}
        for node1, data in self.__network.nodes(data=True):
            if node1 not in durations:
                durations[node1] = {}
            for node2 in self.__network.nodes():
                durations[node1][node2] = round(
                    data['shortest_paths'][node2]['total_duration'], 0)

        return durations
