import logging

from multimodalsim.optimization.optimization import OptimizationResult
from multimodalsim.optimization.dispatcher import OptimizedRoutePlan, Dispatcher
from multimodalsim.config.fixed_line_dispatcher_config import FixedLineDispatcherConfig
from multimodalsim.simulator.vehicle import Vehicle, Route, Stop
from multimodalsim.simulator.request import Leg
from multimodalsim.simulator.vehicle_event import VehicleReady
from multimodalsim.optimization.fixed_line.graph_constructor import Graph_Node, Graph_Edge, Graph, build_graph_with_tactics, build_graph_without_tactics, extract_tactics_from_solution, get_all_tactics_used_in_solution, display_graph

import geopy.distance
import random 
import copy
from operator import itemgetter
import time
import os
import numpy as np
import multiprocessing
import math
from statistics import mean
from collections import Counter
import traceback
from typing import List
logger = logging.getLogger(__name__)

class FixedLineDispatcher(Dispatcher):

    def __init__(self, config=None, ss = False, sp = False, algo = 0):
        super().__init__()
        self.__config = FixedLineDispatcherConfig() if config is None else config
        self.__algo = algo
        self.__general_parameters = self.__config.get_general_parameters()
        self.__speedup_factor = self.__config.get_speedup_factor(sp)
        self.__skip_stop = self.__config.get_skip_stop(ss)
        self.__horizon = self.__config.get_horizon(ss, sp)
        self.__algo_parameters = self.__config.get_algo_parameters(algo)
        self.__walking_vehicle_counter = 0
        self.__CAPACITY = 80
        self.__Data = None
        self.__route_name = None

    @property
    def algo(self):
        return self.__algo
    
    @property
    def speedup_factor(self):
        return self.__speedup_factor
    
    @speedup_factor.setter
    def speedup_factor(self, sf):
        self.__speedup_factor = sf
    
    @property
    def walking_speed(self):
        return self.__general_parameters["walking_speed"]
    
    @property
    def skip_stop(self):
        return self.__skip_stop
    
    @skip_stop.setter
    def skip_stop(self, ss):
        self.__skip_stop = ss
    
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
    
    @property
    def Data(self):
        return self.__Data
    
    @Data.setter
    def Data(self, data):
        self.__Data = data

    @property
    def route_name(self):
        return self.__route_name
    
    @route_name.setter
    def route_name(self, name):
        self.__route_name = name
    
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

    def bus_prepare_input(self, state, main_line_id = None, next_main_line_id = None):
        """Before optimizing, we extract the legs and the routes that we want to be considered by the optimization algorithm.
        For the FixedLineDispatcher, we want to keep only the legs that will cross the main line or next main line in
        the stops in the optimization horizon (assigned to , onboard , or potentially boarding in future stops).
        """
        logger.info('STARTING BUS OPTIMIZE...')
        state.main_line = main_line_id
        state.next_main_line = next_main_line_id

        # Get the selected routes
        selected_routes = [route for route in state.route_by_vehicle_id.values() if route.vehicle.id == main_line_id or route.vehicle.id == next_main_line_id]

        # Get the next stops in the horizon on the main line
        main_line = state.route_by_vehicle_id[main_line_id]
        if main_line.vehicle.route_name == 'Walking_route':
            return [], []
        self.route_name = main_line.vehicle.route_name
        main_line_stops = main_line.next_stops[0:self.horizon]
        
        # The next legs assigned and onboard the selected routes
        selected_next_legs = [leg for route in selected_routes for leg in route.onboard_legs]
        selected_next_legs += [leg for route in selected_routes for leg in route.assigned_legs if leg.origin in [stop.location for stop in main_line_stops] or leg.destination in [stop.location for stop in main_line_stops]]
        
        # Get trips associated with the selected legs
        selected_trips = [leg.trip for leg in selected_next_legs]
        for trip in selected_trips:
            route=None
            second_next_route=None
            if trip.current_leg is not None: #Onboard legs
                current_vehicle_id=trip.current_leg.assigned_vehicle.id if trip.current_leg.assigned_vehicle != None else trip.current_leg.cap_vehicle_id
                if current_vehicle_id == main_line_id: #passenger on board main line, check if transfer to other lines
                    if len(trip.next_legs)>0 and trip.current_leg.destination in [stop.location for stop in main_line_stops]: #transfer to other line in the horizon
                        next_leg = trip.next_legs[0]
                        next_vehicle_id = next_leg.assigned_vehicle.id if next_leg.assigned_vehicle != None else next_leg.cap_vehicle_id
                        route = self.get_route_by_vehicle_id(state, next_vehicle_id)
                    # else: #No transfer to other lines, no route_id to add.
                    #if passenger transferred from another bus to main line, it is already done so we don't need the info
                else: #passenger on board other line, transfer to main line
                    if len(trip.next_legs)>0:
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
                            route = self.get_route_by_vehicle_id(state, previous_vehicle_id)
                        if i < len(trip.next_legs)-1 and next_leg.destination in [stop.location for stop in main_line_stops]: #passenger also transfers to another bus in the horizon
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
                                route = self.get_route_by_vehicle_id(state, previous_vehicle_id)
                            if i < len(trip.next_legs)-1 and next_leg.destination in [stop.location for stop in main_line_stops]:
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

        # selected_next_legs, selected_routes = self.bus_prepare_input(state, main_line_id, next_main_line_id)
        state.main_line = main_line_id
        state.next_main_line = next_main_line_id
        
        ### OSO algorithm
        sp, ss, h_and_time = self.OSO_algorithm(state)
        main_route = state.route_by_vehicle_id[main_line_id]          
        # Update the main line route based on the OSO algorithm results.
        updated_main_route, skipped_legs, updated_legs = self.update_main_line(state, main_route, sp, ss, h_and_time, queue)

        # Walking route is added automatically by the VehicleReady event, DO NOT ADD MANUALLY
        optimized_route_plans = []
        if ss or sp or h_and_time[0]: #if any tactic is used, we need to update the route
            print('We use the following tactics: skip-stop', ss, 'speedup = ', sp, 'hold and time', h_and_time )
            input()
            optimized_route_plan = OptimizedRoutePlan(updated_main_route)
            # Use the current and next stops of the route.
            optimized_route_plan.copy_route_stops()
            # Add the updated onboard legs to the route plan
            if updated_legs != -1:
                for leg in updated_legs['onboard']:
                    optimized_route_plan.add_already_onboard_legs(leg)
                for leg in updated_legs['boarding']:
                    optimized_route_plan.add_leg_to_remove(leg)
            optimized_route_plans.append(optimized_route_plan)
            # Update the route in the state
            state.route_by_vehicle_id[main_line_id] = updated_main_route
        
        ### Process OSO algorithm results
        if len(optimized_route_plans) > 0:
            logger.info('processing optimized route plans for ss...')
            optimization_result = self.process_optimized_route_plans(
                optimized_route_plans, state)
        else:
            logger.info('No tactics used, nothing to do...')
            optimization_result = OptimizationResult(state, [], [])

        return optimization_result

    def get_route_by_vehicle_id(self, state, vehicle_id):
        """Get the route object corresponding to the vehicle_id."""
        route = next(iter([route for route in state.route_by_vehicle_id.values() if route.vehicle.id == vehicle_id]), None)
        return route

    # def OSO_algorithm(self, selected_next_legs, selected_routes, state):
    #     """Online stochastic optimization algorithm for the bus dispatcher.
    #     Inputs:
    #         - selected_next_legs: list, the next legs that are assigned to the main line or onboard the main line.
    #         - selected_routes: list, current and next routes on the main line as well as connecting bus lines.
    #         - state: State object, the current state of the environment.
        
    #     Outputs:
    #         - sp: boolean, the result of the OSO algorithm for the speedup tactic.
    #         - ss: boolean, the result of the OSO algorithm for the skip-stop tactic.
    #         - h_and_time: tuple, the result of the OSO algorithm for the hold tactic the corresponding end of hold time (hold for planned time or transfer, the output hold time is already treated in the OSO algorithm)"""

    #     sp, ss, h_and_time =  self.OLD_OSO_algorithm( main_route, next_route, selected_next_legs, selected_routes, state)
        
    #     # ss, sp, h_and_time = self.OLD_OSO_algorithm(main_route, state)
    #     sp = False
    #     ss = False
    #     next_stop=main_route.next_stops[0]
    #     if next_stop is not None and str(next_stop.location.label) == '41391' and state.main_line == '2790970':
    #         ss = True
    #         input('on est la skip-stop implemented')
    #     # next_stop_departure_time = main_route.next_stops[0].departure_time
    #     # h_and_time = (True, next_stop_departure_time)
    #     h_and_time = (False, -1)
    #     return sp, ss, h_and_time

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
            ss = False
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
            walking_route = self.create_walk_vehicle_and_route(route, walking_time, event_queue)
            
            # Update the legs for passengers alighting at the skipped stop
            route, skipped_legs, new_legs = route.update_legs_for_passengers_alighting_at_skipped_stop(walking_route)
            
            # Get the legs for passengers boarding at the skipped stop
            new_legs = route.get_legs_for_passengers_boarding_at_skipped_stop(new_legs)
            # Skip stop
            route.route_skip_stop()
        else:
            skipped_legs = -1
            new_legs = -1
        return route, skipped_legs, new_legs

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
    
    def create_walk_vehicle_and_route(self, main_route, walking_time, event_queue):
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
        start_stop.passengers_to_board_int = 0
        start_stop.boarding_passengers = []
        start_stop.boarded_passengers = []
        start_stop.passengers_to_alight = []
        start_stop.passengers_to_alight_int = 0
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
        end_stop.passengers_to_board_int = 0
        end_stop.boarding_passengers = []
        end_stop.boarded_passengers = []
        end_stop.passengers_to_alight = []
        end_stop.passengers_to_alight_int = 0
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
                          self.__CAPACITY, release_time, end_time, mode, route_name='Walking_route')
        # Create route
        route = Route(vehicle, next_stops)
        VehicleReady(vehicle, route, event_queue).add_to_queue()
        return (route)
    
    def contains_walk(self, input_string):
        return 'walk' in input_string
    
    def OSO_algorithm(self, state): 
        """Online stochastic optimization algorithm for the bus dispatcher.
        Inputs:
            - state: State object, the current state of the environment.
        
        Outputs:
            - sp: boolean, the result of the OSO algorithm for the speedup tactic.
            - ss: boolean, the result of the OSO algorithm for the skip-stop tactic.
            - h_and_time: tuple, the result of the OSO algorithm for the hold tactic and the corresponding end of hold time
                (The output hold time is already treated in the OSO algorithm)"""
        route = self.get_route_by_vehicle_id(state, state.main_line)
        logger.info('Main line is {}'.format(route.vehicle.id))
        next_route = self.get_route_by_vehicle_id(state, state.next_main_line)
        if (route is None or next_route is None) or (route.current_stop is not None) or route.next_stops[0] is None:
            logger.info("Main route bus is None = {}, Next bus on main route is None = {}, bus has not departed yet = {}, there are no next stops = {}".format(route is None, next_route is None, route.current_stop is not None, len(route.next_stops)==0))
            # input('Error in OSO algorithm')
            return(False, False, (False, -1))
        
        logger.info('We go into the OSO algorithm :) ')
        
        # get stops on both routes
        stops = route.next_stops[0: self.horizon]
        last_stop_id = stops[-1].location.label
        stops_second = next_route.get_next_route_stops(last_stop_id)
        stop = route.next_stops[0]
        stop_id = int(stop.location.label)
        bus_trip_id = route.vehicle.id
        bus_next_trip_id = next_route.vehicle.id
        logger.info('Main line is {} and next main line is {} and first stop is {}, last stop is {}'.format(route.vehicle.id, next_route.vehicle.id, stop_id, last_stop_id))

        #Get initial flows and previous times
        initial_flows = {}
        initial_flows[bus_trip_id] = int(len(route.onboard_legs))
        initial_flows[bus_next_trip_id] = int(len(next_route.onboard_legs))
        last_departure_times = {}
        last_departure_times[bus_trip_id] = route.previous_stops[-1].departure_time if route.previous_stops != [] else route.next_stops[0].arrival_time -1
        last_departure_times[bus_next_trip_id] = next_route.previous_stops[-1].departure_time if next_route.previous_stops != [] else next_route.next_stops[0].arrival_time -1
        

        # Estimate arrival time of transfers at stops
        transfer_times = {}
        transfer_times[bus_trip_id] = self.get_transfer_stop_times(state = state,
                                                                stops = stops,
                                                                type_transfer_arrival_time = self.algo_parameters['type_transfer_arrival_time'],
                                                                time_to_prev=1200,
                                                                time_to_next=1200)
        transfer_times[bus_next_trip_id] = self.get_transfer_stop_times(state = state,
                                                                    stops = stops_second,
                                                                    type_transfer_arrival_time = self.algo_parameters['type_transfer_arrival_time'],
                                                                    time_to_prev=1200,
                                                                    time_to_next=1200)
        logger.info('Transfer times computed')

        last_stop = self.allow_tactics_at_stops(state, transfer_times[route.vehicle.id])
        runtimes = []
        # Create dictionnary saving tactics used in all scenarios
        if self.__algo==2: # Regret Algorithm
            tactic_regrets_dict = self.create_tactics_dict(self, last_stop)
        i=0
        j_try=0
        while i < self.algo_parameters["nbr_simulations"]:
            if j_try < self.algo_parameters["j_try"]:
                try: # Bias because the scenarios which work are those where m/d are possible.
                    j_try+=1
                    runtime_start=time.time()
                    # Step a: Generate instance for scenario j_try for the Regret algorithm
                    bus_trips, transfers = self.Generate_scenario(main_route = route,
                                                                next_route = next_route, 
                                                                stops = stops, 
                                                                next_stops = stops_second,
                                                                last_stop = last_stop,
                                                                transfer_times = transfer_times
                                                                )
                    # Step b: Create graph from generated instance
                    G_gen = build_graph_with_tactics(bus_trips = bus_trips,
                                                    transfers = transfers,
                                                    last_departure_times = last_departure_times,
                                                    initial_flows = initial_flows,
                                                    time_step = self.general_parameters["step"],
                                                    price = self.general_parameters["price"],
                                                    global_speedup_factor = self.speedup_factor,
                                                    global_skip_stop_is_allowed = self.skip_stop,
                                                    simu = True,
                                                    last_stop = int(last_stop.location.label) if last_stop != -1 else -1)
                    display_graph(G_gen, display_flows = False, name = 'Test_graph')
                    # Step c: Get Data on optimization results
                    prev_stop = route.previous_stops[-1] if route.previous_stops != [] else None
                    prev_stop_departure_time = prev_stop.departure_time if prev_stop != None else bus_trips[bus_trip_id][0].arrival_time -1
                    last_travel_time = bus_trips[bus_trip_id][0].arrival_time - prev_stop_departure_time
                    max_departure_time, hold, speedup, skip_stop, bus_flows, optimal_value, runtime = self.get_solution_for_graph(G_gen,
                                                                                                                                  stop_id,
                                                                                                                                  bus_trip_id)

                    # Step d: Update tactics dictionary
                    if self.algo == 2: # Regret Algorithm
                        tactic_regrets_dict = self.update_tactics_dict_regret(tactic_regrets_dict,
                                                                              max_departure_time, hold, speedup, skip_stop,
                                                                              bus_flows,
                                                                              route,
                                                                              next_route,
                                                                              bus_trips,
                                                                              transfers,
                                                                              optimal_value,
                                                                              prev_times = last_departure_times)
                    elif self.algo == 1 or self.algo == 0: # Offline or Deterministic
                        i = self.algo_parameters["nbr_simulations"]
                        j_try = int(self.algo_parameters["j_try"]) + 1
                    runtime = time.time() - runtime_start
                    runtimes.append(runtime)
                    i += 1
                except Exception as e:
                    traceback.print_exc()
                    logger.warning('Problem with scenario {}/{} and stop_id {}'.format(j_try, self.algo_parameters["j_try"], stop_id))
                    input()
            else: 
                logger.warning('The scenario generation failed after {} tries.'.format(j_try))
                return(False, False, (False, -1))
        # Get the best tactic
        if self.algo == 2: # Regret
            max_departure_time, hold, speedup, skip_stop, = self.choose_tactic(tactic_regrets_dict, last_stop)
        return(speedup == 1, skip_stop == 1, (hold >= 0 , max_departure_time))

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
        
    def get_transfer_stop_times(self, state,
                                stops,
                                type_transfer_arrival_time,
                                time_to_prev = 600,
                                time_to_next = 600):
        """Get the arrival times of the transfers at the stops.
        Inputs:
            - state: State object, the current state of the environment.
            - stops: list, the stops to consider.
            - type_transfer_arrival_time: int, the type of transfer arrival time generation to consider.
            - time_to_prev: int, the time to consider before the arrival time of the first stop.
            - time_to_next: int, the time to consider after the departure time of the last stop.
        
        Outputs:
            - transfer_stop_times: dict, the arrival times of the transfers at the stops.
              The format of the dict is as follows:
              transfer_stop_times[stop_id : int] = [(arrival_time : int, route_name :str "ligne+dir"), ...]"""

        #Get potential transfers stops
        available_connections = state.available_connections
        all_stops = [int(stop.location.label) for stop in stops]
        to_add = []
        for stop in all_stops:
            if stop in available_connections:
                for transfer_stop_label in available_connections[stop]:
                    to_add.append(transfer_stop_label)
        all_stops += to_add
        all_stops = list(set(all_stops))

        #Get next vehicles
        next_vehicles = state.next_vehicles

        # Get potential transfer routes: consider all routes, not just selected routes as we don't know in advance where passengers will transfer.
        all_routes = [route for route in state.route_by_vehicle_id.values() if route.vehicle.id != state.main_line and route.vehicle.id != state.next_main_line]
        
        # For each stop, note potential transfer routes and their arrival times.
        min_time = stops[0].arrival_time - time_to_prev
        max_time = stops[-1].departure_time + time_to_next
        transfer_stop_times = {}
        for route in all_routes:
            stops_to_test = []
            if route.current_stop is not None:
                stops_to_test.append(route.current_stop)
            if route.next_stops is not None:
                stops_to_test += route.next_stops
            for stop in stops_to_test:
                if int(stop.location.label) in all_stops and stop.arrival_time > min_time and stop.arrival_time < max_time:
                    if int(stop.location.label) not in transfer_stop_times:
                        transfer_stop_times[int(stop.location.label)] = []
                    current_stop_arrival_time_estimation = self.get_arrival_time_estimation(route, stop, type_transfer_arrival_time)
                    interval = 1800 # default interval is 30 minutes
                    next_route_id = next_vehicles[route.vehicle.id] if route.vehicle.id in next_vehicles else None
                    if next_route_id is not None:
                        next_route = self.get_route_by_vehicle_id(state, next_route_id)
                        next_route_stop = None
                        if next_route.current_stop is not None and next_route.current_stop.location.label == stop.location.label:
                            next_route_stop = next_route.current_stop
                        elif next_route.next_stops is not None:
                            next_route_stops = [stop for stop in next_route.next_stops if stop.location.label == stop.location.label]
                            next_route_stop = next_route_stops[0] if len(next_route_stops) > 0 else None
                        if next_route_stop is not None:
                            next_route_stop_arrival_time_estimation = self.get_arrival_time_estimation(next_route, next_route_stop, type_transfer_arrival_time)
                            interval = next_route_stop_arrival_time_estimation - current_stop_arrival_time_estimation
                    transfer_stop_times[int(stop.location.label)].append((current_stop_arrival_time_estimation, route.vehicle.route_name, interval))
        return transfer_stop_times
    
    def get_arrival_time_estimation(self, route, stop, type_transfer_arrival_time):
        """Get the arrival time estimation for a transfer at a stop.
        Inputs:
            - route: Route object, the route.
            - stop: Stop object, the stop.
            - type_transfer_arrival_time: int, the type of transfer arrival time generation to consider.
        Outputs:
            - arrival_time_estimation: int, the arrival time estimation for the transfer at the stop."""
        if type_transfer_arrival_time == 2: # real
            return stop.arrival_time
        
        if route.previous_stops == []: # the bus has not left the depot yet
            return stop.planned_arrival_time
        
        if route.current_stop is not None: 
            current_delay = route.current_stop.arrival_time - route.current_stop.planned_arrival_time
            return stop.planned_arrival_time + current_delay
        
        last_visited_stop = route.previous_stops[-1]
        current_delay = last_visited_stop.arrival_time - last_visited_stop.planned_arrival_time
        return stop.planned_arrival_time + current_delay
    
    def allow_tactics_at_stops(self, state, transfer_times):
        """
        This function returns the last stop at which tactics are allowed.
        Inputs:
            - state: State object, the current state of the environment.
            - transfer_times: dict, the arrival times of the transfers at the stops.
              The format of the dict is as follows:
              transfer_times[stop_id : int] = [(arrival_time : int, route_name : str "ligne+dir", interval : int), ...]
        Outputs:
            - last: Stop object, the last stop at which tactics are allowed."""
        stops = state.route_by_vehicle_id[state.main_line].next_stops[:self.horizon]
        if len(stops) == 0:
            return(-1)
        
        stop = stops[0]
        normal = stop.departure_time
        tactic = stop.departure_time
        previous_departure_time = state.route_by_vehicle_id[state.main_line].previous_stops[-1].departure_time
        dwell = 0
        last = -1
        for i in range(len(stops)):
            stop = stops[i]
            travel_time = stop.arrival_time - previous_departure_time
            dwell = stop.departure_time-stop.arrival_time
            stop_id = int(stop.location.label)
            normal_time = travel_time+dwell
            if self.skip_stop and self.speedup_factor != 1:
                time_ss = travel_time
                time_sp = int(0.8*travel_time) + dwell
                time = min(time_ss, time_sp)
                tactic = tactic+time
            elif self.skip_stop: 
                time = travel_time
                tactic = tactic+time
            elif self.speedup_factor != 1:
                time = int(0.8*travel_time) + dwell
                tactic = tactic+time
            normal = normal+normal_time
            if stop_id in transfer_times:
                for (time, route_name, interval) in transfer_times[stop_id]:
                    if normal > time and tactic <= time: #tactics can turn an impossible transfer into a possible one
                        last = stop
        return(last)
    
    def create_tactics_dict(self, last_stop):
        """
        This function creates a dictionary saving data on tactics for all scenarios of the Regret algorithm.
        Inputs:
            - last_stop: Stop object, the last stop at which tactics are allowed.
        Outputs:
            - T: dict, the dictionary saving data on tactics for all scenarios of the Regret algorithm."""
        T={}
        ss = self.skip_stop
        sp = self.speedup_factor
        T['h_hp'] = 0
        T['none'] = 0
        T['h_t'] = {}
        T['h_t'][0] = 0
        T['h_t'][1] = []
        if last_stop == -1:
            return(T)
        if ss == True: 
            T['ss'] = 0
        if sp != 1:  
            T['sp'] = 0
            T['sp_hp'] = 0
            T['sp_t'] = {}
            T['sp_t'][0] = 0
            T['sp_t'][1] = []
        return(T)
    
    def Generate_scenario(self, 
                          main_route : Route,
                          next_route : Route,
                          stops : list,
                          next_stops : list,
                          last_stop : Stop,
                          transfer_times : dict):
        """"
        This function generates a scenario for the regret algorithm.

        Inputs: 
        main_route: Route object, the main line route.
        next_route: Route object, the next main line route.
        stops: list, the stops to consider on the main_route.
        next_stops: list, the stops to consider on the next_route.
        last_stop: Stop object, the last stop at which tactics are allowed.
        transfer_times: dict, the arrival times of the transfers at the stops.
            - The format is as follows:
                transfer_times[trip_id : str][stop_id : int] = [(arrival_time : int, route_name :str "ligne+dir", interval : int), ...]

        Outputs:
        - bus_trips: dict, the trips on the main and next routes.
            - The format is as follows:
                bus_trips[trip_id : str] = [Stop1, Stop2, ...]
        - transfers: dict, the transfers at the stops.
            - The format is as follows:
                transfers[trip_id : str][stop_id : int]['boarding'/'alighting'] = [(arrival_time : int, nbr_passengers : int, interval : int), ...]
        """
        transfers = {}
        bus_trips = {}
        prev_stop = main_route.previous_stops[-1] if main_route.previous_stops != [] else None
        bus_trips[main_route.vehicle.id], transfers[main_route.vehicle.id] = self.generate_bus_trip(stops, prev_stop, transfer_times[main_route.vehicle.id], last_stop)
        next_route_prev_stop = next_route.previous_stops[-1] if next_route.previous_stops != [] else None
        bus_trips[next_route.vehicle.id], transfers[next_route.vehicle.id] = self.generate_bus_trip(next_stops, next_route_prev_stop, transfer_times[next_route.vehicle.id])
        return (bus_trips, transfers)

    def get_and_cluster_data(self, route_name :str):
        """
        Get historical data for a route and cluster it.
        Inputs:
            route_name: name of the route
        Outputs:
            stop_to_stop_pairs: dictionary of stop-to-stop pairs
            headways_between_buses: headways between buses
            dwells: dwell times at stops
            boarding: number boarding passengers at stops
            alighting: number of alighting passengers at stops
            transfers_boarding: number of boarding transferring passengers at stops
            transfers_alighting: number of alighting transferring passengers at stops
            TravelTimeClusters: clusters of travel times between stops
            DwellClusters: clusters of dwell times at stops
            Headways: clusters of headways between buses
            Boarding: clusters of boarding passengers at stops
            Alighting: clusters of alighting passengers at stops
            TBoarding: clusters of boarding transferring passengers at stops
            TAlighting: clusters of alighting transferring passengers at stops
        """
        pathtofile = os.path.join("data", "fixed_line", "gtfs", "route_data")

        # Get historical data for the route
        stop_to_stop_pairs, dwells = self.get_route_and_stop_historical_data(route_name, pathtofile=pathtofile)
        boarding, alighting, transfers_boarding, transfers_alighting = self.get_passenger_historical_data(route_name, pathtofile=pathtofile)

        # Get stop data
        completename = os.path.join(pathtofile, 'route_stops_' + route_name + '_month.txt')
        alltype = np.dtype([('f0','i8'),('f1','i8'),('f2','f8')]) #stop_id, sequence, distance
        stops = np.genfromtxt(completename, delimiter=',', dtype=alltype, usecols = [0,1,2], names=True)

        # Cluster historical data
        # Headways = self.cluster_bus_headways(headways_between_buses)
        TravelTimes = self.cluster_travel_times_between_stops(stops, stop_to_stop_pairs)
        Dwells = self.cluster_data_at_stops(stops, dwells)
        Boarding = self.cluster_data_at_stops(stops, boarding)
        Alighting = self.cluster_data_at_stops(stops, alighting)
        TBoarding = self.cluster_data_at_stops(stops, transfers_boarding)
        TAlighting = self.cluster_data_at_stops(stops, transfers_alighting)

        return (stop_to_stop_pairs,
                # headways_between_buses,
                dwells,
                boarding, alighting, 
                transfers_boarding, transfers_alighting, 
                TravelTimes, Dwells, 
                # Headways,
                Boarding, Alighting, 
                TBoarding, TAlighting)

    def get_route_and_stop_historical_data(self, route_name, pathtofile):
        """ 
        Get historical data for a route and cluster it.
        Inputs:
            - route_name: name of the route
            - pathtofile: path to the file containing the data
        Outputs:
            - pairs_dict: dictionary of stop-to-stop travel time pairs
            #- frequence: frequency of the route
            - dwells_dict: dwell times at stops for the route"""
        # completename_frequence = os.path.join(pathtofile, route_name + "_frequence_month.csv")
        # alltype=np.dtype([('f0', 'i8'), ('f1', 'i8'), ('f2', 'i8')])
        # frequence=np.genfromtxt(completename_frequence, delimiter=",", dtype=alltype , usecols = [0,1,2])
        # new_frequence=[]
        # for intervalle in frequence:
        #     new_frequence.append([intervalle[1]],)
        # new_frequence=np.array(new_frequence)

        completename_dwells = os.path.join(pathtofile, route_name + "_dwell_times_month.csv")
        dwells_dict = self.create_data_dict(completename_dwells, passengers = False)
        
        completename_pairs = os.path.join( pathtofile, route_name + "_travel_times_month.csv")
        alltype = np.dtype([('f0', 'i8'), ('f1', 'i8'), ('f2', 'i8'), ('f3', 'i8')])
        pairs = np.genfromtxt(completename_pairs, delimiter = ',', dtype = alltype, usecols = [0,1,2,3])
        pairs_dict = {}
        headers = list(set([(x[0],x[1]) for x in pairs]))
        for (o,d) in headers:
            pairs_dict[(o,d)]=[]
        for x in pairs:
            if x[2]<0: 
                print('Travel time is negative...', x[2])
            else: 
                pairs_dict[(x[0],x[1])].append([x[2], x[3]],) # [travel_time, event_time]
        for key in pairs_dict:
            pairs_dict[key] = np.array(pairs_dict[key])
        return(pairs_dict,
            #    new_frequence, 
               dwells_dict)

    def get_passenger_historical_data(self, route_name, pathtofile):
        """
        This funciton gets historical data for passengers from saved files.
        Inputs:
            - route_name: name of the route
            - pathtofile: path to the file containing the data
        Outputs:
            - m_dict: dictionary of boarding passengers
            - d_dict: dictionary of alighting passengers
            - tm_dict: dictionary of boarding transferring passengers
            - td_dict: dictionary of alighting transferring passengers
            The format is as follows: 
            dict[stop_id : int] = np.array([[duration/quantity : int, event_time : int], ...])"""
        # Boarding passengers
        completename_montants = os.path.join(pathtofile, route_name + "_boarding_passengers_month.csv")
        m_dict = self.create_data_dict(completename_montants)

        # Alighting passengers
        completename_d = os.path.join(pathtofile, route_name + "_alighting_passengers_month.csv")
        d_dict = self.create_data_dict(completename_d)

        # Boarding transferring passengers
        completename_tmontants=os.path.join(pathtofile, route_name + "_transfer_boarding_passengers_month.csv")
        tm_dict = self.create_data_dict(completename_tmontants)

        # Alighting transferring passengers
        completename_td=os.path.join(pathtofile, route_name + "_transfer_alighting_passengers_month.csv")
        td_dict = self.create_data_dict(completename_td)
        return(m_dict, d_dict, tm_dict, td_dict)

    def create_data_dict(self, completename, passengers = True):
        """
        This function creates a dictionary from a file containing data.
        Inputs:
            - completename: name of the file containing the data
            - passengers: boolean, whether the data is for passengers or not
        Outputs:
            - data_dict: dictionary of data
            The format is as follows: 
            dict[stop_id : int] = np.array([[duration/quantity : int, event_time : int], ...])"""
        alltype = np.dtype([('f0','i8'),('f1','i8'),('f2','i8')]) #stop_id, duration/quantity, event_time
        data = np.genfromtxt(completename, delimiter = ',', dtype = alltype, usecols = [0,1,2])
        data_dict = {}
        headers = np.unique([x[0] for x in data])
        for stop in headers:
            data_dict[stop] = []
        for row in data: 
            data_dict[row[0]].append([row[1], row[2]],)
        empty=[]
        for key in data_dict: 
            if data_dict[key] == []:
                empty.append(key)
        if passengers: 
            for key in empty:
                data_dict[key].append([0, 0],)
        else:
            for key in empty:
                data_dict.pop(key, None)
        for key in data_dict:
            data_dict[key] = np.array(data_dict[key])
        return(data_dict)
    
    def cluster_travel_times_between_stops(self,
                                           stops : np.array,
                                           consecutive_stop_pairs : dict):
        """
        This function clusters travel times between stops.
        Inputs:
            - stops: np.array, shape (n,3)
            - consecutive_stop_pairs: dict
        Outputs:
            - KClusters: dict
            The format is as follows:
            dict[(stop_id1, stop_id2)] = (C, clusters)"""
        count=0
        KClusters={}
        for i in range(len(stops)-1):
            current_stop_id = stops[i][0]
            next_stop_id = stops[i+1][0]
            if (current_stop_id, next_stop_id) in consecutive_stop_pairs:
                pair = (current_stop_id, next_stop_id)
                KClusters[pair]=self.cluster_data(consecutive_stop_pairs[pair])
            else:
                count+=1
        return(KClusters)
    
    def cluster_data_at_stops(self,
                              stops : np.array,
                              data_at_stops : dict):
        """
        This function clusters data at stops.
        Inputs:
            - stops: np.array, shape (n,3)
            - data_at_stops: dict
            The format is as follows:
            dict[stop_id : int] = np.array([[duration/quantity : int, event_time : int], ...])
        Outputs:
            - KClusters: dict
            The format is as follows:
            dict[stop_id : int] = (C, clusters"""
        # count = 0
        KClusters={}
        for x in stops:
            stop_id = x[0]
            if stop_id in data_at_stops:
                KClusters[stop_id] = self.cluster_data(data_at_stops[stop_id])
            # else:
            #     count+=1
        return(KClusters)
    
    def cluster_data(self, U):
        """ Clusters the data in U using the k-means algorithm.
        Inputs:
            - U: np.array, shape (n,m)
        Outputs:
            - C: np.array, shape (k,m)
            - clusters: np.array, shape (n,)
        """
        k=3 # Number of clusters
        (n,m)=U.shape
        if n<k:
            C, clusters = self.kmeans(U, n) # If there are less than k points, we cluster them in n clusters
        else: 
            C, clusters = self.kmeans(U, k)
        return (C, clusters)

    def kmeans(self, U,k): # U is a matrix with n rows and m columns, m>k. n points, m coordinates.
        """Performs the k-means algorithm on a set of points U in R^m.
        Returns the k clusters and the indices of the clusters to which each point belongs.
        Inputs: 
            - U: np.array, shape (n,m)
            - k: int
        Outputs:
            - C: np.array, shape (k,m)
            - clusters: np.array, shape (n,)
        """
        (n,m) = U.shape
        tmp = np.random.choice(range(n), k, replace=False) # Assigns k random points to the centers of the clusters
        C = np.zeros((k, m)) # k points with m coordinates
        for i in np.arange(k):
            C[i] = U[tmp[i]] # C[i] is the center of the i-th cluster
        C_old = np.zeros(C.shape) # Initialized to zeros and updated at each iteration
        clusters = np.zeros(n) # n points, each point is assigned to a cluster: cluster[n] = index of the cluster
        diff = self.dist(C, C_old, None) # Difference between the old and new centers
        while diff != 0: # Stops when the centers do not change anymore
            for i in range(n):
                distances = np.zeros(k)
                for j in range(k):
                    distances[j] = self.dist(U[i][1], C[j][1], None) # distance between U[i] and each center of cluster, distance has 1 value which is the time of event
                clusters[i] = np.argmin(distances) # assigns the point U[i] to the closest center
            C_old = copy.deepcopy(C) # updates the old centers
            for i in range(k):
                points = [U[j] for j in range(n) if clusters[j] == i]
                if len(points) > 0:
                    C[i] = np.mean(points, axis = 0) # updates the center of the cluster
            diff = self.dist(C, C_old, None)
        return(C, clusters)

    def dist(self, a, b, ax=1):
        """Calculates the distance between two points in a space of dimension ax."""
        return np.linalg.norm(a - b, axis=ax)
    
    def get_headway(self, main_route, stops_second):
        """Calculates the headway between the main route and the next route.
        Inputs:
            - main_route: Route object, the main route.
            - stops_second: list, the stops of the next route.
        Outputs:
            - headway: int, the headway between the main route and the next route."""
        headway_at_stop_id = stops_second[0].location.label
        next_time = stops_second[0].arrival_time
        previous_stops = main_route.previous_stops
        for stop in previous_stops:
            if stop.location.label == headway_at_stop_id:
                previous_time = stop.arrival_time
                return next_time - previous_time
            
        if main_route.current_stop is not None:
            if main_route.current_stop.location.label == headway_at_stop_id:
                previous_time = main_route.current_stop.arrival_time
                return next_time - previous_time
        
        if main_route.next_stops != []:
            for stop in main_route.next_stops:
                if stop.location.label == headway_at_stop_id:
                    previous_time = stop.arrival_time
                    return next_time - previous_time
    
    def generate_bus_trip(self, stops, prev_stop, transfer_times, last_stop = -1, initial_flow = 0):
        """Generates a trip for a route with stops and previous time prev_time.
        Inputs:
            - stops: list of Stops
            - prev_stop: Stop
            - transfer_times: dict
            - last_stop: Stop, the last stop at which tactics are allowed
            - initial_flow: int, the initial flow of passengers
        Outputs:
            - new_stops: list of Stops
            - transfers: dict
                The format is as follows:
                transfers[stop_id : int]['boarding'/'alighting'] = [(arrival_time : int, nbr_passengers : int, interval : int), ...]"""
        new_stops =[]
        transfers = {}
        prev_time = prev_stop.departure_time if prev_stop != None else stops[0].arrival_time -1
        for stop in stops:
            dwell_time = self.generate_dwell_time(stop, prev_time)
            travel_time = self.generate_travel_time(prev_stop, stop, prev_time)
            nbr_alighting = self.generate_alighting(stop, prev_time, initial_flow)
            initial_flow -= nbr_alighting
            if int(stop.location.label) in transfer_times and (last_stop == -1 or stop.cumulative_distance <= last_stop.cumulative_distance):
                nbr_transferring_alighting = self.generate_transferring_alighting(stop, prev_time, initial_flow)
                initial_flow -= nbr_transferring_alighting
                nbr_transferring_boarding = self.generate_transferring_boarding(stop, prev_time)
                initial_flow += nbr_transferring_boarding
            else:
                nbr_transferring_alighting = 0
                nbr_transferring_boarding = 0
            nbr_boarding = self.generate_boarding(stop, prev_time)
            initial_flow += nbr_boarding
            transfers_at_stop = self.generate_transfers(stop, nbr_transferring_boarding, nbr_transferring_alighting, transfer_times)
            new_stop = Stop(arrival_time = prev_time + travel_time, 
                            departure_time = prev_time + travel_time + dwell_time,
                            location = stop.location,
                            cumulative_distance = stop.cumulative_distance,
                            min_departure_time = stop.min_departure_time,
                            planned_arrival_time = stop.planned_arrival_time,
                            planned_departure_time_from_origin = stop.planned_departure_time_from_origin)
            new_stop.passengers_to_board_int = nbr_boarding
            new_stop.passengers_to_alight_int = nbr_alighting
            transfers[int(new_stop.location.label)] = transfers_at_stop
            new_stops.append(new_stop)
            prev_time = prev_time + travel_time + dwell_time
            prev_stop = new_stop
        return new_stops, transfers
    
    def generate_dwell_time(self, stop, time):
        """Generates a dwell time for a stop.
        Inputs:
            - stop: Stop    
        Outputs:
            - dwell_time: int
            
        Parameters: 
        type_dwell: 
            0: sample in cluster
            1: cluster mean
            2: real value
            3: planned value
        """
        type_dwell = self.algo_parameters['type_dwell']
        if type_dwell == 2:
            # print('Real dwell time for stop ', stop.location.label, ' = ', stop.departure_time - stop.arrival_time)
            return stop.departure_time - stop.arrival_time
        
        route_name = self.route_name
        Data = self.Data[route_name]
        stop_to_stop_pairs, dwells, boarding, alighting, transfers_boarding, transfers_alighting, TravelTimes, Dwells, Boarding, Alighting, TBoarding, TAlighting = Data
        key = int(stop.location.label)
        clusters_pair = Dwells[key]
        values = dwells[key]
        dwell_time = self.get_value_from_clusters(clusters_pair, values, time, type_dwell)
        return (dwell_time)
    
    def get_value_from_clusters(self, clusters_pair, values, time, type_generation):
        """Generate a value from clusters using a specific generation type.
        Inputs:
            - clusters_pair = (C, clusters): tuple of clusters and cluster indices
            - values: np.array, shape (n,2), values from which to generate the value
            - time: int, time of occurence for the event
            - type_generation: int, the type of generation (real, mean, random, planned)
        Outputs:
            - value: int"""
        (C, clusters) = clusters_pair
        (a,b) = values.shape
        distance = np.zeros(a)
        for i in range(len(C)):
            distance[i] = abs(C[i][1] - time)
        cluster_index = np.argmin(distance)
        indices = np.array([j for j in range(a) if clusters[j] == cluster_index])
        if type_generation == 0: 
            index = int(random.choice(indices))
            value = values[index][0]
        elif type_generation == 1: 
            tmp = mean([values[index][0] for index in indices])
            value = random.choice([math.floor(tmp), math.ceil(tmp)])
        return (value)
    
    def generate_travel_time(self, stop1, stop2, time):
        """Generates a travel time between two stops.
        Inputs:
            - stop1: Stop
            - stop2: Stop
            - time: int, time of occurrence of the event
        Outputs:
            - travel_time: int
        """
        if stop1 is None:
            return 1
        type_travel_time = self.algo_parameters['type_travel_time']
        if type_travel_time == 2:
            # print('Real travel time between stops ', stop1.location.label, ' and ', stop2.location.label, ' = ', stop2.arrival_time - stop1.departure_time)
            return stop2.arrival_time - stop1.departure_time
        
        route_name = self.route_name
        Data = self.Data[route_name]
        stop_to_stop_pairs, dwells, boarding, alighting, transfers_boarding, transfers_alighting, TravelTimes, Dwells, Boarding, Alighting, TBoarding, TAlighting = Data
        key = (int(stop1.location.label), int(stop2.location.label))
        clusters_pair = TravelTimes[key]
        values = stop_to_stop_pairs[key]
        travel_time = self.get_value_from_clusters(clusters_pair, values, time, type_travel_time)
        return (travel_time)

    def generate_boarding(self, stop, time):
        """Generates the number of boarding passengers at a stop.
        Inputs:
            - stop: Stop
            - time: int, time of occurrence of the event
        Outputs:
            - boarding: int
        """
        type_boarding = self.algo_parameters['type_boarding']
        if type_boarding == 2:
            count = 0
            passengers_to_board = stop.passengers_to_board
            for trip in passengers_to_board:
                first_leg = trip.next_legs[0] # We are looking for boarding without a transfer.
                if first_leg.origin.label == stop.location.label and trip.current_leg == None and trip.previous_legs == []:
                    count += 1
            return count
        
        route_name = self.route_name
        Data = self.Data[route_name]
        stop_to_stop_pairs, dwells, boarding, alighting, transfers_boarding, transfers_alighting, TravelTimes, Dwells, Boarding, Alighting, TBoarding, TAlighting = Data
        key = int(stop.location.label)
        clusters_pair = Boarding[key]
        values = boarding[key]
        boarding = self.get_value_from_clusters(clusters_pair, values, time, type_boarding)
        return (boarding)  
    
    def generate_alighting(self, stop, time, initial_flow):
        """Generates the number of alighting passengers at a stop.
        Inputs:
            - stop: Stop
            - time: int, time of occurrence of the event
        Outputs:
            - alighting: int
        """
        type_alighting = self.algo_parameters['type_alighting']
        if type_alighting == 2:
            count = 0 
            passengers_to_alight = stop.passengers_to_alight
            # We don't count transferring passengers here
            for trip in passengers_to_alight:
                if (trip.current_leg != None and trip.next_legs == [] and trip.current_leg.destination.label == stop.location.label):
                    count += 1
                if (trip.current_leg == None and trip.next_legs != [] and trip.next_legs[-1].destination.label == stop.location.label):
                        count += 1
            if count <= initial_flow:
                return count
            else:
                return initial_flow
        
        route_name = self.route_name
        Data = self.Data[route_name]
        stop_to_stop_pairs, dwells, boarding, alighting, transfers_boarding, transfers_alighting, TravelTimes, Dwells, Boarding, Alighting, TBoarding, TAlighting = Data
        key = int(stop.location.label)
        clusters_pair = Alighting[key]
        values = alighting[key]
        alighting = self.get_value_from_clusters(clusters_pair, values, time, type_alighting)
        if alighting <= initial_flow:
            return alighting
        else:
            return initial_flow
    
    def generate_transferring_boarding(self, stop, time):
        """Generates the number of boarding transferring passengers at a stop.
        Inputs:
            - stop: Stop
            - time: int, time of occurrence of the event
        Outputs:
            - boarding: int
        """
        type_boarding_transfer = self.algo_parameters['type_boarding_transfer']
        if type_boarding_transfer == 2:
            count = 0
            passengers_to_board = stop.passengers_to_board
            for trip in passengers_to_board:
                if (trip.current_leg != None and trip.next_legs != [] and trip.next_legs[0].origin.label == stop.location.label):
                    count += 1
                if (trip.current_leg is None):
                    if (trip.previous_legs != [] and trip.next_legs[0].origin.label == stop.location.label):
                        count += 1
                    if (trip.previous_legs == []):
                        i = 0 
                        for leg in trip.next_legs:
                            if leg.origin.label == stop.location.label and i > 0:
                                count += 1
                                break
                            i += 1
            return count
        
        route_name = self.route_name
        Data = self.Data[route_name]
        stop_to_stop_pairs, dwells, boarding, alighting, transfers_boarding, transfers_alighting, TravelTimes, Dwells, Boarding, Alighting, TBoarding, TAlighting = Data
        key = int(stop.location.label)
        clusters_pair = TBoarding[key]
        values = transfers_boarding[key]
        transferring_boarding = self.get_value_from_clusters(clusters_pair, values, time, type_boarding_transfer)
        return (transferring_boarding)

    def generate_transferring_alighting(self, stop, time, initial_flow):
        """Generates the number of alighting transferring passengers at a stop.
        Inputs:
            - stop: Stop
            - time: int, time of occurrence of the event
        Outputs:
            - alighting: int
        """
        type_alighting_transfer = self.algo_parameters['type_alighting_transfer']
        if type_alighting_transfer == 2:
            count = 0
            passengers_to_alight = stop.passengers_to_alight
            for trip in passengers_to_alight: # We want transfers only 
                if (trip.current_leg != None and trip.next_legs != [] and trip.current_leg.destination.label == stop.location.label):
                    count += 1
                if (trip.current_leg is None):
                    if (trip.next_legs != []):
                        i = 0
                        for leg in trip.next_legs:
                            if leg.destination.label == stop.location.label and i < len(trip.next_legs) - 1:
                                count += 1
                                break
                            i += 1
            if count <= initial_flow:
                return count
            return initial_flow
        
        route_name = self.route_name
        Data = self.Data[route_name]
        stop_to_stop_pairs, dwells, boarding, alighting, transfers_boarding, transfers_alighting, TravelTimes, Dwells, Boarding, Alighting, TBoarding, TAlighting = Data
        key = int(stop.location.label)
        clusters_pair = TAlighting[key]
        values = transfers_alighting[key]
        transferring_alighting = self.get_value_from_clusters(clusters_pair, values, time, type_alighting_transfer)
        if transferring_alighting <= initial_flow:
            return transferring_alighting
        return (initial_flow)

    def generate_transfers(self, stop, nbr_boarding, nbr_alighting, transfer_times):
        """Generates the transfers at a stop. This makes a link between potential transferring buses
        and the generated passengers.
        Inputs:
            - stop: Stop
            - nbr_boarding: int number of transferring boarding passengers
            - nbr_alighting: int number of transferring alighting passengers
            - transfer_times: dict containing the transfer times for all potential transferring buses at each stop
        Outputs:
            - transfers: dict containing the transfers at the stop
                The format is as follows:
                transfers['boarding'/'alighting'] = [(arrival_time : int, nbr_passengers : int, interval : int), ...]"""
        if nbr_alighting + nbr_boarding == 0 or \
           int(stop.location.label) not in transfer_times:
            transfers = {}
            transfers['boarding'] = []
            transfers['alighting'] = []
            return transfers
        
        transfers = {}
        transfers['boarding'] = []
        transfers['alighting'] = []
        stop_id = int(stop.location.label)
        tmp = []
        for i in range(nbr_boarding):
            transfer_time = random.choice(transfer_times[stop_id])[0]
            tmp.append(transfer_time)
            # count occurrences of transfer_time in transfers['boarding']
            for item, count in Counter(tmp).items():
                transfers['boarding'].append((item, count, 0))
        tmp =[]
        for i in range(nbr_alighting):
            transfer_data = random.choice(transfer_times[stop_id])
            transfer_time = transfer_data[0]
            transfer_interval = transfer_data[2]
            tmp.append((transfer_time, transfer_interval))
            for item, count in Counter(tmp).items():
                transfers['alighting'].append((item[0], count, item[1]))
        return transfers
    
    def choose_tactic(self, T, last_stop):
        """ Chooses the tactic with the lowest regret in the tactics dictionary T.
        Inputs:
            - T: dict, the tactics dictionary
            - last_stop: Stop, the last stop at which tactics are allowed
        Outputs:
            - time_max: int, the latest time at which to depart from the stop after holding
            - hold: int, -1 if no hold time
                        0 if wait for planned time
                        1 if waiting for a transfer
            - speedup: int, 0 if no speedup, 1 if speedup
            - ss: int, 0 if no skip-stop, 1 if skip-stop"""
        time_max=-1
        # We use a hierarchy of tactics in case two tactics have the same regret: None, H_HP, SP, SP_HP, H_T, SP_T, SS
        ss = self.skip_stop
        sp = self.speedup_factor
        if sp == 1: 
            T['sp'] = 1000000
            T['sp_hp'] = 1000000
            T['sp_t'] = [1000000, 0]
        if ss == False:  
            T['ss'] = 1000000
        if last_stop == -1:
            T['sp'] = 1000000
            T['sp_hp'] = 1000000
            T['sp_t'] = [1000000, 0]
            T['ss'] = 1000000
        all_tactic_regrets = [ T['none'], T['h_hp'], T['sp'], T['sp_hp'], T['h_t'][0], T['sp_t'][0], T['ss']]
        index = np.argmin(all_tactic_regrets)
        ss = 0
        speedup = 0
        hold = -1
        if index == 6:
            ss = 1
        if index in [2, 3, 5]:
            sp = 1
        if index in [1, 3]:
            hold = 0
        if index in [4, 5]:
            hold = 1
            if index == 4:
                time_max=mean(T['h_t'][1])
            else:
                time_max=mean(T['sp_t'][1])
        return(time_max, hold, speedup, ss)
    
    def update_tactics_dict_regret(self,
                                   tactic_regrets_dict : dict,
                                   max_departure_time : int, hold :int, speedup: int, skip_stop: int,
                                   bus_flows_in_solution : dict,
                                   route : Route,
                                   next_route : Route,
                                   bus_trips : dict,
                                   transfers : dict,
                                   optimal_value: int,
                                   prev_times : dict):
        """Updates the tactics dictionary T given the optimal tactic, and calculates the regret of all other tactics.
        Inputs:
            - T: dict, the tactics dictionary
            - max_departure_time: int, the latest time at which to depart from the stop after holding
            - hold: int, -1 if no hold time
                         0 if wait for planned time
                         1 if waiting for a transfer
            - speedup: int, 0 if no speedup, 1 if speedup
            - skip_stop: int, 0 if no skip-stop, 1 if skip-stop
            - bus_flows_in_solution: dict, the bus flows in the solution, shows the path of each bus in the graph.
            - route: Route, the main line route
            - next_route: Route, the next main line route
            - bus_trips: dict, the generated trips on the main and next routes
            - transfers: dict, the transfers at the stops in the genrated trips
            - optimal_value: int, the optimal cost when using the optimal tactic
            - prev_times: dict, the departure times from the last visited stop for each bus
        Outputs:
            - T: dict, the updated tactics dictionary
            """
        # Get parameters
        skip_stop_is_allowed = self.skip_stop
        speedup_factor = self.speedup_factor
        trip_id = route.vehicle.id
        next_trip_id = next_route.vehicle.id
        stop_id = int(route.next_stops[0].location.label)
        initial_flows = {}
        initial_flows[trip_id] = int(len(route.onboard_legs))
        initial_flows[next_trip_id] = int(len(next_route.onboard_legs))

        # List of all tactics
        all = ['none', 'h_hp', 'h_t']
        if skip_stop_is_allowed == True: 
            all.append('ss')
        if speedup_factor != 1: 
            all.append('sp')
            all.append('sp_hp')
            all.append('sp_t')

        # Find optimal tactic and remove it from the list of tactics
        if skip_stop==1: 
            all.remove('ss')
        elif speedup == 1: 
            if hold == -1:
                all.remove('sp')
            elif hold == 0: 
                all.remove('sp_hp')
            else: 
                all.remove('sp_t')
        else: 
            if hold == -1: 
                all.remove('none')
            elif hold == 0:
                all.remove('h_hp')
            else: 
                all.remove('h_t')
        tactics = get_all_tactics_used_in_solution(bus_flows_in_solution, trip_id, next_trip_id)
        regret_bus_trips = self.create_stops_list_for_all_non_optimal_tactics(bus_trips, transfers, tactics, stop_id, trip_id, max_departure_time, all, prev_times)
        for tactic in all:
            tactic_bus_trips = {}
            tactic_bus_trips[trip_id] = regret_bus_trips[tactic][trip_id]
            tactic_bus_trips[next_trip_id] = regret_bus_trips[next_trip_id]
            regret = self.get_tactic_regret(stop_id, tactic_bus_trips, transfers, prev_times, initial_flows, optimal_value)
            if tactic == 'sp_t' or tactic == 'h_t':
                tactic_regrets_dict[tactic][0] += regret
                tactic_regrets_dict[tactic][1].append(tactic_bus_trips[trip_id][0].departure_time)
            else: 
                tactic_regrets_dict[tactic] += regret
        return(tactic_regrets_dict)
    
    def get_solution_for_graph(self, G_generated: Graph, stop_id : int, trip_id: str): 
        """
        This function generates the solution for a graph.
        Given a graph G_generated, a stop_id and a trip_id, it first converts the graph to a model format,
        then builds and solves the corresponding arc-flow model, and finally extracts the tactics used at the stop with stop_id for the bus trip_id from the solution.
        Inputs:
            - G_generated: Graph, the graph generated with data from the generated scenario
            - stop_id: int, the stop id
            - trip_id: str, the trip id
        Outputs:
            - max_departure_time: int, the latest time at which to depart from the stop after holding
            - hold: int, the hold time
            - speedup: int, 0 if no speedup, 1 if speedup
            - skip_stop: int, 0 if no skip-stop, 1 if skip-stop
            - bus_flows: dict, the bus flows in the solution, shows the path of each bus in the graph.
            - optimal_value: int, the value of the objective function when using the optimal tactic
            - runtime: int, the runtime of the optimization"""
        optimal_value, bus_flows, display_flows, runtime = G_generated.build_and_solve_model_from_graph("GenGraph",
                                                                                         verbose = False, 
                                                                                         out_of_bus_price = self.general_parameters["out_of_bus_price"])
        max_departure_time, hold, speedup, skip_stop = extract_tactics_from_solution(bus_flows, stop_id, trip_id)
        return(max_departure_time, hold, speedup, skip_stop, bus_flows, optimal_value, runtime)
    
    def create_stops_list_for_all_non_optimal_tactics(self, 
                                                      bus_trips : dict,
                                                      transfers : dict,
                                                      tactics : dict,
                                                      stop_id, trip_id,
                                                      max_departure_time: int,
                                                      all,
                                                      prev_times: dict):
        """
        This function creates bus trips with a list of stops for each non-optimal tactic.
        Each stop has an arrival and departure time.

        Inputs:
            - bus_trips: dictionary of bus trips containing the data on the two trips' stops, travel times, dwell times, number of boarding/alighting passengers etc.
                The format of the bus_trips dictionary is as follows:
                bus_trips[trip_id] = [stop1 : Stop, stop2: Stop,  ...]
            - transfers: dictionary containing the transfer data for passengers transferring on the two bus trips: transfer time, number of transfers, stops, etc.
                The format of the transfers dictionary is as follows:
                transfers[trip_id][stop_id]['boarding'/'alighting'] = [(transfer_time : int, nbr_passengers : int, interval : int), ...]
            - tactics: dictionary containing the tactics used at each stop for the two bus trips. The format of the tactics dictionary is as follows:
                tactics[trip_id][stop_id] = (tactic : str, hold_time : int)
            - stop_id: the id of the first stop
            - trip_id: the id of the main/first bus trip
            - max_departure_time: the latest departure time of the bus from the stop after holding time
            - all: list of all possible tactics (excluding the optimal tactic)
            - prev_times: dictionary containing the departure time from the last visited stop for each bus trip
        Outputs:
            - new_stops: dictionary containing the stops for each non-optimal tactic for the bus trip with trip_id
            """
        speedup_factor = self.speedup_factor
        new_stops = {}
        if stop_id in transfers[trip_id] and len(transfers[trip_id][stop_id]['boarding']+transfers[trip_id][stop_id]['alighting'])>0:
            # final_transfer_time = max([transfer_time for (transfer_time, nbr_passengers) in transfers[trip_id][stop_id]['boarding']+transfers[trip_id][stop_id]['alighting'] if transfer_time < bus_trips[trip_id][0].arrival_time + 120])
            final_transfer_time = max([transfer_time for (transfer_time, nbr_passengers, interval) in transfers[trip_id][stop_id]['boarding']+transfers[trip_id][stop_id]['alighting'] if transfer_time < max_departure_time])
        else: 
            final_transfer_time = -1
        for bus_trip in bus_trips:
            stops = bus_trips[bus_trip]
            if bus_trip == trip_id:
                new_stops[bus_trip] = {}
                for tactic in all:
                    new_stops[bus_trip][tactic] = []
                    # First stop with different tactic
                    prev_time_real = prev_times[bus_trip]
                    prev_time_new = prev_times[bus_trip]
                    travel_time = stops[0].arrival_time - prev_time_real
                    prev_time_real = stops[0].departure_time
                    first_stop, prev_time_new = self.create_stop_using_tactic((tactic, -1), stops[0], final_transfer_time, prev_time_new, travel_time, speedup_factor)
                    new_stops[bus_trip][tactic].append(first_stop)
                    # All other stops
                    new_stops[bus_trip][tactic] += self.create_bus_stops_with_tactics(stops[1:], prev_time_real, prev_time_new, tactics[bus_trip], speedup_factor)
            else: 
                new_stops[bus_trip] = self.create_bus_stops_with_tactics(stops, prev_times[bus_trip], prev_times[bus_trip], tactics[bus_trip], speedup_factor)
        return(new_stops)

    def create_bus_stops_with_tactics(self,
                                      stops : List[Stop],
                                      prev_time_real : int,
                                      prev_time_new : int,
                                      tactics : dict,
                                      speedup_factor = 0.8):
        """
        This function creates a list of stops for a bus trip applying the tactics in the solution.
        These stops will be used as input to construct graphs for the regret algorithm. We apply the tactics directly to the stops
        and force the use of the graph construction without tactics.
        
        Inputs:
            - stops: list of stops for the bus trip
            - prev_time_real: the real departure time from the last visited stop
            - prev_time_new: the new departure time from the last visited stop
            - tactics: dictionary containing the tactics used at each stop for the bus trip
            - speedup_factor: the speedup factor
        Outputs:
            - new_stops: list of stops for the bus trip with the tactics applied"""
        new_stops = []
        for stop in stops:
            travel_time = stop.arrival_time - prev_time_real
            prev_time_real = stop.departure_time
            new_stop, prev_time_new = self.create_stop_using_tactic(tactics[stop.stop_id], stop, -1, prev_time_new, travel_time, speedup_factor)
            new_stops.append(new_stop)
        return(new_stops)

    def create_stop_using_tactic(self, 
                                 tactic_tuple,
                                 stop,
                                 final_transfer_time,
                                 prev_time,
                                 travel_time,
                                 speedup_factor=0.8): 
        """
        This function creates a stop with a tactic applied to it.

        Inputs:
            - tactic_tuple: tuple containing the tactic and the maximum transfer time
            - stop: the stop to which the tactic is applied
            - final_transfer_time: the final transfer time
            - prev_time: the departure time from the previous stop after the tactics were applied to it
            - travel_time: the travel time between the previous stop and the current stop
            - speedup_factor: the speedup factor
        Outputs:
            - new_stop: the new stop with the tactic applied
            - prev_time: the new departure time from the stop after the tactic was applied to it"""
        tactic = tactic_tuple[0]
        time = tactic_tuple[1]
        maximum_transfer_time = time if time != -1 else final_transfer_time
        new_stop = copy.deepcopy(stop) 
        dwell_time = stop.departure_time - stop.arrival_time
        new_stop.arrival_time = prev_time + travel_time
        new_stop.departure_time = new_stop.arrival_time + dwell_time
        if tactic == 'ss':
            new_stop.departure_time = new_stop.arrival_time
            new_stop.skip_stop = 1
        elif tactic == 'sp' or tactic == 'sp_hp' or tactic == 'sp_t':
            new_stop.speedup = 1
            travel_time = max (1, int(travel_time * speedup_factor))
            new_stop.arrival_time = prev_time + travel_time
            new_stop.departure_time = new_stop.arrival_time + dwell_time
            if tactic == 'sp_t':
                if maximum_transfer_time != -1: 
                    if new_stop.departure_time < maximum_transfer_time:
                        new_stop.departure_time = maximum_transfer_time
                else: 
                    new_stop.departure_time = new_stop.departure_time + 60
            elif tactic == 'sp_hp':
                if new_stop.departure_time < new_stop.planned_arrival_time - 60:
                    new_stop.departure_time = new_stop.planned_arrival_time - 60
        elif tactic == 'h_hp':
            if stop.departure_time < new_stop.planned_arrival_time - 60:
                new_stop.departure_time = new_stop.planned_arrival_time - 60
        elif tactic == 'h_t':
            if maximum_transfer_time != -1: 
                if new_stop.departure_time < maximum_transfer_time:
                    new_stop.departure_time = maximum_transfer_time
            else: 
                new_stop.departure_time = new_stop.arrival_time + 60
        prev_time = new_stop.departure_time
        return(new_stop, prev_time)
    
    def get_tactic_regret(self, stop_id, tactic_bus_trips, transfers, prev_times, initial_flows, optimal_value):
        """
        This function calculates the regret of a tactic given the optimal value.
        
        Inputs:
            - stop_id: int, the stop id
            - tactic_bus_trips: dict, the bus trips with the non_optimal_tactic applied to the first stop ot the main route, while all other tactics are kept the same as in the optimal solution
            - transfers: dict, the transfers at the stops in the genrated trips
            - prev_times: dict, the departure times from the last visited stop for each bus
            - initial_flows: dict, the initial flows of passengers for each bus
            - optimal_value: int, the optimal value of the objective function when using the optimal tactic
        Outputs:
            - regret: int, the regret of the tactic compared to the optimal value"""
        step = self.general_parameters["step"]
        price = self.general_parameters["price"]
        G, last_trip_id, bus_departures = build_graph_without_tactics(tactic_bus_trips, transfers, prev_times, initial_flows, times_step = step, price = price, od_dict = {})
        optimal_value_for_tactic, bus_flows, display_flows, runtime = G.build_and_solve_model_from_graph("Gen_offline"+str(stop_id),
                                                                                          verbose = False,
                                                                                          out_of_bus_price = self.general_parameters["out_of_bus_price"])
        regret = optimal_value_for_tactic-optimal_value
        if regret < 0:
            logger.warning('Negative regret value : {}...'.format(regret))
            regret = 0
        return(regret)
    