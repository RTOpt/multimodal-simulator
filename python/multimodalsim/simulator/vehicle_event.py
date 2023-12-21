import logging
import copy

from multimodalsim.simulator.event import Event, ActionEvent
from multimodalsim.state_machine.status import VehicleStatus
from multimodalsim.simulator.vehicle import Route

import multimodalsim.simulator.optimization_event \
    as optimization_event
import multimodalsim.simulator.passenger_event \
    as passenger_event

logger = logging.getLogger(__name__)


class VehicleReady(Event):
    def __init__(self, vehicle, route, queue, update_position_time_step=None):
        super().__init__('VehicleReady', queue, vehicle.release_time)
        self.__vehicle = vehicle
        self.__route = route
        self.__update_position_time_step = update_position_time_step

    @property
    def vehicle(self):
        return self.__vehicle

    def _process(self, env):
        env.add_vehicle(self.__vehicle)

        if self.__route is None:
            self.__route = Route(self.__vehicle)

        env.add_route(self.__route, self.__vehicle.id)

        VehicleWaiting(self.__route, self.queue).add_to_queue()

        if env.coordinates is not None and self.__update_position_time_step \
                is not None:
            self.__vehicle.polylines = \
                env.coordinates.update_polylines(self.__route)
            VehicleUpdatePositionEvent(
                self.__vehicle, self.queue,
                self.time + self.__update_position_time_step,
                self.__update_position_time_step).add_to_queue()
        elif env.coordinates is not None:
            self.__vehicle.polylines = \
                env.coordinates.update_polylines(self.__route)

        return 'Vehicle Ready process is implemented'


class VehicleWaiting(ActionEvent):
    def __init__(self, route, queue, time=None):
        time = time if time is not None else queue.env.current_time
        super().__init__('VehicleBoarding', queue, time,
                         state_machine=route.vehicle.state_machine)
        self.__route = route

    def _process(self, env):

        optimization_event.Optimize(env.current_time, self.queue). \
            add_to_queue()

        if len(self.__route.requests_to_pickup()) > 0:
            # Passengers to board
            VehicleBoarding(self.__route, self.queue).add_to_queue()
        elif len(self.__route.next_stops) > 0:
            # No passengers to board
            if self.__route.current_stop.departure_time > env.current_time:
                VehicleWaiting(
                    self.__route, self.queue,
                    self.__route.current_stop.departure_time).add_to_queue()
            else:
                VehicleDeparture(self.__route, self.queue).add_to_queue()
        else:
            # No next stops for now. If the route of the vehicle is not
            # modified, its status will remain IDLE until Vehicle.end_time,
            # at which point the VehicleComplete event will be processed.
            VehicleComplete(self.__route, self.queue).add_to_queue()

        return 'Vehicle Waiting process is implemented'


class VehicleBoarding(ActionEvent):
    def __init__(self, route, queue):
        super().__init__('VehicleBoarding', queue,
                         queue.env.current_time,
                         state_machine=route.vehicle.state_machine)
        self.__route = route

    def _process(self, env):
        passengers_to_board_copy = self.__route.current_stop. \
            passengers_to_board.copy()
        for req in passengers_to_board_copy:
            self.__route.initiate_boarding(req)
            passenger_event.PassengerToBoard(
                req, self.queue).add_to_queue()

        return 'Vehicle Boarding process is implemented'


class VehicleDeparture(ActionEvent):
    def __init__(self, route, queue):
        super().__init__('Vehicle Departure', queue,
                         route.current_stop.departure_time,
                         state_machine=route.vehicle.state_machine)
        self.__route = route

    def _process(self, env):

        if env.travel_times is not None:
            from_stop = copy.deepcopy(self.__route.current_stop)
            to_stop = copy.deepcopy(self.__route.next_stops[0])
            vehicle = copy.deepcopy(self.__route.vehicle)
            actual_arrival_time = env.travel_times.get_expected_arrival_time(
                from_stop, to_stop, vehicle)
        else:
            actual_arrival_time = self.__route.next_stops[0].arrival_time

        self.__route.depart()

        VehicleArrival(self.__route, self.queue,
                       actual_arrival_time).add_to_queue()

        return 'Vehicle Departure process is implemented'


