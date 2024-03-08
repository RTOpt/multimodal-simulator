import logging

from itertools import cycle
from typing import Any, List, Tuple

from multimodalsim.optimization.dispatcher import Dispatcher, \
    OptimizedRoutePlan
from multimodalsim.optimization.state import State
from multimodalsim.simulator.vehicle import Route
import multimodalsim.simulator.request as request

logger = logging.getLogger(__name__)


class ShuttleHubSimpleNetworkDispatcher(Dispatcher):

    def __init__(self, network: Any, hub_location: str = "0"):
        """
        Parameters:
            network: networkx Graph
                A graph in which the nodes correspond to locations and the
                edges have an attribute "length" that represents the time it
                takes to travel between the locations of the two associated
                nodes.
            hub_location: string
                Label of the hub, i.e., the initial and final location of all
                the vehicles.
        """
        super().__init__()

        self.__network = network
        self.__hub_location = hub_location

    def prepare_input(self, state: State) \
            -> Tuple[List['request.Leg'], List[Route]]:
        """Before optimizing, we extract the legs and the routes that we want
        to be considered by the optimization algorithm. For the
        ShuttleSimpleDispatcher, we want to keep only the legs that have not
        been assigned to any route yet and the routes that are at the
        hub. Since by default all legs (i.e., state.next_legs) and all routes
        (i.e., state.route_by_vehicle_id.values()) are used for optimization
        (see ShuttleDispatcher.prepare_input), we must override the
        prepare_input method.
        """

        # The next legs that have not been assigned to any route yet are
        # assigned to the output variable selected_next_legs.
        selected_next_legs = state.non_assigned_next_legs

        # The routes associated with vehicles that are currently at the hub are
        # added to the output variable selected_routes.
        selected_routes = []
        for vehicle_id, route in state.route_by_vehicle_id.items():
            if route.current_stop is not None \
                    and route.current_stop.location.label \
                    == self.__hub_location:
                selected_routes.append(route)

        return selected_next_legs, selected_routes

    def optimize(self, selected_next_legs: List['request.Leg'],
                 selected_routes: List[Route], current_time: int,
                 state: State) -> List[OptimizedRoutePlan]:
        """Each non assigned next leg is assigned to the first route of a
        vehicle available at the hub. For each chosen route the optimization
        algorithm creates a route plan that consists in sending the
        associated vehicle to the leg origin, then to the leg destination,
        and, finally, to the hub (hub -> leg.origin -> leg.destination ->
        hub). The arrival time and the departure time of each stop is
        determined by the travel time between two stops, which is as a
        constant (see self.__travel_time).
        """

        route_plans = []
        routes_cyclic_list = cycle(selected_routes)
        for leg in selected_next_legs:
            route = next(routes_cyclic_list)

            if route is not None:
                route_plan = self.__create_route_plan(route, leg, current_time)

                route_plans.append(route_plan)

        return route_plans

    def __create_route_plan(self, route, leg, current_time):
        """For the route in argument, create a route plan made up of four
        stops:
          1. Hub
          2. Leg origin
          3. Leg destination
          4. Hub
        The arrival time is the same as the departure time, and it corresponds
        to the sum of the departure time of the previous stop and the travel
        time determined from the graph network. More precisely, the travel time
        corresponds to the "length" of an edge between the nodes associated
        with the origin stop and the destination stop.
        """

        route_plan = OptimizedRoutePlan(route)

        # First stop:
        #   -location: not modified since current stop (hub)
        #   -arrival and departure time: current time
        route_plan.update_current_stop_departure_time(current_time)

        # Second stop:
        #   -location: leg origin
        #   -arrival and departure time: current time + distance between hub
        #   and leg origin
        hub_to_origin_travel_time = self.__network.get_edge_data(
            route.current_stop.location.label, leg.origin.label)["length"]
        first_stop_time = current_time + hub_to_origin_travel_time
        origin_lon = self.__network.nodes[leg.origin.label]["lon"]
        origin_lat = self.__network.nodes[leg.origin.label]["lat"]
        route_plan.append_next_stop(leg.origin.label, first_stop_time,
                                    lon=origin_lon, lat=origin_lat)

        # Third stop:
        #   -location: leg destination
        #   -arrival and departure time: departure time of the previous stop
        #   + distance between leg origin and leg destination
        origin_to_destination_travel_time = self.__network.get_edge_data(
            leg.origin.label, leg.destination.label)["length"]
        second_stop_time = first_stop_time + origin_to_destination_travel_time
        destination_lon = self.__network.nodes[leg.destination.label]["lon"]
        destination_lat = self.__network.nodes[leg.destination.label]["lat"]
        route_plan.append_next_stop(leg.destination.label, second_stop_time,
                                    lon=destination_lon, lat=destination_lat)

        # Fourth (and last) stop:
        #   -location: hub
        #   -arrival time: departure time of the previous stop + distance
        #   between leg origin and leg destination
        destination_to_hub_travel_time = self.__network.get_edge_data(
            leg.destination.label, self.__hub_location)["length"]
        last_stop_time = second_stop_time + destination_to_hub_travel_time
        hub_lon = self.__network.nodes[self.__hub_location]["lon"]
        hub_lat = self.__network.nodes[self.__hub_location]["lat"]
        route_plan.append_next_stop(self.__hub_location, last_stop_time,
                                    lon=hub_lon, lat=hub_lat)

        route_plan.assign_leg(leg)

        return route_plan

