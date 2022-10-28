import logging

from multimodalsim.simulator.event import Event, ActionEvent
import multimodalsim.simulator.optimization_event \
    as optimization_event_process
from multimodalsim.simulator.vehicle_event import VehicleBoarded

logger = logging.getLogger(__name__)


class PassengerRelease(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerRelease', queue, trip.release_time)
        self.__trip = trip

    def _process(self, env):
        env.add_trip(self.__trip)
        env.add_non_assigned_trip(self.__trip)

        legs = env.optimization.split(self.__trip, env)

        self.__trip.assign_legs(legs)

        optimization_event_process.Optimize(
            env.current_time, self.queue).add_to_queue()

        return 'Passenger Release process is implemented'


class PassengerAssignment(ActionEvent):
    def __init__(self, passenger_update, queue):
        self.__passenger_update = passenger_update
        self.__trip = queue.env.get_trip_by_id(
            self.__passenger_update.request_id)
        super().__init__('PassengerAssignment', queue,
                         state_machine=self.__trip.state_machine)

    def _process(self, env):
        self.__env = env
        vehicle = env.get_vehicle_by_id(
            self.__passenger_update.assigned_vehicle_id)

        if self.__passenger_update.next_legs is not None:
            self.__trip.current_leg =\
                self.__replace_copy_legs_with_actual_legs(
                    self.__passenger_update.current_leg)
            self.__trip.next_legs =\
                self.__replace_copy_legs_with_actual_legs(
                    self.__passenger_update.next_legs)

        self.__trip.current_leg.assigned_vehicle = vehicle

        env.remove_non_assigned_trip(self.__trip.id)
        env.add_assigned_trip(self.__trip)

        PassengerReady(self.__trip, self.queue).add_to_queue()

        return 'Passenger Assignment process is implemented'

    def __replace_copy_legs_with_actual_legs(self, legs):
        if type(legs) is list:
            actual_legs = list(
                self.__env.get_leg_by_id(leg.id) for leg in legs)
        else:
            actual_legs = self.__env.get_leg_by_id(legs.id)

        return actual_legs


class PassengerReady(ActionEvent):
    def __init__(self, trip, queue):
        super().__init__('PassengerReady', queue,
                         max(trip.ready_time, queue.env.current_time),
                         state_machine=trip.state_machine)
        self.__trip = trip

    def _process(self, env):
        return 'Passenger Ready process is implemented'


class PassengerToBoard(ActionEvent):
    def __init__(self, trip, queue):
        super().__init__('PassengerToBoard', queue,
                         max(trip.ready_time, queue.env.current_time),
                         state_machine=trip.state_machine)
        self.__trip = trip

    def _process(self, env):
        VehicleBoarded(self.__trip, self.queue).add_to_queue()

        return 'Passenger To Board process is implemented'


class PassengerAlighting(ActionEvent):
    def __init__(self, trip, queue):
        super().__init__('PassengerAlighting', queue,
                         state_machine=trip.state_machine)
        self.__trip = trip

    def _process(self, env):

        if self.__trip.next_legs is None or len(self.__trip.next_legs) == 0:
            # No connection
            logger.debug("No connection")
        else:
            # Connection
            logger.debug("Connection")
            self.__trip.previous_legs.append(self.__trip.current_leg)
            self.__trip.current_leg = self.__trip.next_legs.pop(0)
            self.__trip.assigned_vehicle = \
                self.__trip.current_leg.assigned_vehicle

            # The trip is considered as non-assigned again
            env.remove_assigned_trip(self.__trip.id)
            env.add_non_assigned_trip(self.__trip)

            optimization_event_process.Optimize(
                env.current_time, self.queue).add_to_queue()

        return 'Passenger Alighting process is implemented'
