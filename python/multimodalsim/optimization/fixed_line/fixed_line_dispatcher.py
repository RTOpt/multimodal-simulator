import logging

from multimodalsim.optimization.optimization import OptimizationResult
from multimodalsim.optimization.dispatcher import OptimizedRoutePlan, Dispatcher
from multimodalsim.config.fixed_line_dispatcher_config import FixedLineDispatcherConfig
from multimodalsim.simulator.vehicle import Vehicle, Route, Stop, LabelLocation
from multimodalsim.simulator.vehicle_event import VehicleReady
from multimodalsim.simulator.request import Leg
from multimodalsim.optimization.fixed_line.graph_constructor import build_graph_with_tactics, build_graph_without_tactics,  build_and_solve_model_from_graph, convert_graph, extract_tactics_from_solution

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
        self.__Data = None
        self.__route_name = None


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
        if main_line.vehicle.route_name == 'Walking_route':
            return [], []
        self.route_name = main_line.vehicle.route_name
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
                          self.__CAPACITY, release_time, end_time, mode, route_name='Walking_route')
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
        # get stops on both routes
        stops = route.next_stops[0: self.horizon]
        last_stop_id = stops[-1].location.label
        stops_second = self.get_next_route_stops(last_stop_id, next_route)

        stop_id = stop.location.label
        bus_trip_id = route.vehicle.id
        bus_next_trip_id = next_route.vehicle.id
        #Get initial flows and previous times
        initial_flows = {}
        initial_flows[bus_trip_id] = int(len(route.onboard_legs))
        initial_flows[bus_next_trip_id] = int(len(next_route.onboard_legs))
        last_departure_times = {}
        last_departure_times[bus_trip_id] = route.previous_stops[-1].departure_time if route.previous_stops != [] else route.next_stops[0].arrival_time -1
        last_departure_times[bus_next_trip_id] = next_route.previous_stops[-1].departure_time if next_route.previous_stops != [] else next_route.next_stops[0].arrival_time -1
        

        # Estimate arrival time of transfers at stops
        transfer_times = {}
        ### A FAIRE : DEFINIR time_to_prev et time_to_next
        transfer_times[bus_trip_id] = self.get_transfer_stop_times(state = state,
                                                                stops = stops,
                                                                type_transfer_arrival_time = self.algo_parameters['type_transfer_arrival_time'],
                                                                time_to_prev=600,
                                                                time_to_next=600)
        transfer_times[bus_next_trip_id] = self.get_transfer_stop_times(state = state,
                                                                    stops = stops_second,
                                                                    type_transfer_arrival_time = self.algo_parameters['type_transfer_arrival_time'],
                                                                    time_to_prev=600,
                                                                    time_to_next=600)
        
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
                    bus_trips, transfers = self.Generate_scenario(route,
                                                                    next_route, 
                                                                    stops, 
                                                                    stops_second,
                                                                    last = last_stop,
                                                                    transfer_times=transfer_times
                                                                    )
                    
                    # Step b: Create graph from generated instance
                    G_gen = build_graph_with_tactics(bus_trips = bus_trips,
                                                    transfers = transfers,
                                                    last_departure_times = last_departure_times,
                                                    initial_flows = initial_flows,
                                                    time_step = self.general_parameters["pas"],
                                                    price = self.general_parameters["price"],
                                                    speedup_gen = self.speedup_factor,
                                                    ss_gen = self.skip_stop,
                                                    simu = True,
                                                    last_stop = int(last_stop.location.label) if last_stop != -1 else -1)
                    # Step c: Get Data on optimization results
                    prev_stop = route.previous_stops[-1] if route.previous_stops != [] else None
                    prev_stop_departure_time = prev_stop.departure_time if prev_stop != None else bus_trips[bus_trip_id][0].arrival_time -1
                    last_travel_time = bus_trips[bus_trip_id][0].arrival_time - prev_stop_departure_time
                    time_max, hold, speedup, ss, bus_flows, opt_val, runtime = self.get_gen_data(G_gen,
                                                                                                 stop_id,
                                                                                                 bus_trip_id,
                                                                                                 last_travel_time = last_travel_time)

                    # Step d: Update tactics dictionary
                    if self.algo==2: # Regret Algorithm
                        tactic_regrets_dict = self.update_tactics_dict_regret(tactic_regrets_dict,
                                                                                time_max, hold, speedup, ss,
                                                                                bus_flows,
                                                                                route,
                                                                                next_route,
                                                                                bus_trips,
                                                                                transfers,
                                                                                opt_val)
                    runtime = time.time() - runtime_start
                    runtimes.append(runtime)
                    i+=1
                    if self.algo == 1 or self.algo == 0: # Offline or Deterministic
                        i = self.algo_parameters["nbr_simulations"]
                        j_try = int(self.algo_parameters["j_try"]) + 1
                except Exception as e:
                    traceback.print_exc()
                    logger.warning('Problem with scenario {}/{} and stop_id {}'.format(j_try, self.algo_parameters["j_try"], stop_id))
            else: 
                logger.warning('The scenario generation failed after {} tries.'.format(j_try))
                return(False, False, (False, -1))
        # Step 5: Apply tactics
        if self.algo == 2: # Regret
            time_max, hold, speedup, ss = self.choose_tactic(tactic_regrets_dict, last_stop)

        return(speedup == 1, ss == 1, ( hold >= 0 , time_max))

    def get_next_route_stops(self, last_stop_id, next_route):
        """Get the next stops of the main line and the next main line.
        Inputs:
            - route: Route object, the main line route.
            - next_route: Route object, the next main line route.

        Outputs:
            - stops: list, the next stops of the main line and the next main line."""
        stops_second = []
        stop_id = -1
        i = -1
        while stop_id != last_stop_id and i < len(next_route.next_stops)-1:
            i+=1
            stop = next_route.next_stops[i]
            stop_id = stop.location.label
            stops_second.append(stop)
        return stops_second

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
                                time_to_prev=600,
                                time_to_next=600):
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

        # Get potential transfer routes: consider all routes, not just selected routes as we don't know in advance where passengers will transfer.
        all_routes = [route for route in state.route_by_vehicle_id.values() if route.vehicle.id != state.main_line and route.vehicle.id != state.next_main_line]
        
        # For each stop, note potential transfer routes and their arrival times.
        min_time = stops[0].arrival_time - time_to_prev
        max_time = stops[-1].departure_time + time_to_next
        transfer_stop_times = {}
        for route in all_routes:
            if route.current_stop is not None:
                if int(route.current_stop.location.label) in all_stops and route.current_stop.arrival_time > min_time and route.current_stop.arrival_time < max_time:
                    print("Current stop is in all stops for potential transfers")
                    if int(route.current_stop.location.label) not in transfer_stop_times:
                        transfer_stop_times[int(route.current_stop.location.label)] = []
                    current_stop_arrival_time_estimation = self.get_arrival_time_estimation(route, route.current_stop, type_transfer_arrival_time)
                    transfer_stop_times[int(route.current_stop.location.label)].append(current_stop_arrival_time_estimation, route.vehicle.route_name)
            if route.next_stops is not None:
                for stop in route.next_stops:
                    if int(stop.location.label) in all_stops and stop.arrival_time > min_time and stop.arrival_time < max_time:
                        print("Next stop is in all stops for potential transfers")
                        if int(stop.location.label) not in transfer_stop_times:
                            transfer_stop_times[int(stop.location.label)] = []
                        current_stop_arrival_time_estimation = self.get_arrival_time_estimation(route, stop, type_transfer_arrival_time)
                        transfer_stop_times[int(stop.location.label)].append(current_stop_arrival_time_estimation, route.vehicle.route_name)
        print(transfer_stop_times)
        input('transfer stop times')
        return transfer_stop_times
    
    def get_arrival_time_estimation(self, route, stop, type_transfer_arrival_time):
        if type_transfer_arrival_time==2: # real
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
        normal = stop.departure_time
        tactic = stop.departure_time
        previous_departure_time = state.route_by_vehicle_id[state.main_line].previous_stops[-1].departure_time
        dwell = 0
        last = -1
        for i in range(len(stops)):
            stop=stops[i]
            travel_time = stop.arrival_time - previous_departure_time
            dwell = stop.departure_time-stop.arrival_time
            stop_id = int(stop.location.label)
            normal_time = travel_time+dwell
            if self.skip_stop and self.speedup_factor!=1:
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
            trip_id = state.main_line
            if stop_id in transfer_times:
                for (time, route_name) in transfer_times[stop_id]:
                    if normal > time and tactic <= time: #tactics can turn an impossible transfer into a possible one
                        last = stop
        return(last)
    
    def create_tactics_dict(self, last_stop):
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
                transfer_times[trip_id : str][stop_id : int] = [(arrival_time : int, route_name :str "ligne+dir"), ...]

        Outputs:
        - bus_trips: dict, the trips on the main and next routes.
            - The format is as follows:
                bus_trips[trip_id : str] = [Stop1, Stop2, ...]
        - transfers: dict, the transfers at the stops.
            - The format is as follows:
                transfers[trip_id : str][stop_id : int]['boarding'/'alighting'] = [(arrival_time : int, nbr_passengers : int), ...]
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
            - frequence: frequency of the route
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
                print('Travel time is negative...')
            else: 
                pairs_dict[(x[0],x[1])].append([x[2], x[3]],) # [travel_time, event_time]
        for key in pairs_dict:
            pairs_dict[key] = np.array(pairs_dict[key])
        return(pairs_dict,
            #    new_frequence, 
               dwells_dict)

    def get_passenger_historical_data(self, route_name, pathtofile):
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
        # print('Number of non-existant pairs: ', count)
        return(KClusters)
    
    def cluster_data_at_stops(self,
                              stops : np.array,
                              data_at_stops : dict):
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
        """Calculates the headway between two lines with future stops stops and stops_second."""
        headway_at_stop_id = stops_second[0].location.label
        next_time = stops_second[0].arrival_time
        previous_stops = main_route.previous_stops
        for stop in previous_stops:
            if stop.location.label == headway_at_stop_id:
                previous_time = stop.arrival_time
                break
        headway = next_time - previous_time
        return headway
    
    def generate_bus_trip(self, stops, prev_stop, transfer_times, last_stop = -1, initial_flow = 0):
        """Generates a trip for a route with stops and previous time prev_time.
        Inputs:
            - stops: list of Stops
            - prev_stop: Stop
            - transfer_times: dict
            - last_stop: Stop, the last stop at which tactics are allowed
        Outputs:
            - new_stops: list of Stops
            - transfers: dict
                The format is as follows:
                transfers[stop_id : int]['boarding'/'alighting'] = [(arrival_time : int, nbr_passengers : int), ...]"""
        new_stops =[]
        transfers = {}
        prev_time = prev_stop.departure_time if prev_stop != None else stops[0].arrival_time -1
        for stop in stops:
            dwell_time = self.generate_dwell_time(stop, prev_time)
            travel_time = self.generate_travel_time(prev_stop, stop, prev_time)
            nbr_alighting = self.generate_alighting(stop, prev_time, initial_flow)
            initial_flow -= nbr_alighting
            if int(stop.location.label) in transfer_times and (last_stop == -1 or stop.cumulative_distance <= last_stop.cumulative_distance):
                nbr_transferring_alighting = self.generate_transferring_alighting(stop, initial_flow)
                initial_flow -= nbr_transferring_alighting
                nbr_transferring_boarding = self.generate_transferring_boarding(stop)
                initial_flow += nbr_transferring_boarding
            else:
                nbr_transferring_alighting = 0
                nbr_transferring_boarding = 0
            nbr_boarding = self.generate_boarding(stop, prev_time)
            initial_flow += nbr_boarding
            transfers_at_stop = self.generate_transfers(stop, nbr_transferring_boarding, nbr_transferring_alighting, transfer_times)
            prev_time = prev_time + travel_time + dwell_time
            new_stop = Stop(arrival_time = prev_time + travel_time, 
                            departure_time = prev_time + travel_time + dwell_time,
                            location = stop.location,
                            cumulative_distance = stop.cumulative_distance,
                            min_departure_time = stop.min_departure_time,
                            planned_arrival_time = stop.planned_arrival_time,
                            planned_departure_time_from_origin = stop.planned_departure_time_from_origin)
            new_stop.passengers_to_board.append(nbr_boarding)
            new_stop.passengers_to_alight.append(nbr_alighting)
            transfers[int(new_stop.location.label)] = transfers_at_stop
            new_stops.append(new_stop)
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
        """Generate a value from clusters.
        Inputs:
            - clusters_pair = (C, clusters): tuple of clusters and cluster indices
            - values: np.array, shape (n,2)
            - time: int"""
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
        if stop1 == None:
            return 1
        type_travel_time = self.algo_parameters['type_travel_time']
        if type_travel_time == 2:
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
            for trip in passengers_to_alight: # No transfers
                if (trip.current_leg != None and trip.next_legs == [] and trip.current_leg.destination.label == stop.location.label):
                    count += 1
                if (trip.current_leg == None):
                    i = 0
                    for leg in trip.next_legs:
                        if leg.destination.label == stop.location.label and i < len(trip.next_legs) - 1:
                            count += 1
                            break
                        i += 1
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
            for trip in passengers_to_alight:
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
                transfers['boarding'/'alighting'] = [(arrival_time : int, nbr_passengers : int), ...]"""
        if nbr_alighting + nbr_boarding == 0 or \
           int(stop.location.label) not in transfer_times:
            return []
        
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
                transfers['boarding'].append((item, count))
        tmp =[]
        for i in range(nbr_alighting):
            transfer_time = random.choice(transfer_times[stop_id])[0]
            tmp.append(transfer_time)
            for item, count in Counter(tmp).items():
                transfers['alighting'].append((item, count))
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
        ### Ici on utilise une hierarchie des tactiques si plusieurs sont utilises le meme nombre de fois :
        ## La hierarchie depend de la facilite a implementer une tactique et au risque qu'elle induit 
        ### None> H_HP> SP> SP_HP> H_T > SP_T>SS
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
        tmp=[ T['none'], T['h_hp'], T['sp'], T['sp_hp'], T['h_t'][0], T['sp_t'][0], T['ss']]
        index=np.argmin(tmp) #ceci retourne bien la tactique la plus haute dans la hierarchie si plusieurs tactiques ont le meme regret 
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
                                   time_max: int, hold :int, speedup: int, ss: int,
                                   bus_flows_in_solution : dict,
                                   route : Route,
                                   next_route : Route,
                                   bus_trips : dict,
                                   transfers : dict,
                                   opt_cost: int):
        """Updates the tactics dictionary T given the optimal tactic, and calculates the regret of all other tactics.
        Inputs:
            - T: dict, the tactics dictionary
            - time_max: int, the latest time at which to depart from the stop after holding
            - hold: int, -1 if no hold time
                         0 if wait for planned time
                         1 if waiting for a transfer
            - speedup: int, 0 if no speedup, 1 if speedup
            - ss: int, 0 if no skip-stop, 1 if skip-stop
            - bus_flows_in_solution: dict, the bus flows in the solution, shows the path of each bus in the graph.
            - route: Route, the main line route
            - next_route: Route, the next main line route
            - bus_trips: dict, the generated trips on the main and next routes
            - transfers: dict, the transfers at the stops in the genrated trips
            - opt_cost: int, the optimal cost when using the optimal tactic
        Outputs:
            - T: dict, the updated tactics dictionary
            """
        # Get parameters
        ss_gen = self.skip_stop
        speedup_gen = self.speedup_factor
        price = self.general_parameters["price"]
        step = self.general_parameters["step"]
        out_of_bus_price = self.general_parameters["out_of_bus_price"]
        trip_id = route.vehicle.id
        next_trip_id = next_route.vehicle.id
        stop_id = int(route.next_stops[0].location.label)
        initial_flows = {}
        initial_flows[trip_id] = int(len(route.onboard_legs))
        initial_flows[next_trip_id] = int(len(next_route.onboard_legs))

        # List of all tactics
        all = ['none', 'h_hp', 'h_t']
        if ss_gen == True: 
            all.append('ss')
        if speedup_gen != 1: 
            all.append('sp')
            all.append('sp_hp')
            all.append('sp_t')

        # Find optimal tactic and remove it from the list of tactics
        if ss==1: 
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
        tactics = self.get_tactics(bus_flows_in_solution, trip_id, next_trip_id)
        passages = self.new_create_new_passages(bus_trips, transfers, tactics, stop_id, trip_id, time_max, all)
        for tactic in passages:
            if tactic == 'sp_t' or tactic == 'h_t':
                regret = self.new_get_tactic_regret(tactic, passages, opt_cost, trip_id, initial_flows, step, price, out_of_bus_price)
                tactic_regrets_dict[tactic][0] += regret
                tactic_regrets_dict[tactic][1].append(passages[tactic][trip_id][0].ha+passages[tactic][trip_id][0].dwell)
            else: 
                regret = self.new_get_tactic_regret(tactic, passages,opt_cost, trip_id, initial_flows, step, price, out_of_bus_price)
                tactic_regrets_dict[tactic] += regret
        return(tactic_regrets_dict)

    def get_gen_data(self, G_generated, stop_id, trip_id): 
        """ Extract the results after optimization for the graph G_generated for the stop_id in the bus trip trip_id.
        Inputs:
            - G_generated: Graph, the graph generated with data from the generated scenario
            - stop_id: int, the stop id
            - trip_id: str, the trip id
        Outputs:
            - time_max: int, the latest time at which to depart from the stop after holding
            - hold: int, the hold time
            - speedup: int, 0 if no speedup, 1 if speedup
            - ss: int, 0 if no skip-stop, 1 if skip-stop
            - bus_flows: dict, the bus flows in the solution, shows the path of each bus in the graph.
            - opt_val: int, the value of the objective function when using the optimal tactic
            - runtime: int, the runtime of the optimization"""
        V, A, s, t, flows, ids, node_dict, edge_dict, bus_dict = convert_graph(G_generated)
        opt_val, flow, display_flows, bus_flows, runtime = build_and_solve_model_from_graph(V, A, s, t, flows, ids, node_dict, edge_dict,
                                                                                            "Gen"+str(stop_id),
                                                                                            bus_dict,
                                                                                            verbose = False, 
                                                                                            prix_hors_bus = self.general_parameters["out_of_bus_price"], 
                                                                                            )
        time_max, hold, speedup, ss = extract_tactics_from_solution(bus_flows, stop_id, trip_id)
        return(time_max, hold, speedup, ss, bus_flows, opt_val, runtime)
    