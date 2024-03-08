import logging
import math
from typing import List, Tuple, Optional

import multimodalsim.optimization.optimization as optimization_module
from multimodalsim.optimization.state import State
import multimodalsim.simulator.request as request
from multimodalsim.simulator.stop import Stop, LabelLocation
from multimodalsim.simulator.vehicle import Route

logger = logging.getLogger(__name__)


class Dispatcher:

    def __init__(self):
        super().__init__()

    def dispatch(self, state: State):
        """Optimize the vehicle routing and the trip-route assignment. This
        method relies on three other methods:
            1. prepare_input
            2. optimize
            3. process_optimized_route_plans
        The optimize method must be overriden. The other two methods can be
        overriden to modify some specific behaviors of the dispatching process.

        Input:
            -state: An object of type State that corresponds to a partial deep
             copy of the environment.

        Output:
            -optimization_result: An object of type OptimizationResult, that
             specifies, based on the results of the optimization, how the
             environment should be modified.
        """

        selected_next_legs, selected_routes = self.prepare_input(state)

        if len(selected_next_legs) > 0 and len(selected_routes) > 0:
            # The optimize method is called only if there is at least one leg
            # and one route to optimize.
            optimized_route_plans = self.optimize(selected_next_legs,
                                                  selected_routes,
                                                  state.current_time, state)

            optimization_result = self.process_optimized_route_plans(
                optimized_route_plans, state)
        else:
            optimization_result = optimization_module.OptimizationResult(state, [], [])

        return optimization_result

    def prepare_input(self, state: State) \
            -> Tuple[List['request.Leg'], List[Route]]:
        """Extract from the state the next legs and the routes that are sent as
        input to the optimize method (i.e. the legs and the routes that
        you want to optimize).

        By default, all next legs and all routes existing in the environment at
        the time of optimization will be optimized.

        This method can be overriden to return only the legs and the routes
        that should be optimized based on your needs (see, for example,
        ShuttleSimpleDispatcher).

        Input:
          -state: An object of type State that corresponds to a partial deep
           copy of the environment.

        Output:
          -selected_next_legs: A list of objects of type Trip that correspond
           to the trips (i.e., passengers or requests) that should be
           considered by the optimize method.
          -selected_routes: A list of objects of type Route that correspond
           to the routes associated with the vehicles (i.e., shuttles) that
           should be considered by the optimize method.

        Note that if selected_next_legs or selected_routes is empty, no
        optimization will be done.
           """

        # The next legs of all the trips
        selected_next_legs = state.next_legs

        # All the routes
        selected_routes = state.route_by_vehicle_id.values()

        return selected_next_legs, selected_routes

    def optimize(self, selected_next_legs: List['request.Leg'],
                 selected_routes: List[Route], current_time: int,
                 state: State) -> List['OptimizedRoutePlan']:
        """Determine the vehicle routing and the trip-route assignment
        according to an optimization algorithm. The optimization algorithm
        should be coded in this method.

        Must be overriden (see ShuttleSimpleDispatcher and
        ShuttleSimpleNetworkDispatcher for simple examples).

        Input:
          -selected_next_legs: List of the next legs to be optimized.
          -selected_routes: List of the routes to be optimized.
          -current_time: Integer equal to the current time of the State.
           The value of current_time is defined as follows:
              current_time = Environment.current_time
              + Optimization.freeze_interval.
           Environment.current_time: The time at which the Optimize event is
           processed.
           freeze_interval: 0, by default, see Optimization.freeze_interval
           for more details
          -state: An object of type State that corresponds to a partial deep
           copy of the environment.

        Output:
          -optimized_route_plans: List of the optimized route plans. Each route
           plan is an object of type OptimizedRoutePlan.
        """

        raise NotImplementedError('optimize of {} not implemented'.
                                  format(self.__class__.__name__))

    def process_optimized_route_plans(
            self, optimized_route_plans: List['OptimizedRoutePlan'],
            state: State) -> 'optimization_module.OptimizationResult':
        """Create and modify the simulation objects that correspond to the
        optimized route plans returned by the optimize method. In other words,
        this method "translates" the results of optimization into the
        "language" of the simulator.

        Input:
          -optimized_route_plans: List of objects of type OptimizedRoutePlan
           that correspond to the results of the optimization.
          -state: An object of type State that corresponds to a partial deep
           copy of the environment.
        Output:
          -optimization_result: An object of type OptimizationResult that
           consists essentially of a list of the modified trips, a list of
           the modified vehicles and a copy of the (possibly modified) state.
        """

        modified_trips = []
        modified_vehicles = []

        for route_plan in optimized_route_plans:
            self.__process_route_plan(route_plan)

            trips = [leg.trip for leg in route_plan.assigned_legs]

            modified_trips.extend(trips)
            modified_vehicles.append(route_plan.route.vehicle)

        optimization_result = optimization_module.OptimizationResult(
            state, modified_trips, modified_vehicles)

        return optimization_result

    def __process_route_plan(self, route_plan):

        self.__update_route_next_stops(route_plan)

        for leg in route_plan.already_onboard_legs:
            # Assign leg to route
            route_plan.route.assign_leg(leg)

            # Assign the trip associated with leg that was already on board
            # before optimization took place to the stops of the route
            self.__assign_already_onboard_trip_to_stop(leg, route_plan.route)

        for leg in route_plan.assigned_legs:
            # Assign leg to route
            route_plan.route.assign_leg(leg)

            # Assign the trip associated with leg to the stops of the route
            if leg not in route_plan.legs_manually_assigned_to_stops \
                    and leg not in route_plan.already_onboard_legs:
                self.__automatically_assign_trip_to_stops(leg,
                                                          route_plan.route)

    def __update_route_next_stops(self, route_plan):
        # Update current stop departure time
        if route_plan.route.current_stop is not None:
            route_plan.route.current_stop.departure_time = \
                route_plan.current_stop_departure_time

        route_plan.route.next_stops = route_plan.next_stops

        # Last stop departure time is set to infinity (since it is unknown).
        if route_plan.next_stops is not None \
                and len(route_plan.next_stops) > 0:
            route_plan.route.next_stops[-1].departure_time = math.inf

    def __automatically_assign_trip_to_stops(self, leg, route):

        boarding_stop_found = False
        alighting_stop_found = False

        if route.current_stop is not None:
            current_location = route.current_stop.location

            if leg.origin == current_location:
                self.__add_passenger_to_board(leg.trip, route.current_stop)
                boarding_stop_found = True

        for stop in route.next_stops:
            if leg.origin == stop.location and not boarding_stop_found:
                self.__add_passenger_to_board(leg.trip, stop)
                boarding_stop_found = True
            elif leg.destination == stop.location and boarding_stop_found \
                    and not alighting_stop_found:
                self.__add_passenger_to_alight(leg.trip, stop)
                alighting_stop_found = True

    def __assign_already_onboard_trip_to_stop(self, leg, route):

        for stop in route.next_stops:
            if leg.destination == stop.location:
                stop.passengers_to_alight.append(leg.trip)
                break

    def __add_passenger_to_board(self, trip, stop):
        trip_ids_list = [trip.id for trip in stop.passengers_to_board]
        if trip.id not in trip_ids_list:
            stop.passengers_to_board.append(trip)

    def __add_passenger_to_alight(self, trip, stop):
        trip_ids_list = [trip.id for trip in stop.passengers_to_alight]
        if trip.id not in trip_ids_list:
            stop.passengers_to_alight.append(trip)


