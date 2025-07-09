import logging
from typing import Tuple, Optional
import math

from multimodalsim.optimization.dispatcher import OptimizedRoutePlan, \
    Dispatcher
from multimodalsim.optimization.state import State
from multimodalsim.simulator.vehicle import Vehicle, Route
from multimodalsim.simulator.stop import Stop
import multimodalsim.simulator.request as request
import multimodalsim.optimization.optimization as optimization_module


logger = logging.getLogger(__name__)


class FixedLineSkipStopDispatcher(Dispatcher):

    def __init__(self,
                 skip_stops_by_vehicle_id:
                 dict[str | int, list[tuple[str, float]]] = None,
                 walk_time: float = 120, walk_connection_time: float = 30) -> None:
        """
        skip_stop_by_vehicle_id: Dictionary where each key is a vehicle id and
        the corresponding value is a list of pairs specifying the id of the 
        stop that has to be skipped by the vehicle and the time after which 
        the decision to skip the stop can be taken.
        """

        super().__init__()
        self.__skip_stops_by_vehicle_id = skip_stops_by_vehicle_id \
            if skip_stops_by_vehicle_id is not None else {}
        self.__walk_time = walk_time
        self.__walk_connection_time = walk_connection_time

        self.__nb_walk_vehicles = 0

    def prepare_input(self, state: State) \
            -> Tuple[list['request.Leg'], list[Route]]:
        """Before optimizing, we extract the legs and the routes that we want
        to be considered by the optimization algorithm. For the
        FixedLineDispatcher, we want to keep only the legs that have not
        been assigned to any route yet.
        """

        # # The next legs that have not been assigned to any route yet.
        # selected_next_legs = state.non_assigned_next_legs

        logger.warning("next_legs:")
        for leg in state.next_legs:
            logger.warning(f"{leg.id}: trip: {leg.trip}")

        next_legs_no_current_leg = [leg for leg in state.next_legs
                                    if leg.trip.current_leg is None]
        selected_next_legs = next_legs_no_current_leg

        logger.warning("selected_next_legs:")
        for leg in selected_next_legs:
            logger.warning(leg.id)

        # All the routes
        selected_routes = list(state.route_by_vehicle_id.values())

        logger.warning("selected_routes:")
        for route in selected_routes:
            logger.warning(route.vehicle)

        return selected_next_legs, selected_routes

    def optimize(self, selected_next_legs: list['request.Leg'],
                 selected_routes: list[Route], current_time: float,
                 state: State) \
            -> tuple[list[OptimizedRoutePlan],
                     Optional['optimization_module.OptimizationResult']]:
        """Each selected next leg is assigned to the optimal route. The optimal
        route is the one that has the earliest arrival time at destination
        (i.e. leg.destination)."""

        optimized_route_plans = []

        new_requests = []

        modified_requests, modified_vehicles, new_vehicles = \
            self.__skip_all_stops(selected_routes, current_time, state)

        logger.warning(f"new_vehicles: {len(new_vehicles)}")

        logger.warning(f"selected_routes: {len(selected_routes)}")
        for route in selected_routes:
            logger.warning(f"{route}")

        for leg in selected_next_legs:
            optimal_route = self.__find_optimal_route_for_leg(
                leg, selected_routes, current_time)

            logger.warning(f"leg: {leg.id} (assigned_vehicle: {leg.assigned_vehicle}) | optimal_route: {optimal_route}")

            if optimal_route is not None \
                    and (leg.assigned_vehicle is None
                         or optimal_route.vehicle.id
                         != leg.assigned_vehicle.id):

                logger.error(f"ASSIGN: {leg.id} -> {optimal_route.vehicle.id}")

                if leg.assigned_vehicle is None:
                    optimized_route_plan = OptimizedRoutePlan(optimal_route)

                    # Use the current and next stops of the route.
                    optimized_route_plan.copy_route_stops()

                    optimized_route_plan.assign_leg(leg)
                    optimized_route_plans.append(optimized_route_plan)
                elif optimal_route.vehicle.id != leg.assigned_vehicle.id:
                    logger.error("REASSIGN")
                    # Unassign the leg from the route of the already assigned
                    # vehicle
                    previous_route = state.route_by_vehicle_id[
                        leg.assigned_vehicle.id]
                    previous_route_plan = OptimizedRoutePlan(previous_route)
                    previous_route_plan.copy_route_stops()
                    previous_route_plan.unassign_leg(leg.id)
                    optimized_route_plans.append(previous_route_plan)

                    # Assign leg to optimal new route plan
                    optimized_route_plan = OptimizedRoutePlan(optimal_route)
                    optimized_route_plan.copy_route_stops()
                    optimized_route_plan.assign_leg(leg)
                    optimized_route_plans.append(optimized_route_plan)

        # for route_plan in optimized_route_plans:
        #     self.__skip_stop(route_plan, selected_next_legs, current_time,
        #                      state)

        optimization_result = optimization_module.OptimizationResult(
            state, modified_requests, modified_vehicles, new_requests,
            new_vehicles)

        return optimized_route_plans, optimization_result

    def __find_optimal_route_for_leg(self, leg, selected_routes, current_time):

        origin_stop_id = leg.origin.label
        destination_stop_id = leg.destination.label

        optimal_route = None
        earliest_arrival_time = None
        for route in selected_routes:
            origin_departure_time, destination_arrival_time = \
                self.__get_origin_departure_time_and_destination_arrival_time(
                    route, origin_stop_id, destination_stop_id)

            if origin_departure_time is not None \
                    and origin_departure_time > current_time \
                    and origin_departure_time >= leg.trip.ready_time \
                    and destination_arrival_time is not None \
                    and destination_arrival_time <= leg.trip.due_time \
                    and (earliest_arrival_time is None
                         or destination_arrival_time < earliest_arrival_time):
                earliest_arrival_time = destination_arrival_time
                optimal_route = route

        return optimal_route

    def __get_origin_departure_time_and_destination_arrival_time(
            self, route, origin_stop_id, destination_stop_id):
        origin_stop = self.__get_stop_by_stop_id(origin_stop_id, route)
        destination_stop = self.__get_stop_by_stop_id(destination_stop_id,
                                                      route)

        origin_departure_time = None
        destination_arrival_time = None
        if origin_stop is not None and destination_stop is not None \
                and origin_stop.departure_time < destination_stop.arrival_time:
            origin_departure_time = origin_stop.departure_time
            destination_arrival_time = destination_stop.arrival_time

        return origin_departure_time, destination_arrival_time

    def __get_stop_by_stop_id(self, stop_id, route):
        found_stop = None
        if route.current_stop is not None and stop_id \
                == route.current_stop.location.label:
            found_stop = route.current_stop

        for stop in route.next_stops:
            if stop_id == stop.location.label:
                found_stop = stop

        return found_stop

    def __skip_all_stops(self, selected_routes: list[Route],
                    current_time: float, state: State) \
            -> tuple[list[request.Trip], list[Vehicle], list[Vehicle]]:

        all_modified_requests = []
        all_modified_vehicles = []
        all_new_walk_vehicles = []

        logger.warning(f"selected_routes: {len(selected_routes)}")
        logger.warning(f"type selected_routes: {type(selected_routes)}")
        for route in selected_routes:
            logger.warning(f"{route.vehicle.id}: {route.vehicle.id in self.__skip_stops_by_vehicle_id}")
            if route.vehicle.id in self.__skip_stops_by_vehicle_id:
                skip_stops_list = self.__skip_stops_by_vehicle_id[
                    route.vehicle.id]
                modified_requests, new_walk_vehicles, stop_skipped = \
                    self.__skip_route_stops(route, skip_stops_list,
                                            current_time, state)
                all_modified_requests.extend(modified_requests)
                all_new_walk_vehicles.extend(new_walk_vehicles)
                if stop_skipped:
                    all_modified_vehicles.append(route.vehicle)

        return all_modified_requests, all_modified_vehicles, \
               all_new_walk_vehicles

    def __skip_route_stops(self, route: Route,
                           skip_stops_list: list[tuple[str, float]],
                           current_time: float, state: State) \
            -> tuple[list[request.Trip], list[Vehicle], bool]:

        all_new_walk_vehicles = []
        all_modified_requests = []

        stop_skipped = False

        for (skip_stop_id, skip_stop_time) in skip_stops_list:
            if current_time >= skip_stop_time:
                stop_to_skip = None
                next_stop = None
                for stop in route.next_stops:

                    if stop_to_skip is not None:
                        next_stop = stop
                        break

                    if stop.location.label == skip_stop_id:
                        stop_to_skip = stop

                if stop_to_skip is not None and next_stop is not None:
                    modified_requests, new_walk_vehicles = \
                        self.__reassign_passengers_to_alight(
                            route, stop_to_skip, next_stop, current_time,
                            state)

                    all_modified_requests.extend(modified_requests)
                    all_new_walk_vehicles.extend(new_walk_vehicles)

                    route.next_stops.remove(stop_to_skip)

                    stop_skipped = True

                    logger.warning(f"route: {route}")

        return all_modified_requests, all_new_walk_vehicles, stop_skipped

    def __reassign_passengers_to_alight(
            self, route: Route, stop_to_skip: Stop, next_stop: Stop,
            current_time: float, state: State) -> tuple[list[request.Trip],
                                                        list[Vehicle]]:
        """Reassign the passengers to alight of the skip stop to the next
        stop"""

        modified_requests = []
        new_walk_vehicles = []

        for trip in stop_to_skip.passengers_to_alight:
            old_leg = self.__get_current_leg_corresponding_to_trip(trip, state)

            new_destination = next_stop.location
            new_leg = request.Leg(
                old_leg.id, old_leg.origin, new_destination,
                old_leg.nb_passengers, old_leg.release_time,
                old_leg.ready_time, old_leg.due_time, old_leg.trip)
            new_leg.assigned_vehicle = route.vehicle
            trip.current_leg = new_leg

            walk_vehicle, _ = self.__create_walk_vehicle(
                stop_to_skip, next_stop, old_leg.nb_passengers, current_time,
                state)

            walk_leg_id = "w" + str(old_leg.id)
            new_walk_leg_destination = old_leg.destination
            new_walk_leg = request.Leg(
                walk_leg_id, new_destination, new_walk_leg_destination,
                old_leg.nb_passengers, old_leg.release_time,
                old_leg.ready_time, old_leg.due_time, old_leg.trip)
            # new_walk_leg.assigned_vehicle = walk_vehicle

            trip.next_legs.insert(0, new_walk_leg)

            modified_requests.append(trip)
            new_walk_vehicles.append(walk_vehicle)


        next_stop.passengers_to_alight.extend(
            stop_to_skip.passengers_to_alight)

        stop_to_skip.passengers_to_alight.clear()

        return modified_requests, new_walk_vehicles

    def __get_current_leg_corresponding_to_trip(
            self, trip: 'request.Trip', state: State) -> 'request.Leg':
        found_leg = None
        for leg in state.current_legs:
            logger.error(f"leg.trip: {leg.trip} | trip.id: {trip.id}")
            if leg.trip.id == trip.id:
                found_leg = leg

        return found_leg

    def __create_walk_vehicle(self, stop_to_skip: Stop, next_stop: Stop,
                              nb_passengers, current_time: float,
                              state: State) -> tuple[Vehicle, Route]:

        logger.warning(f"next_stop: {next_stop}")

        # Create vehicle
        walk_stop_time = next_stop.arrival_time + self.__walk_connection_time
        walk_start_stop = Stop(
            walk_stop_time, walk_stop_time,
            next_stop.location)

        logger.warning(f"walk_stop_time: {walk_stop_time} | self.__walk_time: {self.__walk_time}")

        walk_end_stop = Stop(
            walk_stop_time + self.__walk_time, math.inf,
            stop_to_skip.location)
        walk_next_stops = [walk_end_stop]

        mode = "walk"
        vehicle_id = "w" + str(self.__nb_walk_vehicles + 1)
        self.__nb_walk_vehicles += 1

        walk_vehicle = Vehicle(vehicle_id, walk_start_stop.arrival_time,
                               walk_start_stop, nb_passengers, current_time,
                               walk_end_stop.arrival_time, mode)

        walk_route = Route(walk_vehicle, walk_next_stops)

        state.route_by_vehicle_id[walk_vehicle.id] = walk_route
        state.vehicles.append(walk_vehicle)

        return walk_vehicle, walk_route
