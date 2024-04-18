import logging

from multimodalsim.optimization.optimization import OptimizationResult
from multimodalsim.optimization.dispatcher import OptimizedRoutePlan, \
    Dispatcher
import geopy.distance

logger = logging.getLogger(__name__)


class FixedLineDispatcher(Dispatcher):

    def __init__(self):
        super().__init__()

    def prepare_input(self, state):
        """Before optimizing, we extract the legs and the routes that we want
        to be considered by the optimization algorithm. For the
        FixedLineDispatcher, we want to keep only the legs that have not
        been assigned to any route yet.
        """

        # The next legs that have not been assigned to any route yet.
        selected_next_legs = state.non_assigned_next_legs

        # All the routes
        selected_routes = state.route_by_vehicle_id.values()

        return selected_next_legs, selected_routes

    def optimize(self, selected_next_legs, selected_routes, current_time,
                 state):
        """Each selected next leg is assigned to the optimal route. The optimal
        route is the one that has the earliest arrival time at destination
        (i.e. leg.destination)."""

        optimized_route_plans = []
        for leg in selected_next_legs:
            optimal_route = self.__find_optimal_route_for_leg(
                leg, selected_routes, current_time)

            if optimal_route is not None:
                optimized_route_plan = OptimizedRoutePlan(optimal_route)

                # Use the current and next stops of the route.
                optimized_route_plan.copy_route_stops()

                optimized_route_plan.assign_leg(leg)
                optimized_route_plans.append(optimized_route_plan)

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

    def bus_prepare_input(self, state):
        """Before optimizing, we extract the legs and the routes that we want
        to be considered by the optimization algorithm. For the
        FixedLineSynchroDispatcher, we want to keep only the legs that will cross the main line in
        the stops in the optimization horizon (assigned to the main line, onboard the main line, or potentially boarding the main line).
        Moreover, we keep the current route on the main line and the next route on the main line. 
        """
        main_line_id = state.main_line
        next_main_line_id = state.next_main_line

        # Main line route and next routes
        selected_routes = [route for route in state.route_by_vehicle_id.values() if route.vehicle.id == main_line_id or route.vehicle.id == next_main_line_id]
        # print("selected_routes: ", [route.vehicle.id for route in selected_routes])

        # Get the next ten stops on the main line
        main_line = state.route_by_vehicle_id[main_line_id]
        main_line_stops = main_line.next_stops[0:10]
        print('selected stops: ', main_line_stops)
        # The next legs assigned and onboard the selected routes
        selected_next_legs = [leg for route in selected_routes for leg in route.onboard_legs]
        selected_next_legs += [leg for route in selected_routes for leg in route.assigned_legs if leg.origin in [stop.location for stop in main_line_stops] or leg.destination in [stop.location for stop in main_line_stops]]
        
        # Get trips associated with the selected legs
        selected_trips = [leg.trip for leg in selected_next_legs]
        print('selected_trips: ', len(selected_trips))
        for trip in selected_trips:
            print("trip: ", trip.id)
            print('Previous legs: ', len(trip.previous_legs),'Previous legs assigned vehicles: ', [leg.cap_vehicle_id for leg in trip.previous_legs if leg != None])
            print('Current leg vehicle: ', trip.current_leg.cap_vehicle_id if trip.current_leg != None else None, ' type', type(trip.current_leg.cap_vehicle_id if trip.current_leg != None else None))
            print('Next legs: ', len(trip.next_legs),' Next legs assigned vehicles: ', [leg.cap_vehicle_id for leg in trip.next_legs if leg != None], 'types: ', [type(leg.cap_vehicle_id) for leg in trip.next_legs if leg != None])
        for trip in selected_trips:
            route=None
            second_next_route=None
            if trip.current_leg is not None: #Onboard legs
                current_vehicle_id=trip.current_leg.assigned_vehicle.id if trip.current_leg.assigned_vehicle != None else trip.current_leg.cap_vehicle_id
                if current_vehicle_id == main_line_id: #passenger on board main line, check if transfer to other lines
                    print('ligne 139 on est la')
                    print('current leg destination: ', trip.current_leg.destination)
                    if len(trip.next_legs)>0 and trip.current_leg.destination in [stop.location for stop in main_line_stops]: #transfer to other line in the horizon
                        print('ligne 142 add transfer main-> feeder')
                        next_leg = trip.next_legs[0]
                        next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                        route = get_route_by_vehicle_id(state, next_vehicle_id)
                    # else: #No transfer to other lines, no route_id to add.
                    #if passenger transferred from another bus to main line, it is already done so we don't need the info
                else: #passenger on board other line, transfer to main line
                    if len(trip.next_legs)>0:
                        print('ligne 147 passenger has next legs')
                        next_leg = trip.next_legs[0]
                        next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                        previous_vehicle_id = current_vehicle_id
                        i=0
                        while next_vehicle_id != main_line_id and i<len(trip.next_legs)-1: #find the next leg that is on the main line
                            previous_vehicle_id = next_vehicle_id
                            i+=1
                            next_leg = trip.next_legs[i]
                            next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                        if next_vehicle_id == main_line_id and next_leg.origin in [stop.location for stop in main_line_stops]: #passenger boards main line bus in the horizon
                            print('ligne 161, transfer feeder -> main')
                            route = get_route_by_vehicle_id(state, previous_vehicle_id)
                        if i < len(trip.next_legs)-1 and next_leg.destination in [stop.location for stop in main_line_stops]: #passenger also transfers to another bus in the horizon
                            print('ligne 164 transfer feeder->main->feeder')
                            second_next_leg = trip.next_legs[i+1]
                            second_next_vehicle_id = second_next_leg.assigned_vehicle.id if second_next_leg.assigned_vehicle != None else second_next_leg.cap_vehicle_id
                            second_next_route = get_route_by_vehicle_id(state,second_next_vehicle_id)
            else: #Assigned legs, not on any bus. Passenger either hasn't started trip or is transferring. 
                if len(trip.previous_legs)>0: #passenger transferring
                    previous_leg = trip.previous_legs[-1]
                    previous_vehicle_id = previous_leg.assigned_vehicle.id if previous_leg.assigned_vehicle != None else previous_leg.cap_vehicle_id
                    if len(trip.next_legs)>0:
                        next_leg = trip.next_legs[0]
                        next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                        if previous_vehicle_id == main_line_id and previous_leg.destination in [stop.location for stop in main_line_stops]: #passenger transferred from main line and is going to other line
                            route = get_route_by_vehicle_id(state, next_vehicle_id)
                            input('ligne 177 transfer main-> feeder we should never be here')
                        else: #passenger transferred from other line and is going to main line
                            i=0
                            while next_vehicle_id != main_line_id and i<len(trip.next_legs)-1: #find the next leg that is on the main line
                                previous_vehicle_id = next_vehicle_id
                                i+=1
                                next_leg = trip.next_legs[i]
                                next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                            if next_vehicle_id == main_line_id and next_leg.origin in [stop.location for stop in main_line_stops]:
                                print('ligne 186 transfer feeder->main')
                                route = get_route_by_vehicle_id(state, previous_vehicle_id)
                            if i < len(trip.next_legs)-1 and next_leg.destination in [stop.location for stop in main_line_stops]:
                                print('ligne 189 transfer feeder->main->feeder ')
                                second_next_leg = trip.next_legs[i+1]
                                second_next_vehicle_id = second_next_leg.assigned_vehicle.id if second_next_leg.assigned_vehicle != None else second_next_leg.cap_vehicle_id
                                second_next_route = get_route_by_vehicle_id(state, second_next_vehicle_id)
                elif len(trip.next_legs)>0: #Passenger starting their trip
                    print('on est la ligne 194')
                    next_leg = trip.next_legs[0]
                    next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                    previous_vehicle_id = next_vehicle_id
                    i=0
                    while next_vehicle_id != main_line_id and i<len(trip.next_legs)-1: #find the next leg that is on the main line
                        print('on rentre dans la boucle ligne 199')
                        previous_vehicle_id = next_vehicle_id
                        i+=1
                        next_leg = trip.next_legs[i]
                        next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                    if next_vehicle_id == main_line_id and previous_vehicle_id != main_line_id and next_leg.origin in [stop.location for stop in main_line_stops]:
                        print('ligne 201 tranfser feeder->main')
                        route = get_route_by_vehicle_id(state, previous_vehicle_id)
                    if i < len(trip.next_legs)-1 and next_leg.destination in [stop.location for stop in main_line_stops]:
                        print('ligne 204 tranfser feeder->main->feeder')
                        second_next_leg = trip.next_legs[i+1]
                        second_next_vehicle_id = second_next_leg.assigned_vehicle.id if second_next_leg.assigned_vehicle != None else second_next_leg.cap_vehicle_id
                        print('next vehicle id', second_next_vehicle_id, 'route by vehicle id dict', [route.vehicle.id for route in state.route_by_vehicle_id.values()])
                        second_next_route = get_route_by_vehicle_id(state, second_next_vehicle_id)
            if route is not None:
                selected_routes.append(route)
            if second_next_route is not None:
                selected_routes.append(second_next_route)            
        if len(selected_trips)>0:
            print('selected routes: ', [route.vehicle.id for route in selected_routes])
            # input('Press enter to continue...')
        return selected_next_legs, selected_routes
    
    def bus_optimize(self, selected_next_legs, selected_routes, current_time,
                 state):
        """Each selected next leg is assigned to the optimal route. The optimal
        route is the one that has the earliest arrival time at destination
        (i.e. leg.destination)."""

        optimized_route_plans = []
        for leg in selected_next_legs:
            optimal_route = self.__find_optimal_route_for_leg(
                leg, selected_routes, current_time)

            if optimal_route is not None:
                optimized_route_plan = OptimizedRoutePlan(optimal_route)

                # Use the current and next stops of the route.
                optimized_route_plan.copy_route_stops()

                optimized_route_plan.assign_leg(leg)
                optimized_route_plans.append(optimized_route_plan)

        return optimized_route_plans

    def bus_dispatch(self, state, bus=False):
        """Decide tactics to use on main line after every departure from a bus stop.
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

        selected_next_legs, selected_routes = self.bus_prepare_input(state)
        
        ### OSO algorithm
        sp, ss, hp, ht_and_time = OSO_algorithm(selected_next_legs, selected_routes, state)
        main_line_id = state.main_line
        main_route = get_route_by_vehicle_id(state, main_line_id)
        if ss: # add a 'walking' vehicle from the following stop to the skipped stop
            time=get_walk_time(main_route)
        # Update the main line route based on the OSO algorithm results.
        main_route = update_main_line(self, main_route, sp, ss, hp, ht_and_time)
        # Update the route in the state
        state.route_by_vehicle_id[main_line_id] = main_route

        
        ### Process OSO algorithm results and assign passengers to buses
        if len(selected_next_legs) > 0 or len(selected_routes) > 0:
            # The optimize method is called only if there is at least one leg
            # or one route to optimize.
            optimized_route_plans = self.bus_optimize(selected_next_legs,
                                                    selected_routes,
                                                    state.current_time, state)

            optimization_result = self.process_optimized_route_plans(
                optimized_route_plans, state)
        else:
            optimization_result = OptimizationResult(state, [], [])

        return optimization_result

def get_route_by_vehicle_id(state, vehicle_id):
    """Get the route object corresponding to the vehicle_id."""
    route = next(iter([route for route in state.route_by_vehicle_id.values() if route.vehicle.id == vehicle_id]), None)
    return route

def OSO_algorithm(selected_next_legs, selected_routes, state):
    """Online stochastic optimization algorithm for the bus dispatcher.
    Inputs:
        - selected_next_legs: list, the next legs that are assigned to the main line or onboard the main line.
        - selected_routes: list, current and next routes on the main line as well as connecting bus lines.
        - state: State object, the current state of the environment.
    
    Outputs:
        - sp: boolean, the result of the OSO algorithm for the speedup tactic.
        - ss: boolean, the result of the OSO algorithm for the skip-stop tactic.
        - h_and_time: tuple, the result of the OSO algorithm for the hold tactic the corresponding end of hold time (hold for planned time or transfer, the output hold time is already treated in the OSO algorithm)"""
    
    main_route = get_route_by_vehicle_id(state, state.main_line)

    if (main_route is None) or (main_route.current_stop is not None):
        return(False, False, (False, -1))
    
    sp = False
    ss = False
    h_and_time = (False, -1)
    return sp, ss, h_and_time

def update_main_line(self, route, sp, ss, h_and_time):
    """Update the main line route based on the OSO algorithm results.
    Inputs: 
        - route: Route object, the main line route.
        - sp: boolean, the result of the OSO algorithm for the speedup tactic.
        - ss: boolean, the result of the OSO algorithm for the skip-stop tactic.
        - h_and_time: boolean, the result of the OSO algorithm for the hold tactic if we hold for the planned arrival time and the corresponding end of hold time

    Outputs:
        - updated_route: Route object, the updated main line route.
    """
    h = h_and_time[0]
    planned_arrival_time = route.next_stops[0].arrival_time
    planned_departure_time = route.next_stops[0].departure_time
    dwell_time = max(0, planned_departure_time - planned_arrival_time)

    if route.current_stop is not None: # bus departing from depot (vehicle ready event.)
        return route
    else: 
        prev_departure_time = route.previous_stops[-1].departure_time ### since the bus just departed form stop
    
    # Find the arrival time at the next stop
    if sp:
        travel_time = int((planned_arrival_time - prev_departure_time)*self.__speedup_factor)
    else: #also true for ss = True
        travel_time = planned_arrival_time - prev_departure_time
    arrival_time = prev_departure_time + travel_time

    # Find the departure time at the next stop
    if ss:
        dwell_time = 0
    elif h: # wait for planned departure time)
        dwell_time = max(h_and_time[1] - arrival_time, dwell_time)
    departure_time = arrival_time + dwell_time

    # Update the arrival and departure times of the next stop
    next_stop = route.next_stops[0]
    next_stop.arrival_time = arrival_time
    next_stop.departure_time = departure_time

    # Update the arrival and departure times of the following stops
    delta_time = departure_time - planned_departure_time

    for stop in route.next_stops[1:]:
        stop.arrival_time += delta_time
        if stop.min_departure_time is None:
            new_departure_time = stop.departure_time + delta_time
        else:
            new_departure_time = max(stop.departure_time + delta_time,
                                        stop.min_departure_time)
        delta_time = new_departure_time - stop.departure_time
        stop.departure_time = new_departure_time
    if ss: 
        route.next_stops = route.next_stops[1:]
    return route

def get_walk_time(main_route):
    if len(main_route.next_stops)>1:
        second_next_stop = main_route.next_stops[1].location
    else: 
        second_next_stop = None
    if len(main_route.previous_stops)>0: 
        previous_stop = main_route.previous_stops[-1].location
    else: 
        previous_stop = None
    # get skipped stop location 
    next_stop = main_route.next_stops[0].location
    coordinates_skipped = (next_stop.lat, next_stop.lon)
    #get distance between skipped stop and following stop
    if second_next_stop != None:
        second_next_location = second_next_stop.location
        coordinates_next= (second_next_location.lat, second_next_location.lon)
        next_distance = geopy.distance.geodesic(coordinates_skipped, coordinates_next).km
    else:
        next_distance = 1000000000
    if previous_stop != None:
        previous_location = previous_stop.location
        coordinates_previous= (previous_location.lat, previous_location.lon)
        previous_distance = geopy.distance.geodesic(coordinates_skipped, coordinates_previous).km
    else:   
        previous_distance = 1000000000
    distance = min(next_distance, previous_distance)
    print('distance: ', distance)
    # we assume someones walks with a speed of 4km per hour
    time = distance/4*3600 #time in seconds
    return time