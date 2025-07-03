import logging
from typing import Tuple

from multimodalsim.optimization.dispatcher import OptimizedRoutePlan, \
    Dispatcher
from multimodalsim.optimization.state import State
from multimodalsim.simulator.vehicle import Route
import multimodalsim.simulator.request as request

logger = logging.getLogger(__name__)


class FixedLineReassignDispatcher(Dispatcher):

    def __init__(self) -> None:
        super().__init__()

    def prepare_input(self, state: State) \
            -> Tuple[list['request.Leg'], list[Route]]:
        """Before optimizing, we extract the legs and the routes that we want
        to be considered by the optimization algorithm. For the
        FixedLineDispatcher, we want to keep only the legs that have not
        been assigned to any route yet.
        """

        # # The next legs that have not been assigned to any route yet.
        # selected_next_legs = state.non_assigned_next_legs

        selected_next_legs = state.next_legs

        logger.warning("selected_next_legs:")
        for leg in selected_next_legs:
            logger.warning(leg.id)

        # All the routes
        selected_routes = state.route_by_vehicle_id.values()

        logger.warning("selected_routes:")
        for route in selected_routes:
            logger.warning(route.vehicle)

        return selected_next_legs, selected_routes

    def optimize(self, selected_next_legs: list['request.Leg'],
                 selected_routes: list[Route], current_time: float,
                 state: State) -> list[OptimizedRoutePlan]:
        """Each selected next leg is assigned to the optimal route. The optimal
        route is the one that has the earliest arrival time at destination
        (i.e. leg.destination)."""

        optimized_route_plans = []
        for leg in selected_next_legs:
            optimal_route = self.__find_optimal_route_for_leg(
                leg, selected_routes, current_time)

            if optimal_route is not None \
                    and (leg.assigned_vehicle is None
                         or optimal_route.vehicle.id
                         != leg.assigned_vehicle.id):

                if leg.assigned_vehicle is None:
                    optimized_route_plan = OptimizedRoutePlan(optimal_route)

                    # Use the current and next stops of the route.
                    optimized_route_plan.copy_route_stops()

                    optimized_route_plan.assign_leg(leg)
                    optimized_route_plans.append(optimized_route_plan)
                elif optimal_route.vehicle.id != leg.assigned_vehicle.id:
                    # Unassign the leg from the route of the already assigned
                    # vehicle
                    logger.error("UNASSIGN")
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
                    
                    # TODO: Check why leg is not removed from
                    #  Route.assigned_legs of the previous route

        return optimized_route_plans

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
