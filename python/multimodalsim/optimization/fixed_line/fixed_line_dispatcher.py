import logging

from multimodalsim.optimization.optimization import OptimizationResult
from multimodalsim.optimization.dispatcher import OptimizedRoutePlan, Dispatcher
from multimodalsim.config.fixed_line_dispatcher_config import FixedLineDispatcherConfig
from multimodalsim.simulator.vehicle import Vehicle, Route, LabelLocation
from multimodalsim.simulator.vehicle_event import VehicleReady
from multimodalsim.simulator.request import Leg

import geopy.distance
import random 
import copy
from operator import itemgetter
import time
import os
import numpy as np
import multiprocessing
logger = logging.getLogger(__name__)

class FixedLineDispatcher(Dispatcher):

    def __init__(self, config=None, ss=False, sp=False, algo=0):
        super().__init__()
        self.__config = FixedLineDispatcherConfig() if config is None else config
        self.__algo = algo
        self.__general_parameters = self.__config.get_general_parameters
        self.__speedup_factor = self.__config.get_speedup_factor(sp)
        self.__skip_stop = self.__config.get_skip_stop(ss)
        self.__horizon = self.__config.get_horizon(ss, sp)
        self.__algo_parameters = self.__config.get_algo_parameters(algo)
        self.__walking_vehicle_counter = 0
        self.__CAPACITY = 80

    @property
    def speedup_factor(self):
        return self.__speedup_factor
    
    @property
    def walking_speed(self):
        return self.__general_parameters["walking_speed"]
    
    @property
    def skip_stop(self):
        return self.__skip_stop
    
    @property
    def general_parameters(self):
        return self.__general_parameters
    
    @property
    def algo_parameters(self):
        return self.__algo_parameters
    
    @property
    def folder_name_addendum(self):
        return self.__algo_parameters["folder_name_addendum"]
    
    @property
    def horizon(self):
        return self.__horizon
    
    def prepare_input(self, state):
        """Before optimizing, we extract the legs and the routes that we want
        to be considered by the optimization algorithm. For the
        FixedLineDispatcher, we want to keep only the legs that have not
        been assigned to any route yet.
        """
        logger.info('STARTING NORMAL OPTIMIZE...')
        # The next legs that have not been assigned to any route yet.
        selected_next_legs = state.non_assigned_next_legs

        # All the routes
        selected_routes = state.route_by_vehicle_id.values()
        # for route in selected_routes:
        #     if 'walk' in route.vehicle.id:
        #         input('walk route found and is going to be optimized...')

        return selected_next_legs, selected_routes

    def optimize(self, selected_next_legs, selected_routes, current_time,
                 state):
        """Each selected next leg is assigned to the optimal route. The optimal
        route is the one that has the earliest arrival time at destination
        (i.e. leg.destination)."""
        optimized_route_plans = []
        for leg in selected_next_legs:
            # print('leg:', leg.id, 'origin:', leg.origin.label, 'destination:', leg.destination.label)
            optimal_route = self.__find_optimal_route_for_leg(
                leg, selected_routes, current_time)

            if optimal_route is not None:
                # print('optimal route:', optimal_route.vehicle.id, 'current stop:', optimal_route.current_stop.location.label if optimal_route.current_stop is not None else None)
                # if 'walk' in optimal_route.vehicle.id:
                #     input('optimal walk vehicle found...')
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
        # print('leg:', leg.id,'origin',leg.origin.label,'destination',leg.destination.label, 'origin departure time: ', origin_departure_time, 'destination arrival time: ', destination_arrival_time,'optimal route:', optimal_route.vehicle.id if optimal_route is not None else None)
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

    def bus_prepare_input(self, state, main_line_id = None, next_main_line_id = None):
        """Before optimizing, we extract the legs and the routes that we want
        to be considered by the optimization algorithm. For the
        FixedLineSynchroDispatcher, we want to keep only the legs that will cross the main line in
        the stops in the optimization horizon (assigned to the main line, onboard the main line, or potentially boarding the main line).
        Moreover, we keep the current route on the main line and the next route on the main line. 
        """
        logger.info('STARTING BUS OPTIMIZE...')
        state.main_line = main_line_id
        state.next_main_line = next_main_line_id

        # Get the selected routes
        selected_routes = [route for route in state.route_by_vehicle_id.values() if route.vehicle.id == main_line_id or route.vehicle.id == next_main_line_id]


        # Get the next stops in the horizon on the main line
        main_line = state.route_by_vehicle_id[main_line_id]
        main_line_stops = main_line.next_stops[0:self.horizon]
        
        # The next legs assigned and onboard the selected routes
        selected_next_legs = [leg for route in selected_routes for leg in route.onboard_legs]
        selected_next_legs += [leg for route in selected_routes for leg in route.assigned_legs if leg.origin in [stop.location for stop in main_line_stops] or leg.destination in [stop.location for stop in main_line_stops]]
        
        # Get trips associated with the selected legs
        selected_trips = [leg.trip for leg in selected_next_legs]
        print('selected_trips: ', len(selected_trips))
        for trip in selected_trips:
            route=None
            second_next_route=None
            if trip.current_leg is not None: #Onboard legs
                current_vehicle_id=trip.current_leg.assigned_vehicle.id if trip.current_leg.assigned_vehicle != None else trip.current_leg.cap_vehicle_id
                if current_vehicle_id == main_line_id: #passenger on board main line, check if transfer to other lines
                    # print('ligne 139 on est la')
                    # print('current leg destination: ', trip.current_leg.destination)
                    if len(trip.next_legs)>0 and trip.current_leg.destination in [stop.location for stop in main_line_stops]: #transfer to other line in the horizon
                        # print('ligne 142 add transfer main-> feeder')
                        next_leg = trip.next_legs[0]
                        next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                        route = self.get_route_by_vehicle_id(state, next_vehicle_id)
                    # else: #No transfer to other lines, no route_id to add.
                    #if passenger transferred from another bus to main line, it is already done so we don't need the info
                else: #passenger on board other line, transfer to main line
                    if len(trip.next_legs)>0:
                        # print('passenger has next legs')
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
                            # print('transfer feeder -> main')
                            route = self.get_route_by_vehicle_id(state, previous_vehicle_id)
                        if i < len(trip.next_legs)-1 and next_leg.destination in [stop.location for stop in main_line_stops]: #passenger also transfers to another bus in the horizon
                            # print('transfer feeder->main->feeder')
                            second_next_leg = trip.next_legs[i+1]
                            second_next_vehicle_id = second_next_leg.assigned_vehicle.id if second_next_leg.assigned_vehicle != None else second_next_leg.cap_vehicle_id
                            second_next_route = self.get_route_by_vehicle_id(state,second_next_vehicle_id)
            else: #Assigned legs, not on any bus. Passenger either hasn't started trip or is transferring. 
                if len(trip.previous_legs)>0: #passenger transferring
                    previous_leg = trip.previous_legs[-1]
                    previous_vehicle_id = previous_leg.assigned_vehicle.id if previous_leg.assigned_vehicle != None else previous_leg.cap_vehicle_id
                    if len(trip.next_legs)>0:
                        next_leg = trip.next_legs[0]
                        next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                        if previous_vehicle_id == main_line_id and previous_leg.destination in [stop.location for stop in main_line_stops]: #passenger transferred from main line and is going to other line
                            route = self.get_route_by_vehicle_id(state, next_vehicle_id)
                            input('transfer main-> feeder we should never be here')
                        else: #passenger transferred from other line and is going to main line
                            i=0
                            while next_vehicle_id != main_line_id and i<len(trip.next_legs)-1: #find the next leg that is on the main line
                                previous_vehicle_id = next_vehicle_id
                                i+=1
                                next_leg = trip.next_legs[i]
                                next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                            if next_vehicle_id == main_line_id and next_leg.origin in [stop.location for stop in main_line_stops]:
                                # print('transfer feeder->main')
                                route = self.get_route_by_vehicle_id(state, previous_vehicle_id)
                            if i < len(trip.next_legs)-1 and next_leg.destination in [stop.location for stop in main_line_stops]:
                                # print('transfer feeder->main->feeder ')
                                second_next_leg = trip.next_legs[i+1]
                                second_next_vehicle_id = second_next_leg.assigned_vehicle.id if second_next_leg.assigned_vehicle != None else second_next_leg.cap_vehicle_id
                                second_next_route = self.get_route_by_vehicle_id(state, second_next_vehicle_id)
                elif len(trip.next_legs)>0: #Passenger starting their trip
                    next_leg = trip.next_legs[0]
                    next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                    previous_vehicle_id = next_vehicle_id
                    i=0
                    while next_vehicle_id != main_line_id and i<len(trip.next_legs)-1: #find the next leg that is on the main line
                        previous_vehicle_id = next_vehicle_id
                        i+=1
                        next_leg = trip.next_legs[i]
                        next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                    if next_vehicle_id == main_line_id and previous_vehicle_id != main_line_id and next_leg.origin in [stop.location for stop in main_line_stops]:
                        # print('tranfser feeder->main')
                        route = self.get_route_by_vehicle_id(state, previous_vehicle_id)
                    if i < len(trip.next_legs)-1 and next_leg.destination in [stop.location for stop in main_line_stops]:
                        # print('tranfser feeder->main->feeder')
                        second_next_leg = trip.next_legs[i+1]
                        second_next_vehicle_id = second_next_leg.assigned_vehicle.id if second_next_leg.assigned_vehicle != None else second_next_leg.cap_vehicle_id
                        second_next_route = self.get_route_by_vehicle_id(state, second_next_vehicle_id)
            if route is not None:
                selected_routes.append(route)
            if second_next_route is not None:
                selected_routes.append(second_next_route)            
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

    def bus_dispatch(self, state, queue=None, main_line_id=None, next_main_line_id=None):
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
            -queue: An object of type EventQueue that contains the events to process in the envrionment
            -main_line_id: str, the id of the main line vehicle.
            -next_main_line_id: str, the id of the next main line vehicle.


        Output:
            -optimization_result: An object of type OptimizationResult, that
                specifies, based on the results of the optimization, how the
                environment should be modified.
        """

        selected_next_legs, selected_routes = self.bus_prepare_input(state, main_line_id, next_main_line_id)
        
        ### OSO algorithm
        sp, ss, h_and_time = self.OSO_algorithm(selected_next_legs, selected_routes, state)
        main_route = state.route_by_vehicle_id[main_line_id]          
        # Update the main line route based on the OSO algorithm results.
        updated_main_route, skipped_legs, updated_legs = self.update_main_line(state, main_route, sp, ss, h_and_time, queue)

        # Walking route is added automatically by the VehicleReady event, DO NOT ADD MANUALLY
        optimized_route_plans = []
        if ss or sp or h_and_time[0]: #if any tactic is used, we need to update the route
            optimized_route_plan = OptimizedRoutePlan(updated_main_route)
            # Use the current and next stops of the route.
            optimized_route_plan.copy_route_stops()
            # Add the updated onboard legs to the route plan
            if updated_legs != -1:
                for leg in updated_legs['onboard']:
                    optimized_route_plan.add_already_onboard_legs(leg)
                for leg in updated_legs['boarding']:
                    optimized_route_plan.add_leg_to_remove(leg)
                    # input('adding ss onboard leg to optimized route plan...')
            optimized_route_plans.append(optimized_route_plan)
            # Update the route in the state
            state.route_by_vehicle_id[main_line_id] = updated_main_route
        
        ### Process OSO algorithm results
        if len(optimized_route_plans) > 0:
            print('processing optimized route plans for ss...')
            optimization_result = self.process_optimized_route_plans(
                optimized_route_plans, state)
        else:
            optimization_result = OptimizationResult(state, [], [])

        return optimization_result

    def get_route_by_vehicle_id(self, state, vehicle_id):
        """Get the route object corresponding to the vehicle_id."""
        route = next(iter([route for route in state.route_by_vehicle_id.values() if route.vehicle.id == vehicle_id]), None)
        return route

    def OSO_algorithm(self, selected_next_legs, selected_routes, state):
        """Online stochastic optimization algorithm for the bus dispatcher.
        Inputs:
            - selected_next_legs: list, the next legs that are assigned to the main line or onboard the main line.
            - selected_routes: list, current and next routes on the main line as well as connecting bus lines.
            - state: State object, the current state of the environment.
        
        Outputs:
            - sp: boolean, the result of the OSO algorithm for the speedup tactic.
            - ss: boolean, the result of the OSO algorithm for the skip-stop tactic.
            - h_and_time: tuple, the result of the OSO algorithm for the hold tactic the corresponding end of hold time (hold for planned time or transfer, the output hold time is already treated in the OSO algorithm)"""
        
        main_route = self.get_route_by_vehicle_id(state, state.main_line)
        next_route = self.get_route_by_vehicle_id(state, state.next_main_line)

        sp, ss, h_and_time =  self.OLD_OSO_algorithm( main_route, next_route, selected_next_legs, selected_routes, state)
        if (main_route is None) or (main_route.current_stop is not None):
            return(False, False, (False, -1))
        
        # ss, sp, h_and_time = self.OLD_OSO_algorithm(main_route, state)
        sp = False
        ss = False
        next_stop=main_route.next_stops[0]
        if next_stop is not None and str(next_stop.location.label) == '41391' and state.main_line == '2790970':
            ss = True
            input('on est la skip-stop implemented')
        # next_stop_departure_time = main_route.next_stops[0].departure_time
        # h_and_time = (True, next_stop_departure_time)
        h_and_time = (False, -1)
        return sp, ss, h_and_time

    def update_main_line(self, state, route, sp, ss, h_and_time, event_queue):
        """Update the main line route based on the OSO algorithm results.
        Inputs: 
            - route: Route object, the main line route.
            - sp: boolean, the result of the OSO algorithm for the speedup tactic.
            - ss: boolean, the result of the OSO algorithm for the skip-stop tactic.
            - h_and_time: (bool, int) tuple, the result of the OSO algorithm for the hold tactic and the corresponding end of hold time

        Outputs:
            - updated_route: Route object, the updated main line route.
        """
        h = h_and_time[0] #hold tactic boolean
        
        # if route.current_stop is not None: # bus departing from depot (Vehicle.READY event), no optimization needed
        #     return route, -1, -1
        if (not h) and (not ss) and (not sp): # no tactics
            return route, -1, -1
        
        # Get the planned arrival and departure times, and the dwell time at the next stop
        planned_arrival_time = route.next_stops[0].arrival_time
        planned_departure_time = route.next_stops[0].departure_time
        dwell_time = max(0, planned_departure_time - planned_arrival_time)
        prev_departure_time = route.previous_stops[-1].departure_time ### since the bus just departed from a stop
        
        # Find the arrival time at the next stop after tactics
        if sp:
            logger.info('Speedup implemented...')
            travel_time = int((planned_arrival_time - prev_departure_time) * self.speedup_factor)
        else: #also true for ss = True
            travel_time = planned_arrival_time - prev_departure_time
        arrival_time = prev_departure_time + travel_time

        # Find the dwell and departures time at the next stop after tactics
        if len(route.next_stops) <=1 :
            ss=False
        if ss:
            walking_time = self.get_walk_time(route)
            dwell_time = 0
        elif h: # add additional dwell time for hold tactic
            dwell_time = max(h_and_time[1] - arrival_time, dwell_time)
            logger.info('Hold time implemented...')
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
            logger.info('Skip-stop implemented at stop '+str(route.next_stops[0].location.label)+'...')
            #Add walking vehicle to the skipped stop
            walking_route = self.create_walk_vehicle_and_route(state, route, walking_time, event_queue)
            
            # Update the legs for passengers alighting at the skipped stop
            route, skipped_legs, new_legs = self.update_legs_for_passengers_alighting_at_skipped_stop(route, walking_route)
            
            # Get the legs for passengers boarding at the skipped stop
            new_legs = self.get_legs_for_passengers_boarding_at_skipped_stop(route, new_legs)
            # Skip stop
            route = self.route_skip_stop(route)
        else:
            skipped_legs = -1
            new_legs = -1
        return route, skipped_legs, new_legs

    def route_skip_stop(self, route):
        """Skip the next stop on the main line route.
        Inputs:
            - route: Route object, the main line route.

        Outputs:
            - route: Route object, the updated main line route."""
        if len(route.next_stops)>1:
            route.next_stops = route.next_stops[1:]
        return route

    def get_walk_time(self, main_route):
        """Get the walking time between the skipped stop and the following stop.
        Inputs:
            - main_route: Route object, the main line route.

        Outputs:
            - walking_time: int, the walking time in seconds between the skipped stop and the closest stop."""
        if len(main_route.next_stops)>1:
            following_stop_location = main_route.next_stops[1].location
        else: 
            following_stop_location = None
        if len(main_route.previous_stops)>0:
            previous_stop_location = main_route.previous_stops[-1].location
        else: 
            previous_stop_location = None

        # get skipped stop location 
        skipped_stop_location = main_route.next_stops[0].location
        coordinates_skipped = (skipped_stop_location.lat, skipped_stop_location.lon)
        #get distance between skipped stop and following stop
        if following_stop_location != None:
            coordinates_following = (following_stop_location.lat, following_stop_location.lon)
            distance_to_following = geopy.distance.geodesic(coordinates_skipped, coordinates_following).km
        else:
            distance_to_following = 1000000000
        if previous_stop_location != None:
            coordinates_previous= (previous_stop_location.lat, previous_stop_location.lon)
            distance_to_previous = geopy.distance.geodesic(coordinates_skipped, coordinates_previous).km
        else:   
            distance_to_previous = 1000000000
        walking_distance = min(distance_to_following, distance_to_previous)
        # we assume someones walks with a speed of 4km per hour
        walking_time = int(walking_distance/4*3600) #time in seconds
        return walking_time
    
    def create_walk_vehicle_and_route(self, state, main_route, walking_time, event_queue):
        """Create a walk vehicle that will travel between the skipped stop and the following stop. 
        Once the VehicleReady event is trigerred the route and vehicle will be added to the environment. 
        They should not be added manually. When the vehicle is ready/released and Optimize event is triggered and 
        unassigned passengers are assigned. This means that passengers that had to get off after the skipped stop 
        will be assigned to the walk vehicle.

        Inputs:
            - main_route: Route object, the main line route.
            - walking_time: int, the walking time in seconds between the skipped stop and the closest stop.

        Outputs:
            - walk_vehicle: Vehicle object, the walk vehicle."""
        start_stop = copy.deepcopy(main_route.next_stops[1]) #we assume we cannot skip the last stop
        start_stop.arrival_time = int(start_stop.arrival_time)
        start_stop.departure_time = start_stop.arrival_time + 5
        start_stop.cumulative_distance = 0
        start_stop.min_departure_time = None
        start_stop.passengers_to_board = []
        start_stop.boarding_passengers = []
        start_stop.boarded_passengers = []
        start_stop.passengers_to_alight = []
        start_stop.alighted_passengers = []
        start_stop.planned_arrival_time = start_stop.arrival_time
        start_stop.planned_departure_time_from_origin = start_stop.departure_time

        end_stop = copy.deepcopy(main_route.next_stops[0])
        #find the passengers ALIGHTING at this stop
        release_time = event_queue.env.current_time + 1
        end_stop.arrival_time = start_stop.departure_time + walking_time
        end_stop.departure_time = end_stop.arrival_time
        end_stop.cumulative_distance = walking_time*4/3600
        end_stop.min_departure_time = None
        end_stop.passengers_to_board = []
        end_stop.boarding_passengers = []
        end_stop.boarded_passengers = []
        end_stop.passengers_to_alight = []
        end_stop.alighted_passengers = []
        end_stop.planned_arrival_time = end_stop.arrival_time
        end_stop.planned_departure_time_from_origin = start_stop.departure_time

        next_stops = [end_stop]

        end_time = next_stops[-1].arrival_time+60

        vehicle_id = 'walking_vehicle_'+str(self.__walking_vehicle_counter)
        self.__walking_vehicle_counter += 1
        mode = None
        # Create vehicle
        vehicle = Vehicle(vehicle_id, start_stop.arrival_time, start_stop,
                          self.__CAPACITY, release_time, end_time, mode)
        # Create route
        route = Route(vehicle, next_stops)
        VehicleReady(vehicle, route, event_queue).add_to_queue()
        return (route)

    def update_legs_for_passengers_alighting_at_skipped_stop(self, route, walking_route):
        """Update the legs for passengers alighting at the skipped stop.
        Inputs:
            - route: Route object, the main line route.
            - skipped_legs: list, the legs for passengers alighting at the skipped stop that are onboard the main line.

        Outputs:
            - route: Route object, the updated main line route."""
        skipped_stop = route.next_stops[0]
        next_stop = route.next_stops[1]

        # Find passengers alighting at the skipped stop
        skipped_legs = [leg for leg in route.onboard_legs if leg.destination == skipped_stop.location]
        trips = [leg.trip for leg in skipped_legs]
        # remove alighting legs from the destination stop
        for trip in trips:
            skipped_stop.passengers_to_alight.remove(trip)
            # print(len(skipped_stop.passengers_to_alight), 'number of passengers to alight at skipped stop')
            # input()
        # remove the alighting legs from the onboard legs
        route.onboard_legs = [leg for leg in route.onboard_legs if leg not in skipped_legs]

        # prepare input data for walking
        new_legs = {}
        new_legs['walk'] = []
        new_legs['onboard'] = []
        new_legs['boarding'] = []
        walk_origin = walking_route.current_stop.location.label
        walk_destination = walking_route.next_stops[0].location.label
        walk_release_time = walking_route.vehicle.release_time-1
        walk_ready_time = walking_route.vehicle.release_time
        walk_due_time = walking_route.vehicle.end_time+10
        walk_cap_vehicle_id = walking_route.vehicle.id
        # replace the onboard legs with new legs with destination next_stop
        for leg in skipped_legs:
            leg_id = leg.id
            origin = leg.origin.label
            destination = next_stop.location.label
            nb_passengers = leg.nb_passengers
            release_time = leg.release_time
            ready_time = leg.ready_time
            due_time = leg.due_time
            trip = leg.trip
            cap_vehicle_id = leg.cap_vehicle_id
            new_leg = Leg(leg_id, LabelLocation(origin),
                          LabelLocation(destination),
                          nb_passengers, release_time,
                          ready_time, due_time, trip)
            new_leg.assigned_vehicle = route.vehicle
            new_leg.set_cap_vehicle_id(cap_vehicle_id)
            route.onboard_legs.append(new_leg) # passengers onboard are automatically reassigned to their destination stop in __process_route_plan if they are in RoutePlan()
            new_legs['onboard'].append(new_leg)

            # get the trip of the leg
            trip = leg.trip
            # replace the current leg of the trip
            trip.current_leg = new_leg

            # add alighting passenger to the following stop
            # No need, done in process route plans.

            # add walk leg to the trip
            walk_leg_id = leg_id + '_walking'
            walk_leg = Leg(walk_leg_id, LabelLocation(walk_origin),
                           LabelLocation(walk_destination), 
                           nb_passengers, walk_release_time,
                           walk_ready_time, walk_due_time, trip)
            walk_leg.set_cap_vehicle_id(walk_cap_vehicle_id)
            trip.next_legs = [walk_leg] + trip.next_legs
            new_legs['walk'].append(walk_leg)
        return route, skipped_legs, new_legs

    def get_legs_for_passengers_boarding_at_skipped_stop(self, route, new_legs):
        """Update the legs for passengers boarding at the skipped stop.
        Inputs:
            - route: Route object, the main line route.
            - new_legs: dict, the new legs for passengers boarding at the skipped stop.

        Outputs:
            - new_legs: dict, the updated new legs."""
        # Find legs supposed to board at the skipped stop
        boarding_legs = [leg for leg in route.assigned_legs if leg.origin == route.next_stops[0].location]
        # Add 'boarding_legs_to_remove' to the new legs
        new_legs['boarding'] = boarding_legs
        # # Remove the boarding legs from the stop (this stop is skipped so not modified later on)
        # route.next_stops[0].passengers_to_board = []
        return new_legs
    
    def contains_walk(self, input_string):
        return 'walk' in input_string
    
    def OLD_OSO_algorithm(self, route, next_route, selected_next_legs, selected_routes, state): 
        stop = route.next_stops[0]
        if stop == None: 
            return(False, False, (False, -1))
        stops = route.next_stops[0: self.horizon]
        stops_second = next_route.next_stops[0: self.horizon]
                                            # Estimate arrival time of transfers at stops
        transfer_times = self.get_transfer_stop_times(tops_first = stops, 
                                                      stops_second = stops_second,
                                                      type_ttime = self.algo_parameters['type_ttime'])
        trip_id = route.vehicle.id
        stop_id = stop.location.label
        last_stop = self.allow_tactics_at_stops(state, transfer_times)
        initial_flows = route.onboard_legs
                                            # Dictionnary saving tactics used in all scenarios
        T_regret=self.create_tactics_dict(self, stop)
        if self.__algo==2: # Regret Algorithm
            i=0
            j_try=0
            succes = False
        return(False, False, (False, -1))
        #     while i<self.algo_parameters["nbr_simulations"]:
        #         if j_try<int(self.algo_parameters["j_try"]):
        #             try: # Bias because the scenarios which work are those where m/d are possible.
        #                 j_try+=1
        #                 # Step a: Generate instance for scenario j_try for the Regret algorithm
        #                 passages,last=NewGenerateur(lign,
        #                                             dir, 
        #                                             self.general_parameters['nbr_bus'], 
        #                                             Data,
        #                                             type_intervalles=self.algo_parameters['type_intervalles'],
        #                                             type_dwell=self.algo_parameters['type_dwell'],
        #                                             type_tps_parcours=self.algo_parameters['type_tps_parcours'],
        #                                             type_m=self.algo_parameters['type_m'],
        #                                             type_d=self.algo_parameters['type_d'],
        #                                             type_tm=self.algo_parameters['type_tm'],
        #                                             type_td=self.algo_parameters['type_td'],
        #                                             type_ttime=self.algo_parameters['type_ttime'],
        #                                             Real_passages=passages_multiple,
        #                                             initial_flows=initial_flows,
        #                                             plan_times=planned_times,
        #                                             dimension=self.general_parameters["dimension"],
        #                                             last=last,
        #                                             horizon=self.horizon,
        #                                             transfer_times=transfer_times
        #                                             )
        #                 runtime_start_regret=time.time()
        #                 # Step b: Create graph from generated instance
        #                 G_gen, bus,od,stats_od,extras=build_multiple_buses_hash(passages_multiple=passages,
        #                                                                         flot_initial=initial_flows,
        #                                                                         pas=self.general_parameters["pas"],
        #                                                                         price=self.general_parameters["price"],
        #                                                                         speedup_gen=self.speedup_factor,
        #                                                                         ss_gen=self.skip_stop,
        #                                                                         od_dict={}, 
        #                                                                         simu=True,
        #                                                                         last_stop=last_stop)
        #                 # nb_noeuds.append(nb_nodes(G_gen))
        #                 # nb_arcs.append(nb_edges(G_gen))

        #                 # Step c: Get Data on optimization results
        #                 passage_gen_id=[p for p in passages[trip_id] if get_passage_stop_id(p)==int(stop_id) and get_passage_transfer(p)==False][0]
        #                 dwell_gen=get_passage_dwell_time(passage_gen_id)
        #                 last_dwell_real=route.previous_stops[-1].departure_time - route.previous_stops[-1].arrival_time
        #                 last_dist_real=real_prev_dists[stop_id]
        #                 simu_last_temps_parcours=get_simu_last_temps_parcours(passages,
        #                                                                       trip_id,
        #                                                                       passage_gen_id,
        #                                                                       last_regret)
        #                 time_max, wait, speedup, ss, bus_flows, opt_val, runtime=get_gen_data(G_gen,stop_id,
        #                                                                                       trip_id,
        #                                                                                       self.general_parameters["price"],
        #                                                                                       affichage=False, 
        #                                                                                       global_savepath=global_savepath,
        #                                                                                       simu_last_temps_parcours=simu_last_temps_parcours,
        #                                                                                       j_try=str(j_try)+'regret')

        #                 # Step d: Update tactics dictionary
        #                 T_regret=update_tactics_dict_regret(T_regret, 
        #                                                     time_max, wait, speedup, ss,
        #                                                     bus_flows,
        #                                                     stop_id, trip_id,
        #                                                     passages_gen=passages_regret,
        #                                                     opt_cost=opt_val,
        #                                                     initial_flows=initial_flows,
        #                                                     pas=self.general_parameters["pas"],
        #                                                     price=self.general_parameters["price"],
        #                                                     speedup_gen=self.speedup_factor,
        #                                                     ss_gen=self.skip_stop,
        #                                                     prix_hors_bus=self.general_parameters["prix_hors_bus"],
        #                                                     global_savepath=global_savepath,
        #                                                     affichage=affichage,
        #                                                     j_try=j_try)
        #                 runtime_regret=time.time()-runtime_start_regret
        #                 # runtimes_regret.append(runtime_regret)
        #                 i+=1
        #                 if self.algo == 1 or self.algo ==0:
        #                     j_try = int(self.algo_parameters["j_try"]) + 1

        #             except Exception as e:
        #                 traceback.print_exc()
        #                 print('probleme dans simulation numero:',j_try, 'stop_id =', stop_id)
        #         else: 
        #             print('on a depasse le nombre possible de simus sans reuissir')
        #             input("Press enter to continue...")
        #             return(False, False, (False, -1))
        #     # Step 5: Apply tactics
        #     if self.algo == 2: # Regret
        #         time_max_regret, wait_regret, speedup_regret, ss_regret=choose_tactic(T_regret,
        #                                                                               self.skip_stop,
        #                                                                               self.speedup_factor,
        #                                                                               last_stop)

        #     # Step 6: Apply tactics
        #     passages_multiple_real,last, initial_flows,final_passages,h_prev,h_final=apply_tactics(passages_multiple,
        #                                                                                         stop_id,trip_id,
        #                                                                                         last,
        #                                                                                         initial_flows,
        #                                                                                         dwell_gen,
        #                                                                                         h_prev,
        #                                                                                         h_final,
        #                                                                                         last_dwell_real,
        #                                                                                         time_max_regret,
        #                                                                                         wait_regret,
        #                                                                                         speedup_regret,
        #                                                                                         ss_regret,
        #                                                                                         final_passages=final_passages,
        #                                                                                         last_dist_real=last_dist_real)
        # transfer_time_to_use=[p for p in Real_passages_gen[trip_id] if get_passage_stop_id(p)==int(stop_id) and get_passage_transfer(p)==False][0]
        # transfer_ha=get_passage_heure_act(transfer_time_to_use)

    def get_transfer_times(self, transfer_data, transfer_ha, type_ttime):
        """Get the transfer times for the passengers.
        Inputs:
            - transfer_data: dict, the transfer data.
            - transfer_ha: int, the current time.
            - type_ttime: int, the type of transfer time generation.
            
        Outputs:
            - transfer_times: dict, the transfer times for the passengers"""
        transfer_times={}
        for trip in transfer_data: 
            transfer_times[trip]={}
            for stop in transfer_data[trip]:
                transfer_times[trip][stop]=[]
                for heure in transfer_data[str(trip)][stop]:
                    times=transfer_data[str(trip)][stop][heure]
                    if type_ttime==2:### real
                        transfer_times[trip][stop].append(times[0][1])
                    else:
                        e=next((x for x in times if x[1] <transfer_ha),-1)
                        if e==-1: 
                            #ce bus n'est pas parti a l'heure actuelle, notre meilleure estimation est hp a l'arret
                            transfer_times[trip][stop].append(times[0][0])
                        else: 
                            # 0: heure planifiée +retard actuel
                            if type_ttime==0: #heure planifiee +retard actuel
                                retard=int(e[1])-int(e[0])
                                transfer_times[trip][stop].append(times[0][0]+retard)
                            # 1: temps de parcours proportionnel à la distance restante actuelle (référence=tps parcours planifié)
                            elif type_ttime==1:#same as type_ttime=0 car pas plus d'infos
                                h_reel_passage=e[1]
                                temps_parcours_plan=times[0][0]-e[0]
                                heure_act=h_reel_passage+temps_parcours_plan
                                transfer_times[trip][stop].append(heure_act)
        return(transfer_times)

    def get_transfer_data(self, stop_times, passages, transfer_stops, horizon, lign, dir):
        """ 
        """
        # 0-trip_id
        # 1-arrival_time-heure d'arrivee a l'arret
        # 2-departure_time-heure de depart depuis l'arret
        # 3-stop_id-id de l'arret
        # 4-stop_sequence- ordre de l'arret dans la sequence 
        # 5-shape_dist_traveled-distance parcourue depuis l'origine
        # 6-nb_passengers-nb de passagers en bus
        # 7-nb_montants-nbr de passagers montants a cet arret
        # 8-nb_descendants-nbr de passagers descendants a cet arret
        # 9-ligne-nom complet de la ligne "nom"+"dir"(format N,S,O,E)
        # 10-h_plan-heure d'arrivee planifiee a l'arret
        # 11-dep_ori-heure de depart depuis l'origine pour ce trajet 
        if len(stop_times)==0:
            return({})
        #Get all stops
        ligne_direction = lign+dir
        completename=os.path.join("stl","Data",'route_stops_'+lign+dir+'_month.txt')
        alltype=np.dtype([('f0', 'i8'), ('f1', 'U12'),('f2','float16'),('f3','i8')])
        stops=self.genfromtxt_with_lock(completename,delimiter=",",dtype=alltype, usecols=[0,1,2,3], names=True)
        # 0-stop_order
        # 1-stop_id
        # 2-dist_cum
        # 3-number of times stop was registered in the month
        stop_passages={}
        transfer_data={}
        tmp={}
        stop_times=sorted(stop_times, key=itemgetter(11,4))
        order=sorted([(passages[trip][0].ha-passages[trip][0].cost,trip) for trip in passages],key=itemgetter(0))
        normaux=[p for p in passages[order[-1][1]] if get_passage_transfer(p)==False] 
        for stop_time in stop_times:
            transfer_data[trip]={}
            stop=int(get_passage_stop_id(p))
            if stop in stop_passages:
                stop_passages[stop].append((get_passage_heure_act(p),trip))
            else: 
                stop_passages[stop]=[(get_passage_heure_act(p),trip)]

        for stop in stop_passages: 
            new=[]
            stop_passages[stop]=sorted(stop_passages[stop],key=itemgetter(0))
            tmp=stop_passages[stop].pop(0)
            new_tmp=(tmp[0]-900,tmp[1])
            new.append(new_tmp)
            prev=new[0][0]+900
            for i in range(1,len(stop_passages[stop])):
                intervalle = stop_passages[stop][i][0]-prev
                if intervalle>1200:
                    new.append((stop_passages[stop][i][0]-600,stop_passages[stop][i][1]))
                else: 
                    new.append((stop_passages[stop][i][0]-int(intervalle/2),stop_passages[stop][i][1]))
                prev=stop_passages[stop][i][0]
            stop_passages[stop]=new
            stop_passages[stop].append((stop_passages[stop][-1][0]+1200,-1))
        for (temps_depart,trip) in order:
            transfer_data[trip]={}
            normaux=[(p, get_passage_dist(p)) for p in passages[trip] if get_passage_transfer(p)==False]
            normaux=sorted(normaux, key=itemgetter(1))
            first=int(get_passage_stop_id(normaux[0][0]))
            start = [k for k, x in enumerate(stops) if int(x[1]) == first][0]
            for j in range(start,min(start+1+horizon, len(stops))): 
                stop=int(stops[j][1])
                if stop in stop_passages:
                    index=next((i for i, (v, w) in enumerate(stop_passages[stop]) if w == trip),-1)
                    if index!=-1:
                        time_max=stop_passages[stop][index+1][0]
                        min_time=stop_passages[stop][index][0]
                if stop in transfer_stops:
                    for (stop_corr, ligne_dir_corr) in transfer_stops[stop]:
                        i=0
                        x=stop_times[i]
                        while int(x[11])<time_max and i<len(stop_times)-1: 
                            info=( int(stop_times[i][3]), str(stop_times[i][9]))
                            if info ==(stop_corr,ligne_dir_corr): 
                                heure_corr=int(x[1])
                                if heure_corr>min_time and heure_corr<time_max:
                                    if stop in transfer_data[trip]:
                                        transfer_data[trip][stop][heure_corr]=[]
                                    else: 
                                        transfer_data[trip][stop]={}
                                        transfer_data[trip][stop][heure_corr]=[]
                                    trip_id=str(stop_times[i][0])
                                    jt=i
                                    while stop_times[jt][0]==trip_id and jt>=0: #ordre inversement chronologique
                                        hp=int(stop_times[jt][10])
                                        arr_time=int(stop_times[jt][1])#actual arrival time
                                        dist=float(stop_times[jt][5])
                                        transfer_data[trip][stop][heure_corr].append( (hp, arr_time,dist ))
                                        jt-=1
                            i+=1
                            x=stop_times[i]
        return(transfer_data)

    def genfromtxt_with_lock(filename, dtype, delimiter=",", usecols=None, names=True,encoding='bytes',skip_header=0):
        lock = multiprocessing.Lock()

        def file_lock(operation):
            if operation == 'lock':
                lock.acquire()
            elif operation == 'unlock':
                lock.release()

        with open(filename, 'r') as file:
            file_lock('lock')  # Acquire lock before reading
            data = np.genfromtxt(file, delimiter=delimiter, dtype=dtype, usecols=usecols, names=names,encoding=encoding,skip_header=skip_header)
            file_lock('unlock')  # Release lock after reading
            return data
        
    def get_transfer_stop_times(self, state, stops_first, stops_second, type_ttime):
        min_time = stops_first[0].arrival_time - 1800 # 30 minutes before arrival
        max_time = stops_second[-1].departure_time
        available_connections = state.available_connections
        #Get potential transfers stops
        all_stops = [int(str(stop.location)) for stop in stops_first + stops_second]
        to_add = []
        for stop in all_stops:
            if stop.location in available_connections:
                for stop in available_connections[stop.location]:
                    to_add.append(int(str(stop)))
        all_stops += to_add
        # Get potential transfer routes
        all_routes = [route for route in state.route_by_vehicle_id.values() if route.vehicle.id != state.main_line and route.vehicle.id != state.next_main_line]
        # For each stop note potential transfer routes and their arrival times.
        transfer_stop_times = {}
        for route in all_routes:
            if route.current_stop is not None:
                if int(str(route.current_stop.location)) in all_stops and route.current_stop.arrival_time > min_time and route.current_stop.arrival_time < max_time:
                    print("Current stop is in all stops for potential transfers")
                    if route.current_stop.location not in transfer_stop_times:
                        transfer_stop_times[route.current_stop.location] = []
                    current_stop_arrival_time_estimation = self.get_arrival_time_estimation(route, route.current_stop, type_ttime)
                    transfer_stop_times[route.current_stop.location].append(route.current_stop.arrival_time, route.vehicle.id)
            if route.next_stops is not None:
                for stop in route.next_stops:
                    if int(str(stop.location)) in all_stops and stop.arrival_time > min_time and stop.arrival_time < max_time:
                        print("Next stop is in all stops for potential transfers")
                        if stop.location not in transfer_stop_times:
                            transfer_stop_times[stop.location] = []
                        current_stop_arrival_time_estimation = self.get_arrival_time_estimation(route, stop, type_ttime)
                        transfer_stop_times[stop.location].append(current_stop_arrival_time_estimation, route.vehicle.id)
        return transfer_stop_times
    
    def get_arrival_time_estimation(self, route, stop, type_ttime):
        if type_ttime==2: # real
            return stop.arrival_time
        if route.previous_stops == []: #bus n'est pas parti
            return stop.planned_arrival_time
            #ce bus n'est pas parti a l'heure actuelle, notre meilleure estimation est hp a l'arret
        if route.current_stop is not None: 
            current_delay = route.current_stop.arrival_time - route.current_stop.planned_arrival_time
            return stop.planned_arrival_time + current_delay
        last_visited_stop = route.previous_stops[-1]
        current_delay = last_visited_stop.arrival_time - last_visited_stop.planned_arrival_time
        return stop.planned_arrival_time + current_delay
    
    def allow_tactics_at_stops(self, state, transfer_times):
        stops = state.route_by_vehicle_id[state.main_line].next_stops[:self.horizon]
        normal=stop.departure_time
        tactic=stop.departure_time
        previous_departure_time = state.route_by_vehicle_id[state.main_line].previous_stops[-1].departure_time
        dwell=0
        last=-1
        for i in range(len(stops)):
            stop=stops[i]
            travel_time = stop.arrival_time - previous_departure_time
            dwell = stop.departure_time-stop.arrival_time
            stop_id = stop.location
            normal_time=travel_time+dwell
            if self.skip_stop and self.speedup_factor!=1:
                time_ss=travel_time
                time_sp=int(0.8*travel_time)+dwell
                time=min(time_ss,time_sp)
                tactic=tactic+time
            elif self.skip_stop: 
                time=travel_time
                tactic=tactic+time
            elif self.speedup_factor!=1:
                time=int(0.8*travel_time)+dwell
                tactic=tactic+time
            normal=normal+normal_time
            trip_id = state.main_line
            if stop_id in transfer_times:
                for t in transfer_times[stop_id]:
                    if normal>t:
                        if tactic<=t: #tactics can turn an impossible transfer into a possible one
                            last=stop
        return(last)
    
    def create_tactics_dict(self, last_stop):
        T={}
        ss = self.skip_stop
        sp = self.speedup_factor
        T['h_hp']=0
        T['none']=0
        T['h_t']={}
        T['h_t'][0]=0
        T['h_t'][1]=[]
        if last_stop == -1:
            return(T)
        if ss==True: 
            T['ss']=0
        if sp!=1:  
            T['sp']=0
            T['sp_hp']=0
            T['sp_t']={}
            T['sp_t'][0]=0
            T['sp_t'][1]=[]
        return(T)