class VehicleArrival(ActionEvent):
    def __init__(self, route, queue, arrival_time):
        super().__init__('VehicleArrival', queue, arrival_time,
                         state_machine=route.vehicle.state_machine)
        self.__route = route

    def _process(self, env):

        self.__update_stop_times(env.current_time)

        self.__route.arrive()

        if len(self.__route.next_stops) == 0 \
                and not self.__route.vehicle.reusable:
            VehicleComplete(self.__route, self.queue,
                            self.queue.env.current_time).add_to_queue(
                forced_insertion=True)

        passengers_to_alight_copy = self.__route.current_stop. \
            passengers_to_alight.copy()
        for trip in passengers_to_alight_copy:
            if trip.current_leg in self.__route.onboard_legs:
                self.__route.initiate_alighting(trip)
                passenger_event.PassengerAlighting(
                    trip, self.queue).add_to_queue()

        if len(passengers_to_alight_copy) == 0:
            VehicleWaiting(self.__route, self.queue).add_to_queue()

        return 'Vehicle Arrival process is implemented'

    def __update_stop_times(self, arrival_time):

        planned_arrival_time = self.__route.next_stops[0].arrival_time
        delta_time = arrival_time - planned_arrival_time

        for stop in self.__route.next_stops:
            stop.arrival_time += delta_time
            if stop.min_departure_time is None:
                new_departure_time = stop.departure_time + delta_time
            else:
                new_departure_time = max(stop.departure_time + delta_time,
                                         stop.min_departure_time)
            delta_time = new_departure_time - stop.departure_time
            stop.departure_time = new_departure_time


class VehicleNotification(Event):
    def __init__(self, route_update, queue):
        self.__env = None
        self.__route_update = route_update
        self.__vehicle = queue.env.get_vehicle_by_id(
            self.__route_update.vehicle_id)
        self.__route = queue.env.get_route_by_vehicle_id(self.__vehicle.id)
        super().__init__('VehicleNotification', queue)

    def _process(self, env):

        self.__env = env

        if self.__route_update.next_stops is not None:
            self.__route.next_stops = \
                copy.deepcopy(self.__route_update.next_stops)
            for stop in self.__route.next_stops:
                self.__update_stop_with_actual_trips(stop)

        if self.__route_update.current_stop_modified_passengers_to_board \
                is not None:
            # Add passengers to board that were modified by optimization and
            # that are not already present in
            # self.__route.current_stop.passengers_to_board
            actual_modified_passengers_to_board = \
                self.__replace_copy_trips_with_actual_trips(
                    self.__route_update.
                    current_stop_modified_passengers_to_board)
            for trip in actual_modified_passengers_to_board:
                logger.error("trip.id={}".format(trip.id))
                logger.error("self.__route.vehicle.id={}".format(
                    self.__route.vehicle.id))
                if trip not in \
                        self.__route.current_stop.passengers_to_board:
                    self.__route.current_stop.passengers_to_board \
                        .append(trip)

        if self.__route_update.current_stop_departure_time is not None \
                and self.__route.current_stop is not None:
            # If self.__route.current_stop.departure_time is equal to
            # env.current_time, then the vehicle may have already left the
            # current stop. In this case self.__route.current_stop should
            # be None (because optimization should not modify current stops
            # when departure time is close to current time), and we do not
            # modify it.
            if self.__route.current_stop.departure_time \
                    != self.__route_update.current_stop_departure_time:
                self.__route.current_stop.departure_time \
                    = self.__route_update.current_stop_departure_time
                VehicleWaiting(self.__route, self.queue).add_to_queue()

        if self.__route_update.modified_assigned_legs is not None:
            # Add the assigned legs that were modified by optimization and
            # that are not already present in self.__route.assigned_legs.
            actual_modified_assigned_legs = \
                self.__replace_copy_legs_with_actual_legs(
                    self.__route_update.modified_assigned_legs)
            for leg in actual_modified_assigned_legs:
                if leg not in self.__route.assigned_legs:
                    self.__route.assigned_legs.append(leg)

        # Update polylines
        if env.coordinates is not None:
            self.__vehicle.polylines = \
                env.coordinates.update_polylines(self.__route)

        return 'Notify Vehicle process is implemented'

    def __update_stop_with_actual_trips(self, stop):

        stop.passengers_to_board = self.__replace_copy_trips_with_actual_trips(
            stop.passengers_to_board)
        stop.boarding_passengers = self.__replace_copy_trips_with_actual_trips(
            stop.boarding_passengers)
        stop.boarded_passengers = self.__replace_copy_trips_with_actual_trips(
            stop.boarded_passengers)
        stop.passengers_to_alight = self \
            .__replace_copy_trips_with_actual_trips(stop.passengers_to_alight)

    def __replace_copy_trips_with_actual_trips(self, trips_list):

        return list(self.__env.get_trip_by_id(req.id) for req in trips_list)

    def __replace_copy_legs_with_actual_legs(self, legs_list):

        return list(self.__env.get_leg_by_id(leg.id) for leg in legs_list)


