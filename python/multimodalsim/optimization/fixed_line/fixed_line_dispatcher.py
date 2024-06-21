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
        self.__Data = None


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
        # return(False, False, (False, -1))
            while i<self.algo_parameters["nbr_simulations"]:
                if j_try<int(self.algo_parameters["j_try"]):
                    try: # Bias because the scenarios which work are those where m/d are possible.
                        j_try+=1
                        # Step a: Generate instance for scenario j_try for the Regret algorithm
                        passages,last=NewGenerateur(lign,
                                                    dir, 
                                                    self.general_parameters['nbr_bus'], 
                                                    Data,
                                                    type_intervalles=self.algo_parameters['type_intervalles'],
                                                    type_dwell=self.algo_parameters['type_dwell'],
                                                    type_tps_parcours=self.algo_parameters['type_tps_parcours'],
                                                    type_m=self.algo_parameters['type_m'],
                                                    type_d=self.algo_parameters['type_d'],
                                                    type_tm=self.algo_parameters['type_tm'],
                                                    type_td=self.algo_parameters['type_td'],
                                                    type_ttime=self.algo_parameters['type_ttime'],
                                                    Real_passages=passages_multiple,
                                                    initial_flows=initial_flows,
                                                    plan_times=planned_times,
                                                    dimension=self.general_parameters["dimension"],
                                                    last=last,
                                                    horizon=self.horizon,
                                                    transfer_times=transfer_times
                                                    )
                        runtime_start_regret=time.time()
                        # Step b: Create graph from generated instance
                        G_gen, bus,od,stats_od,extras=build_multiple_buses_hash(passages_multiple=passages,
                                                                                flot_initial=initial_flows,
                                                                                pas=self.general_parameters["pas"],
                                                                                price=self.general_parameters["price"],
                                                                                speedup_gen=self.speedup_factor,
                                                                                ss_gen=self.skip_stop,
                                                                                od_dict={}, 
                                                                                simu=True,
                                                                                last_stop=last_stop)
                        # nb_noeuds.append(nb_nodes(G_gen))
                        # nb_arcs.append(nb_edges(G_gen))

                        # Step c: Get Data on optimization results
                        passage_gen_id=[p for p in passages[trip_id] if get_passage_stop_id(p)==int(stop_id) and get_passage_transfer(p)==False][0]
                        dwell_gen=get_passage_dwell_time(passage_gen_id)
                        last_dwell_real=route.previous_stops[-1].departure_time - route.previous_stops[-1].arrival_time
                        last_dist_real=real_prev_dists[stop_id]
                        simu_last_temps_parcours=get_simu_last_temps_parcours(passages,
                                                                              trip_id,
                                                                              passage_gen_id,
                                                                              last_regret)
                        time_max, wait, speedup, ss, bus_flows, opt_val, runtime=get_gen_data(G_gen,stop_id,
                                                                                              trip_id,
                                                                                              self.general_parameters["price"],
                                                                                              affichage=False, 
                                                                                              global_savepath=global_savepath,
                                                                                              simu_last_temps_parcours=simu_last_temps_parcours,
                                                                                              j_try=str(j_try)+'regret')

                        # Step d: Update tactics dictionary
                        T_regret=update_tactics_dict_regret(T_regret, 
                                                            time_max, wait, speedup, ss,
                                                            bus_flows,
                                                            stop_id, trip_id,
                                                            passages_gen=passages_regret,
                                                            opt_cost=opt_val,
                                                            initial_flows=initial_flows,
                                                            pas=self.general_parameters["pas"],
                                                            price=self.general_parameters["price"],
                                                            speedup_gen=self.speedup_factor,
                                                            ss_gen=self.skip_stop,
                                                            prix_hors_bus=self.general_parameters["prix_hors_bus"],
                                                            global_savepath=global_savepath,
                                                            affichage=affichage,
                                                            j_try=j_try)
                        runtime_regret=time.time()-runtime_start_regret
                        # runtimes_regret.append(runtime_regret)
                        i+=1
                        if self.algo == 1 or self.algo ==0:
                            j_try = int(self.algo_parameters["j_try"]) + 1

                    except Exception as e:
                        traceback.print_exc()
                        print('probleme dans simulation numero:',j_try, 'stop_id =', stop_id)
                else: 
                    print('on a depasse le nombre possible de simus sans reuissir')
                    input("Press enter to continue...")
                    return(False, False, (False, -1))
            # Step 5: Apply tactics
            if self.algo == 2: # Regret
                time_max_regret, wait_regret, speedup_regret, ss_regret=choose_tactic(T_regret,
                                                                                      self.skip_stop,
                                                                                      self.speedup_factor,
                                                                                      last_stop)

            # Step 6: Apply tactics
            passages_multiple_real,last, initial_flows,final_passages,h_prev,h_final=apply_tactics(passages_multiple,
                                                                                                stop_id,trip_id,
                                                                                                last,
                                                                                                initial_flows,
                                                                                                dwell_gen,
                                                                                                h_prev,
                                                                                                h_final,
                                                                                                last_dwell_real,
                                                                                                time_max_regret,
                                                                                                wait_regret,
                                                                                                speedup_regret,
                                                                                                ss_regret,
                                                                                                final_passages=final_passages,
                                                                                                last_dist_real=last_dist_real)
        transfer_time_to_use=[p for p in Real_passages_gen[trip_id] if get_passage_stop_id(p)==int(stop_id) and get_passage_transfer(p)==False][0]
        transfer_ha=get_passage_heure_act(transfer_time_to_use)

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
    
    def NewGenerateur(self, 
                      lign:str,
                      dir:str,
                      Real_passages,
                      initial_flows,
                      plan_times,
                      last={},
                      transfer_times={}):
        """"
        Fonction qui génère des passages de bus.
        On a besoin des statistiques sur les lignes de bus pour pouvoir lancer cette fonction ! À générer auparavant. 

        Entrées: 
        lign-numéro de ligne 
        dir-direction de la ligne 
        date
        nbr_bus-nombre de trajets à générer
        h_debut-heure du premier départ à générer. Bien vérifier que le dernier départ n'est pas après la fin de service. 
        # k nombre de clusters pour le clustering
        StopClusters-clusters sur les temps de parcours
        DwellClusters-clusters sur les dwells times
        Intervalles-clusters des intevralles 
        Montants-clusters sur le nombre de passagers montants
        Descendants-clusters sur le nombre de passagers montants
        TMontants-clusters sur le nombre de passagers en correspondance montants
        TDescendants-clusters sur le nombre de passagers en correspondance montants
        type_xxx: type de génération de données 
            0: tirage dans cluster 
            1: moyenne du cluster 
            2: donnée réelle 
            3: planifié
        type_ttime: type de génération de données 
            0: heure planifiée +retard actuel
            1: temps de parcours proportionnel à la distance restante actuelle (référence=tps parcours planifié)
            2: donnée réelle 
            3: planifié
        Passages: passages reels dans la simulation
        dimension: dimension des clusters 
        # pathtofile: dossier par defaut ou chercher les donnees necessaires 
        cost_attente: cout de rater le dernier bus dans l'horizon 
        # affichage: bool qui indique si on affiche les clusters
        last: dict qui pour chaque trip donne le dernier arret visite, l'heure actuelle de DEPART depuis l'arret, le dwell a l'arret, et l'heure planifiee d'arrivee a l'arret

        Sorties: 
        passages-liste de passages aux arrets. Les passages sont ordonnés dans l'ordre de passage (passages normaux et transferts)
        last: dict qui pour chaque trip donne le dernier arret visite, l'heure actuelle de DEPART depuis l'arret, le dwell a l'arret, et l'heure planifiee d'arrivee a l'arret
        """
        nbr_bus = self.general_parameters['nbr_bus']
        type_intervalles = self.algo_parameters['type_intervalles']
        type_dwell = self.algo_parameters['type_dwell']
        type_tps_parcours = self.algo_parameters['type_tps_parcours']
        type_m = self.algo_parameters['type_m']
        type_d = self.algo_parameters['type_d']
        type_tm = self.algo_parameters['type_tm']
        type_td = self.algo_parameters['type_td']
        type_ttime = self.algo_parameters['type_ttime']
        initial_flows = initial_flows
        dimension = self.general_parameters["dimension"]
        horizon = self.horizon
        Data = self.Data[lign+dir]

        ###Get Data 
        pairs, frequence, dwells,montants,descendants,transferts,new_pairs,new_dwells,new_frequence,new_m,new_d,new_tm,new_td,StopClusters,DwellClusters,Intervalles,Montants,Descendants,TMontants,TDescendants=Data

        #Get all stops
        completename=os.path.join("stl","Data",'route_stops_'+lign+dir+'_month.txt')
        alltype=np.dtype([('f0', 'i8'), ('f1', 'U12'),('f2','float16'),('f3','i8')])
        stops=np.genfromtxt(completename,delimiter=",",dtype=alltype, usecols=[0,1,2,3], names=True)
        # 0-stop_order
        # 1-stop_id
        # 2-dist_cum
        # 3-number of times stop was registered in the month
        stop_dict={}
        stop_list=[]
        for stop in stops:
            stop_list.append(int(stop[1]))
            stop_dict[int(stop[1])]={}
            stop_dict[int(stop[1])]['order']=int(stop[0])
            stop_dict[int(stop[1])]['dist']=float(stop[2])
            stop_dict[int(stop[1])]['f']=int(stop[3])
        if lign=='70': 
            if dir=='O':
                all=746 #nombre de trip_ids dans le mois 
            else: 
                all=702 ### a revoir
        else:### ligne 42
            if dir=='O':
                all=1188
            else: 
                all=1297
        ### Partie 2: Génération de passages 
        ### Infos sur les passages reels\planifies 
        if type_intervalles==2:
            order=sorted([(Real_passages[trip][0].ha-Real_passages[trip][0].cost,trip) for trip in Real_passages],key=itemgetter(0))
        elif type_intervalles==3: 
            order=sorted([(Real_passages[trip][0].hp-Real_passages[trip][0].cost,trip) for trip in Real_passages],key=itemgetter(0))
        else:
            order=[]
        
        #le premier passage de chaque bus est adapte pour ne plus prendre en compte le dwell time a l'arret prec
        debut=sorted([(Real_passages[trip][0].ha-Real_passages[trip][0].cost,trip) for trip in Real_passages],key=itemgetter(0))[0][0]
        intervalles=gen_intervalle(Intervalles,new_frequence,frequence,nbr_bus,debut,dimension,type_intervalles,order)
        order=sorted([(Real_passages[trip][0].ha-Real_passages[trip][0].cost,trip) for trip in Real_passages],key=itemgetter(0))
        
        if last=={}:
            for trip in Real_passages:
                last[trip]=(-1,Real_passages[trip][0].ha-Real_passages[trip][0].cost,0,Real_passages[trip][0].ha-Real_passages[trip][0].cost)

        if initial_flows=={}:
            for trip in Real_passages:
                initial_flows[trip]=0
        # print('flot initial', initial_flows)
        #get info: 
        dwell_data={}
        m_data={}
        d_data={}
        tm={}
        td={}
        tdwell={}
        ttime={}
        tps={}
        trip=0
        trips={}
        # print(order)
        for (h,trip_id) in order:
            # print('h', h, 'trip_id', trip_id)
            trips[trip]=trip_id
            first=True
            prec_dwell=0 #car on prend l'heure de depart depuis le dernier arret
            prev=last[trip_id][1]#heure de depart reelle post tactiques depuis le dernier arret pour ce bus
            tmp=Real_passages[trip_id]
            dwell_data[trip]={}
            m_data[trip]={}
            d_data[trip]={}
            tm[trip_id]={}
            td[trip_id]={}
            tdwell[trip_id]={}
            ttime[trip_id]={}
            tps[trip]={}
            for p in tmp:
                dwell=int(get_passage_dwell_time(p))
                stop=int(get_passage_stop_id(p))
                m=int(get_passage_nb_montant(p))
                d=int(get_passage_nb_desc(p))
                if get_passage_transfer(p)==False:
                    dwell_data[trip][stop]=dwell #dwell reel 
                    m_data[trip][stop]=m
                    d_data[trip][stop]=d
                    if type_tps_parcours==2:#reel
                        if first==False:
                            tps[trip][(stop_prev,stop)]=get_passage_cost(p)-prec_dwell#tps de parcours reel
                            stop_prev=stop
                            prec_dwell=dwell
                        else:
                            first=False
                            tps[trip][(-1,stop)]=get_passage_cost(p)-last[trips[trip]][2]#tps de parcours reel
                            stop_prev=stop
                            prec_dwell=dwell
                    elif type_tps_parcours==3:#planifie
                        if first==False:
                            tps[trip][(stop_prev,stop)]=get_passage_heure_plan(p)-prev-10
                            prev=get_passage_heure_plan(p)
                            stop_prev=stop
                        else:#premier arret pour ces passages
                            first=False
                            stop_prev=stop
                            # tps[trip][(last[trip][0],stop)]=get_passage_heure_plan(p)-prev-10 #10 is general dwell time
                            prev=get_passage_heure_plan(p)
                    prec_dwell=dwell
                else:
                    trip_tmp=copy.deepcopy(trip)
                    trip=trip_id
                    tdwell[trip][stop]=dwell
                    if stop in tm[trip]:
                        tm[trip][stop].append(m)
                    else: 
                        tm[trip][stop]=[m]
                    if stop in td[trip]: 
                        td[trip][stop].append(d)
                    else: 
                        td[trip][stop]=[d]
                    if stop in ttime[trip]:
                        if type_ttime==2: #reel 
                            ttime[trip][stop].append(get_passage_heure_act(p))
                        elif type_ttime==3: #planifie
                            ttime[trip][stop].append(get_passage_heure_plan(p))
                    else: 
                        if type_ttime==2: #reel 
                            ttime[trip][stop]=[get_passage_heure_act(p)]
                        elif type_ttime==3: #planifie
                            ttime[trip][stop]=[get_passage_heure_plan(p)]
                    trip=trip_tmp
            trip+=1
        # print('trips dict', trips)
        if type_ttime==0 or type_ttime==1 or type_ttime==3: #translation, estimation ou reel 
            ttime=transfer_times
        if ttime=={}:
            for (h,trip_id) in order:
                ttime[trip_id]={}
        # print(ttime)
        passages={}
        # time=h_debut
        for i in range(nbr_bus):
            trip_id=i
            passages[trips[trip_id]]=[]
            if i==0:
                h_debut=debut
            if i==1: 
                h_debut=get_passage_heure_act(Real_passages[trips[1]][0])-Real_passages[trips[1]][0].cost
            # h_debut=debut+sum([intervalles[j] for j in range(i+1)])
            old_dwell=last[trips[trip_id]][2]
            hp=h_debut
            # hp=debut+sum([intervalles[j] for j in range(i+1)])
            # print('total',initial_flows[trips[trip_id]])
            total=initial_flows[trips[trip_id]] #nombre de passagers dans le bus 
            stop=get_passage_stop_id(Real_passages[trips[trip_id]][0])
            l=get_passage_level(Real_passages[trips[trip_id]][0])
            start = [k for k, x in enumerate(stops) if int(x[1]) == stop][0]
            if i==0: 
                end=min(start+1+horizon, len(stops))
            #dwell time
            if type_dwell==2:
                if stop in dwell_data[trip_id]:
                    dwell=dwell_data[trip_id][stop]
                    # print('on est la dwell 1')
                else:
                    dwell=0#le stop est skip dans le cas reel 
            elif stop in dwells:
                real=len(dwells[stop])
                win_dwell=real/all
                (C, clusters)=DwellClusters[stop]
                dwells_stop=dwells[stop]
                new_dwells_stop=new_dwells[stop]
                dwell=gen_dwell(C, clusters,dwells_stop, new_dwells_stop, dimension,h_debut,type_dwell,win_dwell,dwell)
            else:
                dwell=0 #on ne s'arrete pas a l'arret.

            #nombre descendants:
            #calculer avant le nombre de montants (sinon le total peut etre negatif!)
            if type_d==2: #reel
                if int(stop) in d_data[trip_id]:
                    d=d_data[trip_id][int(stop)]
                    # print('on est la d 1')
                    if total-d<0:
                        if total>0:
                            d=total-1
                        else: d=0
                else:#the bus did not stop here in real life
                    d=0
            elif stop in descendants:
                real_d=len([x for x in descendants[stop]])
                win=real_d/all
                (C, clusters)=Descendants[stop]
                descendants_stop=descendants[stop]
                new_descendants_stop=new_d[stop]
                d=gen_d(C, clusters,descendants_stop, new_descendants_stop, dimension,h_debut,type_d,win)
                if total-d<0:
                    if total>0:
                        d=total-1
                    else: d=0
            else: 
                d=0
            total-=d
            # print('total',total,'d',d,'stop',stop)

            #nbr montants
            if type_m==2: #reel
                if int(stop) in m_data[trip_id]:
                    # print('on est la m 1')
                    m=m_data[trip_id][int(stop)]
                else:#the bus did not stop here in real life
                    m=0
            elif stop in montants:
                real_m=len([x for x in montants[stop]])
                win=real_m/all
                (C, clusters)=Montants[stop]
                montants_stop=montants[stop]
                new_montants_stop=new_m[stop]
                m=gen_m(C, clusters,montants_stop, new_montants_stop, dimension,h_debut,type_m,win)
            else:
                m=0
            total+=m
            # print('total',total)

            #tps parcours
            prec=last[trips[trip_id]][0]#dernier arret visite par ce bus avant la simulation 
            if prec==-1:
                if start==0:
                    temps_parcours=0
                elif type_tps_parcours==2 or type_tps_parcours==3:
                    # print('on est la tmps parcours 1')
                    temps_parcours=get_passage_cost(Real_passages[trips[trip_id]][0])
                else: 
                    prec1=int(stops[start-1][1])
                    (C, clusters)=StopClusters[(prec1,stop)]
                    pairs_stop=pairs[(prec1,stop)]
                    new_pairs_stop=new_pairs[(prec1,stop)]
                    temps_parcours=gen_tps(C,clusters,pairs_stop, new_pairs_stop,dimension, h_debut,type_tps_parcours)
            ### le temps de parcours prends en compte le dwell a l'arret prec
            elif type_tps_parcours==2:#reel
                temps_parcours=get_passage_cost(Real_passages[trips[trip_id]][0])-last[trips[trip_id]][2]
            elif type_tps_parcours==3:#planifie
                prev=last[trips[trip_id]][3]#heure d'arrivee planifiee au dernier arret 
                temps_parcours=max(1,get_passage_heure_plan(Real_passages[trips[trip_id]][0])-prev-5)
            else:
                if (prec,stop) in StopClusters:
                    (C, clusters)=StopClusters[(prec,stop)]
                    pairs_stop=pairs[(prec,stop)]
                    new_pairs_stop=new_pairs[(prec,stop)]
                    temps_parcours=gen_tps(C,clusters,pairs_stop, new_pairs_stop,dimension, h_debut,type_tps_parcours)
                else:
                    if start>0:
                        prec1=int(stops[start-1][1])
                        (C, clusters)=StopClusters[(prec1,stop)]
                        pairs_stop=pairs[(prec1,stop)]
                        new_pairs_stop=new_pairs[(prec1,stop)]
                        temps_parcours=gen_tps(C,clusters,pairs_stop, new_pairs_stop,dimension, h_debut,type_tps_parcours)
                        dist_prec=float([x[2] for k, x in enumerate(stops) if int(x[1]) == prec][0])
                        dist1=float(stops[start][2])-float(stops[start-1][2])
                        dist2=float(stops[start][2])-dist_prec
                        temps_parcours=max(1,int(temps_parcours*dist2/dist1))
                    else:
                        temps_parcours=0

            ##pas besoin car ici old_dwell=0 
            if type_tps_parcours!=3:
                temps_parcours+=old_dwell 
            hp=hp+temps_parcours
            dist=float(stops[start][2])
            if int(stop) in plan_times[trips[trip_id]]:
                h_plan=plan_times[trips[trip_id]][int(stop)]
            else:
                # print('stop', stop, 'trip', trips[trip_id], 'plan_time',plan_times[trips[trip_id]])
                h_plan=hp
            # print(stop, h_plan, hp, dwell, m, d,temps_parcours, l,total)
            passages[trips[trip_id]].append(Passage(int(stop),h_plan,hp,dwell,m,d,temps_parcours,False,l,dist))
            old_dwell=dwell
            prec=stop
            q=0
            # for j in range(start+1,min(start+1+horizon, len(stops))):
            for j in range(start+1,end):
                # print('iter', q)
                q+=1
                l+=1
                stop=int(stops[j][1])

                #temps parcours 
                if type_tps_parcours==2 or type_tps_parcours==3:#reel ou planifie
                    if (prec,stop) in tps[trip_id]:
                        temps_parcours=tps[trip_id][(prec,stop)]#ce dict est deja remplie avec les infos correspondantes en fonction de type
                    else:
                        prec1=[(prec2,stop2) for (prec2,stop2) in tps[trip_id] if stop2==int(stop)]
                        if len(prec1)!=0:
                            prec1=prec1[0][0]#dernier arret ou s'est arrete le bus avant stop dans le cas reel
                            dist_prec1=float([x[2] for k, x in enumerate(stops) if int(x[1]) == prec1][0])
                            dist_prec=float(stops[j-1][2])
                            dist=float(stops[j][2])
                            dist1=dist-dist_prec
                            dist2=dist-dist_prec1
                            temps_parcours_tmp=tps[trip_id][(prec1,stop)]
                            temps_parcours=max(1,int(temps_parcours_tmp*dist1/dist2))
                        else: 
                            stop1=[(prec2,stop2) for (prec2,stop2) in tps[trip_id] if prec2==int(prec)]
                            if len(stop1)!=0:
                                stop1=stop1[0][1]
                                dist_stop1=float([x[2] for k, x in enumerate(stops) if int(x[1]) == stop1][0])
                                dist_stop=float(stops[j][2])
                                dist_prec=float(stops[j-1][2])
                                dist1=dist_stop-dist_prec
                                dist2=dist_stop1-dist_prec
                                temps_parcours_tmp=tps[trip_id][(prec,stop1)]
                                temps_parcours=max(1,int(temps_parcours_tmp*dist1/dist2))
                            else:
                                indice_tmp=j
                                while len(prec1)==0 and indice_tmp<len(stops)-1:
                                    indice_tmp+=1
                                    stop_tmp=int(stops[indice_tmp][1])
                                    prec1=[(prec2,stop2) for (prec2,stop2) in tps[trip_id] if stop2==int(stop_tmp)]
                                if indice_tmp>=len(stops)-1:#on est au dernier passage
                                    (C, clusters)=StopClusters[(prec,stop)]
                                    pairs_stop=pairs[(prec,stop)]
                                    new_pairs_stop=new_pairs[(prec,stop)]
                                    ### le temps de parcours prends en compte le dwell a l'arret prec
                                    temps_parcours=gen_tps(C,clusters,pairs_stop, new_pairs_stop,dimension, h_debut,1)
                                else:
                                    prec1=prec1[0][0]#premier arret ou s'arrete le bus apres stop dans le cas reel
                                    dist_prec1=float([x[2] for k, x in enumerate(stops) if int(x[1]) == prec1][0])
                                    dist_stop_tmp=float(stops[indice_tmp][2])
                                    dist=float(stops[j][2])
                                    dist_prec=float(stops[j-1][2])
                                    dist1=dist_stop_tmp-dist_prec1
                                    dist2=dist-dist_prec
                                    temps_parcours_tmp=tps[trip_id][(prec1,stop_tmp)]
                                    temps_parcours=max(1,int(temps_parcours_tmp*dist2/dist1))
                        ### si on a pas la valeur exacte on trouve la valeur proportionnelle par rapport
                        ### a la distance parcourue
                else:
                    (C, clusters)=StopClusters[(prec,stop)]
                    pairs_stop=pairs[(prec,stop)]
                    new_pairs_stop=new_pairs[(prec,stop)]
                    ### le temps de parcours prends en compte le dwell a l'arret prec
                    temps_parcours=gen_tps(C,clusters,pairs_stop, new_pairs_stop,dimension, h_debut,type_tps_parcours)
                    # print(stop,'  ',temps_parcours)
                if type_tps_parcours!=3:
                    temps_parcours+=old_dwell 
                
                #dwell time
                if type_dwell==2:#reel 
                    if int(stop) in dwell_data[trip_id]:
                        # print('on est la dwell 2')
                        dwell=dwell_data[trip_id][int(stop)]
                    else:
                        dwell=0
                elif stop in dwells: 
                    real=len(dwells[stop])
                    win_dwell=real/all
                    (C, clusters)=DwellClusters[stop]
                    dwells_stop=dwells[stop]
                    new_dwells_stop=new_dwells[stop]
                    dwell=gen_dwell(C, clusters,dwells_stop, new_dwells_stop, dimension,h_debut,type_dwell,win_dwell,dwell)
                else: 
                    dwell=0 #on ne s'arrete pas a l'arret. Pas de SS pour l'instant

                #nombre descendants
                if type_d==2: #reel
                    if int(stop) in d_data[trip_id]:
                        d=d_data[trip_id][int(stop)]
                        if total-d<0:
                            if total>0:
                                d=total-1
                            else: d=0
                    else:#the bus did not stop here in real life
                        d=0
                elif stop in descendants:
                    real_d=len([x for x in descendants[stop]])
                    win=real_d/all
                    (C, clusters)=Descendants[stop]
                    descendants_stop=descendants[stop]
                    new_descendants_stop=new_d[stop]
                    d=gen_d(C, clusters,descendants_stop, new_descendants_stop, dimension,h_debut,type_d,win)
                    if total-d<0:
                        if total>0:
                            d=total-1
                        else: d=0
                else: 
                    d=0
                # print('total',total,'d',d,'stop',stop)
                #nbr montants
                if type_m==2: #reel
                    if int(stop) in m_data[trip_id]:
                        m=m_data[trip_id][int(stop)]
                    else:#the bus did not stop here in real life
                        m=0
                elif stop in montants:
                    real_m=len([x for x in montants[stop]])
                    win=real_m/all
                    (C, clusters)=Montants[stop]
                    montants_stop=montants[stop]
                    new_montants_stop=new_m[stop]
                    m=gen_m(C, clusters,montants_stop, new_montants_stop, dimension,h_debut,type_m,win)
                else:
                    m=0
                
                # print('total',total)
                dist=float(stops[j][2])
                # print(stop, hp, dwell, m, d,temps_parcours, l,total)
                hp=hp+temps_parcours
                if int(stop) in plan_times[trips[trip_id]]:
                    h_plan=plan_times[trips[trip_id]][int(stop)]
                else:
                    # print('stop', stop, 'trip', trips[trip_id], 'plan_time',plan_times[trips[trip_id]])
                    h_plan=hp
                # print(stop, h_plan, hp, dwell, m, d,temps_parcours, l,total)
                
                ### Transferts?
                tmp_trip_id=copy.deepcopy(trip_id)
                trip_id=trips[trip_id]
                maxd=0
                d=0
                dreal=False
                tdreal=False
                if type_d==2: 
                    maxd=copy.deepcopy(d)
                    dreal=True
                elif type_td==2:
                    tdreal=True
                    if (int(stop) in ttime[trip_id]):
                        for transfer_time in ttime[trip_id][int(stop)]:
                            if int(stop) in td[trip_id]:
                                maxd=sum(k for k in  td[trip_id][int(stop)])
                                # print('on est la maxd')
                else:
                    maxd=copy.deepcopy(d)
                #dans tous les cas ttime represente deja l'heure de passage du bus de transfert comme on souhaite
                # la modeliser 
                # NON: if type_ttime==2 or type_ttime==3: #si on a les vrais  temps de transferts
                if (int(stop) in ttime[trip_id]):
                    for transfer_time in ttime[trip_id][int(stop)]:
                        m_tmp=0
                        d_tmp=0
                        transfer=False
                        #transfert descendant
                        if type_td==2:#real 
                            if int(stop) in td[trip_id] and len(td[trip_id][int(stop)])>0:
                                d_tmp=td[trip_id][int(stop)].pop(0)
                                if maxd-d_tmp<0:#normalement pas besoin de ce test... 
                                    if dreal: #dreal et tdreal ...pas normal
                                        if maxd>0:
                                            d_tmp=maxd
                                        else: d_tmp=0
                                    else: 
                                        # print('on est la bis maxd')
                                        maxd=maxd+(d_tmp-maxd)
                                    # else: d=0
                            #else: d=0#pas de transferts descendants a cet arret 
                        elif stop in transferts['d']:
                            real_d=len(transferts['d'][stop])
                            win_td=real_d/all
                            (C, clusters)=TDescendants[stop]
                            tdescendants_stop=transferts['d'][stop]
                            new_tdescendants_stop=new_td[stop]
                            d_tmp=gen_td(C, clusters,tdescendants_stop, new_tdescendants_stop, dimension,h_debut,type_td,win_td)
                            if maxd-d_tmp<0:
                                if dreal:
                                    if maxd>0:
                                        d_tmp=maxd
                                    else: d_tmp=0
                                else: 
                                    maxd=maxd+(d_tmp-maxd)
                        #Transfert montant
                        if type_tm==2:#real
                            if int(stop) in tm[trip_id] and len(tm[trip_id][int(stop)])>0:
                                m_tmp=tm[trip_id][int(stop)].pop(0)
                            # else:  m=0
                        elif stop in transferts['m']:
                            real_m=len(transferts['m'][stop])
                            win_tm=real_m/all
                            transfer=True
                            (C, clusters)=TMontants[stop]
                            tmontants_stop=transferts['m'][stop]
                            new_tmontants_stop=new_tm[stop]
                            m_tmp=gen_tm(C, clusters,tmontants_stop, new_tmontants_stop, dimension,h_debut,type_tm,win_tm)
                        if m_tmp>0 or d_tmp>0:
                            transfer=True
                        if transfer:
                            maxd=maxd-d_tmp
                            passages[trips[tmp_trip_id]].append(Passage(int(stop),transfer_time,transfer_time,10,m_tmp,d_tmp,1800,True,l,dist))
                tmp_passage_transfer=[p for p in passages[trips[tmp_trip_id]] if get_passage_stop_id(p)==int(stop) and get_passage_transfer(p)==True and get_passage_nb_desc(p)>0]
                tdtot=sum([get_passage_nb_desc(p) for p in tmp_passage_transfer])
                if tdtot>d: #probleme !
                    if dreal: 
                        # if tdreal:
                        #     print('il y a un pb on ne devrait pas etre la')
                        while d-tdtot<0:
                            trans=np.random.choice(tmp_passage_transfer)
                            if get_passage_nb_desc(trans)>0:
                                trans.nb_d-=1
                                tdtot-=1
                    else: 
                        if total-tdtot>=0:
                            d=tdtot
                        else: 
                            maxtd=total
                            while maxtd-tdtot<0:
                                trans=np.random.choice(tmp_passage_transfer)
                                if get_passage_nb_desc(trans)>0:
                                    trans.nb_d-=1
                                    tdtot-=1
                            d=tdtot
                passages[trips[tmp_trip_id]].append(Passage(int(stop),h_plan,hp,dwell,m,d,temps_parcours,False,l,dist))
                total=total-d
                total+=m
                m=0
                d=0
                old_dwell=dwell
                # time+=temps_parcours
                prec=stop
                trip_id=tmp_trip_id
        i=0
        return(passages, last)

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
        pathtofile = r'C:\Users\kklau\Desktop\Final_Recherche\stl\Data'

        # Get historical data for the route
        stop_to_stop_pairs, headways_between_buses, dwells = self.get_route_and_stop_historical_data(route_name, pathtofile=pathtofile)
        boarding, alighting, transfers_boarding, transfers_alighting = self.get_passenger_historical_data(route_name, pathtofile=pathtofile)

        # Get stop data
        completename = os.path.join(pathtofile, 'route_stops_' + route_name + '_month.txt')
        alltype = np.dtype([('f0','i8'),('f1','i8'),('f2','i8')])
        stops = np.genfromtxt(completename, delimiter=',', dtype=alltype, usecols = [0,1,2], names=True)

        # Cluster historical data
        Headways = self.cluster_bus_headways(headways_between_buses)
        TravelTimes = self.cluster_travel_times_between_stops(stops, stop_to_stop_pairs)
        Dwells = self.cluster_data_at_stops(stops, dwells)
        Boarding = self.cluster_data_at_stops(stops, boarding)
        Alighting = self.cluster_data_at_stops(stops, alighting)
        TBoarding = self.cluster_data_at_stops(stops, transfers_boarding)
        TAlighting = self.cluster_data_at_stops(stops, transfers_alighting)

        return stop_to_stop_pairs, headways_between_buses, dwells, boarding, alighting, transfers_boarding, transfers_alighting, TravelTimes, Dwells, Headways, Boarding, Alighting, TBoarding, TAlighting

    def get_route_and_stop_historical_data(self, route_name, pathtofile):
        completename_frequence = os.path.join(pathtofile, route_name + "_frequence_month.csv")
        alltype=np.dtype([('f0', 'i8'), ('f1', 'i8'), ('f2', 'i8')])
        frequence=np.genfromtxt(completename_frequence, delimiter=",", dtype=alltype , usecols = [0,1,2])
        new_frequence=[]
        for intervalle in frequence:
            new_frequence.append([intervalle[1]],)
        new_frequence=np.array(new_frequence)

        completename_dwells = os.path.join(pathtofile, route_name + "_dwells_month.csv")
        dwells_dict = self.create_data_dict(completename_dwells, passengers = False)
        
        completename_pairs = os.path.join( pathtofile, route_name + "_pairs_month.csv")
        alltype = np.dtype([('f0', 'i8'), ('f1', 'i8'), ('f2', 'i8'), ('f3', 'i8'), ('f4', 'i8')])
        pairs = np.genfromtxt(completename_pairs, delimiter = ',', dtype = alltype, usecols = [0,1,2,3,4])
        pairs_dict = {}
        headers = list(set([(x[0],x[1]) for x in pairs]))
        for (o,d) in headers:
            pairs_dict[(o,d)]=[]
        for x in pairs:
            if x[2]<0: 
                pairs_dict[(x[0],x[1])].append([-x[2]],)
            else: 
                pairs_dict[(x[0],x[1])].append([x[2]],)
        for key in pairs_dict:
            pairs_dict[key] = np.array(pairs_dict[key])
        return(pairs_dict, new_frequence, dwells_dict)

    def get_passenger_historical_data(self, route_name, pathtofile):
        # Boarding passengers
        completename_montants = os.path.join(pathtofile, route_name + "_m_month.csv")
        m_dict = self.create_data_dict(completename_montants)

        # Alighting passengers
        completename_d = os.path.join(pathtofile, route_name + "_d_month.csv")
        d_dict = self.create_data_dict(completename_d)

        # Boarding transferring passengers
        completename_tmontants=os.path.join(pathtofile, route_name + "_tm_month.csv")
        tm_dict = self.create_data_dict(completename_tmontants)

        # Alighting transferring passengers
        completename_td=os.path.join(pathtofile, route_name + "_td_month.csv")
        td_dict = self.create_data_dict(completename_td)
        return(m_dict, d_dict, tm_dict, td_dict)

    def create_data_dict(self, completename, passengers = True):
        alltype = np.dtype([('f0','i8'),('f1','i8'),('f2','i8'),('f3','i8')])
        data = np.genfromtxt(completename, delimiter = ',', dtype = alltype, usecols = [0,1,2,3])
        data_dict = {}
        headers = np.unique([x[0] for x in data])
        for stop in headers:
            data_dict[stop] = []
        for row in data: 
            if row[1] != 0:
                data_dict[row[0]].append([row[1]],)
        empty=[]
        for key in data_dict: 
            if data_dict[key] == []:
                empty.append(key)
        if passengers: 
            for key in empty:
                data_dict[key].append([0],)
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
            current_stop_id = stops[i][1]
            next_stop_id = stops[i+1][1]
            if (current_stop_id, next_stop_id) in consecutive_stop_pairs:
                pair = (current_stop_id, next_stop_id)
                KClusters[pair]=self.cluster_data(consecutive_stop_pairs[pair])
            else:
                count+=1
        print('Number of non-existant pairs: ', count)
        return(KClusters)
    
    def cluster_data_at_stops(self,
                              stops : np.array,
                              data_at_stops : dict):
        count = 0
        KClusters={}
        for x in stops:
            stop=x[1]
            if stop in data_at_stops:
                KClusters[stop] = self.cluster_data(data_at_stops[stop])
            else:
                count+=1
        return(KClusters)
    
    def cluster_bus_headways(self, headways_between_buses : dict):
        KClusters={}
        U = headways_between_buses
        k = 3
        (n,m) = U.shape
        C, clusters = self.kmeans(U, k)
        KClusters = (C, clusters)
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
                    distances[j] = self.dist(U[i], C[j], None) # distance between U[i] and each center of cluster, distances has k values
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
    
