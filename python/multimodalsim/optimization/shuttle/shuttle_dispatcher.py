import logging
import math

from multimodalsim.optimization.optimization import OptimizationResult
from multimodalsim.simulator.vehicle import Stop, LabelLocation

logger = logging.getLogger(__name__)


class Dispatcher(object):

    def __init__(self):
        pass

    def dispatch(self, state):
        raise NotImplementedError('dispatch not implemented')


class ShuttleDispatcher(Dispatcher):

    def __init__(self):
        super().__init__()

    def dispatch(self, state):
        """Optimize the vehicle routing and the trip-route assignment for the
        shuttles. This method relies on three other methods:
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
            optimization_result = OptimizationResult(state, [], [])

        return optimization_result

    def prepare_input(self, state):
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
           should be considered by the optimize method."""

        # The next legs of all the trips
        selected_next_legs = state.next_legs

        # All the routes
        selected_routes = state.route_by_vehicle_id.values()

        return selected_next_legs, selected_routes

    def optimize(self, selected_next_legs, selected_routes, current_time,
                 state):
        """Determine the vehicle routing and the trip-route assignment
        according to an optimization algorithm. The optimization algorithm
        should be coded in this method.

        Must be overriden (see ShuttleSimpleDispatcher and
        ShuttleSimpleNetworkDispatcher for simple examples).

        Input:
          -selected_next_legs: List of the next legs to be optimized.
          -routes: List of the routes to be optimized.
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

    def process_optimized_route_plans(self, optimized_route_plans, state):
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

        optimization_result = OptimizationResult(state, modified_trips,
                                                 modified_vehicles)

        return optimization_result

    def __process_route_plan(self, route_plan):

        self.__update_route_next_stops(route_plan)

        for leg in route_plan.assigned_legs:
            # Assign legs to route
            route_plan.route.assign_leg(leg)

            # Assign trip to the stops of the route
            self.__assign_trip_to_stops(leg.trip, route_plan.route)

    def __update_route_next_stops(self, route_plan):
        # Update current stop departure time
        if route_plan.route.current_stop is not None:
            route_plan.route.current_stop.departure_time = \
                route_plan.current_stop_departure_time

        route_plan.route.next_stops = route_plan.next_stops

        # Last stop departure time is set to infinity (since it is unknown).
        if len(route_plan.route.next_stops) > 0:
            route_plan.route.next_stops[-1].departure_time = math.inf

    def __assign_trip_to_stops(self, trip, route):
        boarding_stop_found = False
        alighting_stop_found = False

        if route.current_stop is not None:
            current_location = route.current_stop.location

            if trip.origin == current_location:
                route.current_stop.passengers_to_board.append(trip)
                boarding_stop_found = True

        for stop in route.next_stops:
            if trip.origin == stop.location and not boarding_stop_found:
                stop.passengers_to_board.append(trip)
                boarding_stop_found = True
            elif trip.destination == stop.location and boarding_stop_found \
                    and not alighting_stop_found:
                stop.passengers_to_alight.append(trip)
                alighting_stop_found = True


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
    """

    def __init__(self, route, current_stop_departure_time=None,
                 next_stops=None, assigned_legs=None):
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

    @property
    def route(self):
        return self.__route

    @property
    def current_stop_departure_time(self):
        return self.__current_stop_departure_time

    @property
    def next_stops(self):
        return self.__next_stops

    @property
    def assigned_legs(self):
        return self.__assigned_legs

    def update_current_stop_departure_time(self, departure_time):
        """Modify the departure time of the current stop of the route plan
        (i.e., the stop at which the vehicle is at the time of optimization).
            Parameter:
                departure_time: int
                    New departure time of the current stop.
        """
        self.__current_stop_departure_time = departure_time

    def append_next_stop(self, stop_id, arrival_time, departure_time=None):
        """Append a stop to the list of next stops of the route plan.
            Parameters:
                stop_id: string
                    Label of a stop location.
                arrival_time: int
                    Time at which the vehicle is planned to arrive at the stop.
                departure_time: int or None
                    Time at which the vehicle is panned to leave the stop.
                    If None, then departure_time is set equal to arrival_time.
        """

        if departure_time is None:
            departure_time = arrival_time

        stop = Stop(arrival_time, departure_time, LabelLocation(stop_id))

        self.__next_stops.append(stop)

        return self.__next_stops

    def assign_leg(self, leg):
        """Append a leg to the list of assigned legs of the route plan.
            Parameter:
                leg: object of type Leg
                    The leg to be assigned to the route.
        """

        leg.assigned_vehicle = self.route.vehicle

        self.__assigned_legs.append(leg)

        return self.__assigned_legs


