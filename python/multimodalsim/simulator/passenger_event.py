from multimodalsim.simulator.event import Event, ActionEvent
import multimodalsim.simulator.optimization_event \
    as optimization_event_process
import multimodalsim.simulator.request as request
from multimodalsim.simulator.vehicle_event import VehicleBoarded, \
    VehicleAlighted
import multimodalsim.simulator.environment as environment
import multimodalsim.simulator.event_queue as event_queue

import logging
from typing import Optional


logger = logging.getLogger(__name__)


class PassengerRelease(ActionEvent):
    def __init__(self, trip: 'request.Trip',
                 queue: 'event_queue.EventQueue') -> None:
        super().__init__('PassengerRelease', queue, trip.release_time,
                         state_machine=trip.state_machine)
        self.__trip = trip

    @property
    def trip(self) -> 'request.Trip':
        return self.__trip

    def _process(self, env: 'environment.Environment') -> str:

        env.add_trip(self.__trip)
        env.add_non_assigned_trip(self.__trip)

        if self.__trip.current_leg is None:
            legs = env.optimization.split(self.__trip, env)
            self.__trip.assign_legs(legs)

        return 'Passenger Release process is implemented'


class PassengerAssignment(ActionEvent):
    def __init__(self, trip_id: str | int,
                 queue: 'event_queue.EventQueue',
                 passenger_update: Optional['request.PassengerUpdate']
                 = None) -> None:
        self.__passenger_update = passenger_update
        self.__trip = queue.env.get_trip_by_id(trip_id)
        super().__init__('PassengerAssignment', queue,
                         state_machine=self.__trip.state_machine)

    def _process(self, env: 'environment.Environment') -> str:

        if self.__passenger_update is not None:
            self.__env = env

            self.__update_legs()

            self.__assign_vehicle()

            self.__update_environment()

        PassengerReady(self.__trip, self.queue).add_to_queue()

        return 'Passenger Assignment process is implemented'

    def __update_legs(self):
        if self.__passenger_update.current_leg is not None:
            self.__trip.current_leg = \
                self.__replace_copy_leg_with_actual_leg(
                    self.__passenger_update.current_leg)
            self.__update_current_leg(self.__trip.current_leg,
                                      self.__passenger_update.current_leg)

        if self.__passenger_update.next_legs is not None:
            self.__trip.next_legs =\
                self.__replace_copy_legs_with_actual_legs(
                    self.__passenger_update.next_legs)
            self.__update_next_legs(self.__trip.next_legs,
                               self.__passenger_update.next_legs)

    def __update_current_leg(self, current_leg_actual: 'request.Leg',
                             current_leg_copy: 'request.Leg'):
        """Update future information about the current leg."""
        current_leg_actual.destination = current_leg_copy.destination

    def __update_next_legs(self, next_legs_actual_list: list['request.Leg'],
                          next_legs_copy_list: list['request.Leg']):
        """Update information about the next leg."""
        for next_leg_actual, next_leg_copy in zip(next_legs_actual_list, next_legs_copy_list):
            if next_leg_copy.assigned_vehicle is not None:
                next_leg_actual.assigned_vehicle = \
                    self.__env.get_vehicle_by_id(
                        next_leg_copy.assigned_vehicle.id)
            else:
                next_leg_actual.assigned_vehicle = None
            next_leg_actual.origin = next_leg_copy.origin
            next_leg_actual.destination = next_leg_copy.destination

    def __assign_vehicle(self):
        # Vehicle of the first next leg. Note that the vehicle of the current
        # leg cannot be modified.
        vehicle = self.__env.get_vehicle_by_id(
            self.__passenger_update.assigned_vehicle_id)
        self.__trip.next_legs[0].assigned_vehicle = vehicle

    def __update_environment(self):
        self.__env.remove_non_assigned_trip(self.__trip.id)
        self.__env.add_assigned_trip(self.__trip)

    def __replace_copy_legs_with_actual_legs(self, legs):
        # Replace the Leg objects in argument with the Leg objects of same id
        # from the environment. If no leg with same id is found in the
        # environment, then the leg as argument is considered to be the actual
        # leg.
        actual_legs_list = []
        for leg in legs:
            actual_leg = self.__replace_copy_leg_with_actual_leg(leg)
            actual_legs_list.append(actual_leg)

        return actual_legs_list

    def __replace_copy_leg_with_actual_leg(self, leg):
        # Replace the Leg object in argument with the Leg object of same id
        # from the environment. If no leg with same id is found in the
        # environment, then the leg as argument is considered to be the actual
        # leg.
        actual_leg = self.__env.get_leg_by_id(leg.id)
        if actual_leg is None:
            # A new leg was created during optimization
            actual_leg = self.__create_actual_leg_from_leg_copy(leg)

        return actual_leg

    def __create_actual_leg_from_leg_copy(self, leg):
        actual_trip = self.__env.get_trip_by_id(leg.trip.id)

        actual_assigned_vehicle = None
        if leg.assigned_vehicle is not None:
            actual_assigned_vehicle = self.__env.get_vehicle_by_id(
                leg.assigned_vehicle.id)

        leg.trip = actual_trip
        leg.assigned_vehicle = actual_assigned_vehicle

        # actual_leg = request.Leg(leg.id, leg.origin, leg.destination,
        #                  leg.nb_passengers, leg.release_time, leg.ready_time,
        #                  leg.due_time, actual_trip)
        # actual_leg.assigned_vehicle = actual_assigned_vehicle

        return leg