class OptimizedRoutePlan:
    """Structure to store the optimization results of one route.

        Attributes:
            route: object of type Route
                The route that will be modified according to the route plan.
            current_stop_departure_time: int or float
                The planned departure time of the current stop of the route.
            next_stops: list of objects of type Stop
                The planned next stops of the route.
            assigned_legs: list of objects of type Leg.
                The legs planned to be assigned to the route.

        Remark:
            If the parameter next_stops of __init__ is None and no stop is
            appended through the append_next_stop method, then the original
            stops of the route will not be modified (see FixedLineDispatcher
            for an example).

    """

    def __init__(self, route: Route,
                 current_stop_departure_time: Optional[int] = None,
                 next_stops: Optional[List[Stop]] = None,
                 assigned_legs: Optional[List['request.Leg']] = None):
        """
        Parameters:
            route: object of type Route
                The route that will be modified according to the route plan.
            current_stop_departure_time: int, float or None
                The planned departure time of the current stop of the route.
            next_stops: list of objects of type Stop or None
                The planned next stops of the route.
            assigned_legs: list of objects of type Leg or None
                The legs planned to be assigned to the route.
        """

        self.__route = route
        self.__current_stop_departure_time = current_stop_departure_time
        self.__next_stops = next_stops if next_stops is not None else []
        self.__assigned_legs = assigned_legs if assigned_legs is not None \
            else []

        self.__already_onboard_legs = []

        self.__legs_manually_assigned_to_stops = []

    @property
    def route(self) -> Route:
        return self.__route

    @property
    def current_stop_departure_time(self) -> int:
        return self.__current_stop_departure_time

    @property
    def next_stops(self) -> List[Stop]:
        return self.__next_stops

    @property
    def assigned_legs(self) -> List['request.Leg']:
        return self.__assigned_legs

    @property
    def already_onboard_legs(self) -> List['request.Leg']:
        return self.__already_onboard_legs

    @property
    def legs_manually_assigned_to_stops(self) -> List['request.Leg']:
        return self.__legs_manually_assigned_to_stops

    def update_current_stop_departure_time(self, departure_time: int):
        """Modify the departure time of the current stop of the route plan
        (i.e., the stop at which the vehicle is at the time of optimization).
            Parameter:
                departure_time: int
                    New departure time of the current stop.
        """
        self.__current_stop_departure_time = departure_time

    def append_next_stop(self, stop_id: str | int, arrival_time: int,
                         departure_time: Optional[int] = None,
                         lon: Optional[float] = None,
                         lat: Optional[float] = None,
                         cumulative_distance: Optional[float] = None,
                         legs_to_board: Optional[List['request.Leg']] = None,
                         legs_to_alight: Optional[List['request.Leg']] = None)\
            -> List[Stop]:
        """Append a stop to the list of next stops of the route plan.
            Parameters:
                stop_id: string
                    Label of a stop location.
                arrival_time: int
                    Time at which the vehicle is planned to arrive at the stop.
                departure_time: int or None
                    Time at which the vehicle is panned to leave the stop.
                    If None, then departure_time is set equal to arrival_time.
                lon: float
                    Longitude of the stop. If None, then the stop has no
                    longitude.
                lat: float
                    Latitude of the stop. If None, then the stop has no
                    latitude.
                cumulative_distance: float
                    Cumulative distance that the vehicle will have travelled
                    when it arrives at the stop.
                legs_to_board: list of objects of type Leg or None
                    The legs that should be boarded at that stop. If None, then
                    the legs that are not explicitly assigned to a stop will
                    automatically be boarded at the first stop corresponding to
                    the origin location.
                legs_to_alight: list of objects of type Leg or None
                    The legs that should be alighted at that stop. If None,
                    then the legs that are not explicitly assigned to a stop
                    will automatically be alighted at the first stop
                    corresponding to the destination location.
        """
        if self.__next_stops is None:
            self.__next_stops = []

        if departure_time is None:
            departure_time = arrival_time

        stop = Stop(arrival_time, departure_time,
                    LabelLocation(stop_id, lon, lat),
                    cumulative_distance=cumulative_distance)

        if legs_to_board is not None:
            self.__assign_legs_to_board_to_stop(legs_to_board, stop)

        if legs_to_alight is not None:
            self.__assign_legs_to_alight_to_stop(legs_to_alight, stop)

        self.__next_stops.append(stop)

        return self.__next_stops

    def assign_leg(self, leg: 'request.Leg') -> List['request.Leg']:
        """Append a leg to the list of assigned legs of the route plan.
            Parameter:
                leg: object of type Leg
                    The leg to be assigned to the route.
        """

        leg.assigned_vehicle = self.route.vehicle

        if leg not in self.__assigned_legs:
            self.__assigned_legs.append(leg)

        return self.__assigned_legs

    def copy_route_stops(self):
        """Copy the current and next stops of the route to the current and
        next stops of OptimizedRoutePlan, respectively."""

        if self.route.current_stop is not None:
            self.__current_stop_departure_time = \
                self.route.current_stop.departure_time

        self.__next_stops = self.route.next_stops

    def assign_already_onboard_legs(self):
        """The legs that are on board will automatically be alighted at the
        first stop corresponding to the destination location."""
        self.__already_onboard_legs.extend(self.route.onboard_legs)

    def __assign_legs_to_board_to_stop(self, legs_to_board, stop):
        for leg in legs_to_board:
            stop.passengers_to_board.append(leg.trip)
            if leg not in self.__legs_manually_assigned_to_stops:
                self.__legs_manually_assigned_to_stops.append(leg)
                self.assign_leg(leg)

    def __assign_legs_to_alight_to_stop(self, legs_to_alight, stop):
        for leg in legs_to_alight:
            stop.passengers_to_alight.append(leg.trip)
            if leg not in self.__legs_manually_assigned_to_stops:
                self.__legs_manually_assigned_to_stops.append(leg)
                self.assign_leg(leg)
