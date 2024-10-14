import logging
import math

from multimodalsim.optimization.optimization import OptimizationResult
from multimodalsim.simulator.vehicle import Stop, LabelLocation

logger = logging.getLogger(__name__)

class Dispatcher:

    def __init__(self):
        super().__init__()

    def dispatch(self, state):
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
           should be considered by the optimize method.

        Note that if selected_next_legs or selected_routes is empty, no
        optimization will be done.
           """

        # The next legs of all the trips
        selected_next_legs = state.next_legs

        # All the routes
        selected_routes = state.route_by_vehicle_id.values()

        return selected_next_legs, selected_routes
    
    def bus_prepare_input(self, state):
        raise NotImplementedError('optimize of {} not implemented'.
                                  format(self.__class__.__name__))
    
    def bus_optimize(self, selected_next_legs, selected_routes, current_time,
                    state):
        raise NotImplementedError('optimize of {} not implemented'.
                                  format(self.__class__.__name__))
    
    def optimize(self, selected_next_legs, selected_routes, current_time,
                 state):
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

    def bus_dispatch(self, state, queue, main_line_id, next_main_line_id):
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

            trips = [leg.trip for leg in route_plan.assigned_legs + route_plan.already_onboard_legs + route_plan.legs_to_remove]
            # print('Modified trips for Optimizations')
            # for trip in route_plan.assigned_legs:
            #     print('Trip ID: ', trip.id, 'is ASSIGNED to vehicle: ', route_plan.route.vehicle.id, 'in Optimizations')
            # for trip in route_plan.already_onboard_legs:
            #     print('Trip ID: ', trip.id, 'is ALREADY ON BOARD on vehicle: ', route_plan.route.vehicle.id, 'in Optimizations')
            # for trip in route_plan.legs_to_remove:
            #     print('Trip ID: ', trip.id, 'is to be REMOVED from vehicle: ', route_plan.route.vehicle.id, 'in Optimizations')
            modified_trips.extend(trips)
            modified_vehicles.append(route_plan.route.vehicle)

        optimization_result = OptimizationResult(state, modified_trips,
                                                 modified_vehicles)

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
        
        for leg in route_plan.legs_to_remove:
            # Remove leg from route : on en a besoin pour que ce soit update dans le environment
            # Fait dans VehicleNotification.process
            # route_plan.route.unassign_leg(leg)

            # Remove the trip associated with leg from the stops of the route
            if leg not in route_plan.already_onboard_legs:
                self.__remove_trip_from_stops(leg, route_plan.route)


    def __update_route_next_stops(self, route_plan):
        # Update current stop departure time
        if route_plan.route.current_stop is not None:
            route_plan.route.current_stop.departure_time = \
                route_plan.current_stop_departure_time

        route_plan.route.next_stops = route_plan.next_stops

        # # Last stop departure time is set to infinity (since it is unknown).
        # # Never do this for GTFS data.
        # if route_plan.next_stops is not None \
        #         and len(route_plan.next_stops) > 0:
        #     route_plan.route.next_stops[-1].departure_time = math.inf

    def __automatically_assign_trip_to_stops(self, leg, route):

        boarding_stop_found = False
        alighting_stop_found = False
        boarding_stop = None
        alighting_stop = None

        if route.current_stop is not None:
            current_location = route.current_stop.location

            if leg.origin == current_location:
                # self.__add_passenger_to_board(leg.trip, route.current_stop)
                boarding_stop_found = True
                boarding_stop = route.current_stop

        for stop in route.next_stops:
            if leg.origin == stop.location and not boarding_stop_found:
                # self.__add_passenger_to_board(leg.trip, stop)
                boarding_stop_found = True
                boarding_stop = stop
            elif leg.destination == stop.location and boarding_stop_found \
                    and not alighting_stop_found:
                # self.__add_passenger_to_alight(leg.trip, stop)
                alighting_stop_found = True
                alighting_stop = stop
        if not (boarding_stop_found and alighting_stop_found):
            logger.warning("Trip {} could not be assigned to stops of route {}.".format(leg.trip.id, route.vehicle.id))
        else:
            self.__add_passenger_to_board(leg.trip, boarding_stop)
            self.__add_passenger_to_alight(leg.trip, alighting_stop)

    def __remove_trip_from_stops(self, leg, route):
        """Remove the trip associated with leg from the stops of the route.
           The trip origin has already been removed from the stops of the route.
           We only need to find the trip destination and remove the alighting passenger.
           Input:
               -leg: object of type Leg: The leg to be removed from the alighting passengers from the destination stops of the route.
               -route: object of type Route: The route from which the trip should be removed from the stops.
        """
        alighting_stop_found = False

        if route.current_stop is not None:
            current_location = route.current_stop.location

            if leg.destination == current_location:
                self.__remove_passenger_to_alight(leg.trip, route.current_stop)
                alighting_stop_found = True
                input('We should never be here...')
        for stop in route.next_stops:
            if leg.destination == stop.location and not alighting_stop_found:
                self.__remove_passenger_to_alight(leg.trip, stop)
                alighting_stop_found = True
        if not alighting_stop_found:
            logger.warning("Trip {} could not be removed from stops of route {}."
                           .format(leg.trip.id, route.vehicle.id))

    def __assign_already_onboard_trip_to_stop(self, leg, route):
        ### Passenger does not alight at current stop, he would already have alighted before the opt.
        for stop in route.next_stops:
            if leg.destination == stop.location:
                stop.passengers_to_alight.append(leg.trip)
                stop.passengers_to_alight_int += 1
                break

    def __add_passenger_to_board(self, trip, stop):
        # print('on est la, on ajoute le passenger_to_board ', trip.id,' au stop: ', stop.location.label)
        trip_ids_list = [trip.id for trip in stop.passengers_to_board]
        if trip.id not in trip_ids_list:
            stop.passengers_to_board.append(trip)
            stop.passengers_to_board_int +=1

    def __add_passenger_to_alight(self, trip, stop):
        # print('on est la, on ajoute le passenger_to_alight ', trip.id,' au stop: ', stop.location.label)
        trip_ids_list = [trip.id for trip in stop.passengers_to_alight]
        if trip.id not in trip_ids_list:
            stop.passengers_to_alight.append(trip)
            stop.passengers_to_alight_int = stop.passengers_to_alight_int + 1

    def __remove_passenger_to_board(self, trip, stop):
        trip_ids_list = [trip.id for trip in stop.passengers_to_board]
        if trip.id in trip_ids_list:
            stop.passengers_to_board.remove(trip)
            stop.passengers_to_board_int = max( 0, stop.passengers_to_board_int - 1)
    
    def __remove_passenger_to_alight(self, trip, stop):
        trip_ids_list = [trip.id for trip in stop.passengers_to_alight]
        if trip.id in trip_ids_list:
            stop.passengers_to_alight.remove(trip)
            stop.passengers_to_alight_int = max( 0, stop.passengers_to_alight_int - 1)

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

        self.__already_onboard_legs = []

        self.__legs_manually_assigned_to_stops = []

        self.__legs_to_remove = []

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

    @property
    def already_onboard_legs(self):
        return self.__already_onboard_legs

    @property
    def legs_manually_assigned_to_stops(self):
        return self.__legs_manually_assigned_to_stops

    @property
    def legs_to_remove(self):
        return self.__legs_to_remove
    
    def add_leg_to_remove(self, leg):
        self.__legs_to_remove.append(leg)
    
    def update_current_stop_departure_time(self, departure_time):
        """Modify the departure time of the current stop of the route plan
        (i.e., the stop at which the vehicle is at the time of optimization).
            Parameter:
                departure_time: int
                    New departure time of the current stop.
        """
        self.__current_stop_departure_time = departure_time

    def append_next_stop(self, stop_id, arrival_time, departure_time=None,
                         lon=None, lat=None, cumulative_distance=None,
                         legs_to_board=None, legs_to_alight=None):
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

    def unassign_leg(self, leg):
        """Remove a leg from the list of assigned legs of the route plan.
            Parameter:
                leg: object of type Leg
                    The leg to be removed from the list of assigned legs of the
                    route plan.
        """
        if leg.assigned_vehicle is not None and leg.assigned_vehicle == self.route.vehicle:
            leg.assigned_vehicle = None

        if leg in self.__assigned_legs:
            self.__assigned_legs.remove(leg)

        return self.__assigned_legs
    
    def assign_leg(self, leg):
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
    
    def add_already_onboard_legs(self, leg):
        """The legs that are on board will automatically be alighted at the
        first stop corresponding to the destination location."""
        self.__already_onboard_legs.append(leg)

    def __assign_legs_to_board_to_stop(self, legs_to_board, stop):
        for leg in legs_to_board:
            stop.passengers_to_board.append(leg.trip)
            stop.passengers_to_board_int += 1
            if leg not in self.__legs_manually_assigned_to_stops:
                self.__legs_manually_assigned_to_stops.append(leg)
                self.assign_leg(leg)

    def __assign_legs_to_alight_to_stop(self, legs_to_alight, stop):
        for leg in legs_to_alight:
            stop.passengers_to_alight.append(leg.trip)
            stop.passengers_to_alight_int += 1
            if leg not in self.__legs_manually_assigned_to_stops:
                self.__legs_manually_assigned_to_stops.append(leg)
                self.assign_leg(leg)