class PassengerReady(ActionEvent):
    def __init__(self, trip: 'request.Trip',
                 queue: 'event_queue.EventQueue') -> None:
        super().__init__('PassengerReady', queue,
                         max(trip.ready_time, queue.env.current_time),
                         state_machine=trip.state_machine,
                         event_priority=Event.HIGH_PRIORITY)
        self.__trip = trip

    def _process(self, env: 'environment.Environment') -> str:
        return 'Passenger Ready process is implemented'


class PassengerToBoard(ActionEvent):
    def __init__(self, trip: 'request.Trip',
                 queue: 'event_queue.EventQueue') -> None:
        super().__init__('PassengerToBoard', queue,
                         max(trip.ready_time, queue.env.current_time),
                         state_machine=trip.state_machine)
        self.__trip = trip

    def _process(self, env: 'environment.Environment') -> str:
        self.__trip.start_next_leg()
        self.__trip.current_leg.boarding_time = env.current_time

        VehicleBoarded(self.__trip, self.queue).add_to_queue()

        return 'Passenger To Board process is implemented'


class PassengerAlighting(ActionEvent):
    def __init__(self, trip: 'request.Trip',
                 queue: 'event_queue.EventQueue') -> None:
        super().__init__('PassengerAlighting', queue,
                         state_machine=trip.state_machine)
        self.__trip = trip

    def _process(self, env: 'environment.Environment') -> str:

        self.__trip.current_leg.alighting_time = env.current_time

        VehicleAlighted(self.__trip.current_leg, self.queue).add_to_queue()

        self.__trip.finish_current_leg()

        if self.__trip.next_legs is None or len(self.__trip.next_legs) == 0:
            # No connection
            logger.debug("No connection: {}".format(self.__trip.id))
        else:
            # Connection
            logger.debug("Connection: {}".format(self.__trip.id))

            # The trip is considered as non-assigned again
            env.remove_assigned_trip(self.__trip.id)
            env.add_non_assigned_trip(self.__trip)

            if self.__trip.next_legs[0].assigned_vehicle is not None:
                # Next leg has already been assigned to a vehicle.
                PassengerAssignment(self.__trip.id, self.queue).add_to_queue()

        return 'Passenger Alighting process is implemented'


class PassengerUnassignment(ActionEvent):
    def __init__(self, trip: 'request.Trip',
                 queue: 'event_queue.EventQueue') -> None:
        super().__init__('PassengerUnassignment', queue,
                         state_machine=trip.state_machine)
        self.__trip = trip

    @property
    def trip(self) -> 'request.Trip':
        return self.__trip

    def _process(self, env: 'environment.Environment') -> str:

        env.remove_assigned_trip(self.__trip)
        env.add_non_assigned_trip(self.__trip)
        self.__trip.next_legs[0].assigned_vehicle = None

        return 'Passenger Unassignment process is implemented'