class VehicleBoarded(Event):
    def __init__(self, trip, queue):
        self.__trip = trip
        self.__route = queue.env.get_route_by_vehicle_id(
            self.__trip.current_leg.assigned_vehicle.id)
        super().__init__('VehicleBoarded', queue)

    def _process(self, env):
        self.__route.board(self.__trip)

        if len(self.__route.current_stop.boarding_passengers) == 0:
            # All passengers are on board
            VehicleWaiting(self.__route, self.queue).add_to_queue()
            # Else we wait until all the boarding passengers are on board
            # before creating the event VehicleWaiting.
        elif len(self.__route.requests_to_pickup()) > 0:
            # Passengers to board
            VehicleBoarding(self.__route, self.queue).add_to_queue()

        return 'Vehicle Boarded process is implemented'


class VehicleAlighted(Event):
    def __init__(self, leg, queue):
        self.__leg = leg
        self.__route = leg.assigned_vehicle
        self.__route = queue.env.get_route_by_vehicle_id(
            leg.assigned_vehicle.id)
        super().__init__('VehicleAlighted', queue)

    def _process(self, env):
        self.__route.alight(self.__leg)

        if len(self.__route.current_stop.alighting_passengers) == 0:
            # All passengers are alighted
            VehicleWaiting(self.__route, self.queue).add_to_queue()
            # Else we wait until all the passengers on board are alighted
            # before creating the event VehicleWaiting.

        return 'Vehicle Alighted process is implemented'


class VehicleUpdatePositionEvent(Event):
    def __init__(self, vehicle, queue, event_time, time_step=None):
        super().__init__("VehicleUpdatePositionEvent", queue, event_time)

        self.__vehicle = vehicle
        self.__route = queue.env.get_route_by_vehicle_id(vehicle.id)
        self.__event_time = event_time
        self.__queue = queue
        self.__time_step = time_step

    def _process(self, env):
        self.__vehicle.position = env.coordinates.update_position(
            self.__vehicle, self.__route, self.__event_time)

        if self.__vehicle.status != VehicleStatus.COMPLETE \
                and self.__time_step is not None:
            VehicleUpdatePositionEvent(
                self.__vehicle, self.__queue,
                self.__event_time + self.__time_step,
                self.__time_step).add_to_queue()

        return 'VehicleUpdatePositionEvent processed'

    @property
    def vehicle(self):
        return self.__vehicle


class VehicleComplete(ActionEvent):
    def __init__(self, route, queue, event_time=None):
        if event_time is None:
            event_time = max(route.vehicle.end_time, queue.env.current_time)
        super().__init__('VehicleComplete', queue, event_time,
                         state_machine=route.vehicle.state_machine,
                         event_priority=Event.LOW_PRIORITY)
        self.__route = route

    def _process(self, env):

        return 'Vehicle Complete process is implemented'

    def add_to_queue(self, forced_insertion=False):
        if not self.queue.is_event_type_in_queue(self.__class__,
                                                 owner=self.__route.vehicle)\
                or forced_insertion:
            super().add_to_queue()
