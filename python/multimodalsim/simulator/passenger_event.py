import logging

from multimodalsim.simulator.event import Event, ActionEvent
import multimodalsim.simulator.optimization_event \
    as optimization_event_process
import multimodalsim.simulator.request as request
from multimodalsim.simulator.vehicle_event import VehicleBoarded, \
    VehicleAlighted
import multimodalsim.simulator.environment as environment
import multimodalsim.simulator.event_queue as event_queue

logger = logging.getLogger(__name__)


class PassengerRelease(Event):
    def __init__(self, trip: 'request.Trip',
                 queue: 'event_queue.EventQueue') -> None:
        super().__init__('PassengerRelease', queue, trip.release_time)
        self.__trip = trip

    @property
    def trip(self) -> 'request.Trip':
        return self.__trip

    def _process(self, env: 'environment.Environment') -> str:

        self.__env = env

        if env.get_trip_by_id(self.__trip) is None:
            # Adding new trip to the environment
            self.__release_new_trip()
        else:
            # Unassignement of existing trip (no re-optimization is triggered)
            self.__release_existing_trip()

        return 'Passenger Release process is implemented'

    def __release_new_trip(self):
        self.__env.add_trip(self.__trip)
        self.__env.add_non_assigned_trip(self.__trip)

        if self.__trip.current_leg is None:
            legs = self.__env.optimization.split(self.__trip, self.__env)
            self.__trip.assign_legs(legs)

        optimization_event_process.Optimize(
            self.__env.current_time, self.queue).add_to_queue()

    def __release_existing_trip(self):
        self.__env.remove_assigned_trip(self.__trip)
        self.__env.add_non_assigned_trip(self.__trip)
        self.__trip.current_leg.assigned_vehicle = None


class PassengerAssignment(ActionEvent):
    def __init__(self, passenger_update: 'request.PassengerUpdate',
                 queue: 'event_queue.EventQueue') -> None:
        self.__passenger_update = passenger_update
        self.__trip = queue.env.get_trip_by_id(
            self.__passenger_update.request_id)
        super().__init__('PassengerAssignment', queue,
                         state_machine=self.__trip.state_machine)

    def _process(self, env: 'environment.Environment') -> str:
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

        if self.__passenger_update.next_legs is not None:
            self.__trip.next_legs =\
                self.__replace_copy_legs_with_actual_legs(
                    self.__passenger_update.next_legs)

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
            actual_leg = leg

        return actual_leg


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

            optimization_event_process.Optimize(
                env.current_time, self.queue).add_to_queue()

        return 'Passenger Alighting process is implemented'
