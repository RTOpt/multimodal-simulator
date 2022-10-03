import logging

from multimodalsim.optimization.state import State
from multimodalsim.simulator.event import Event
import multimodalsim.simulator.optimization_event_process as optimization_event_process
from multimodalsim.simulator.status import PassengersStatus
from multimodalsim.simulator.vehicle_event_process import VehicleBoarded

logger = logging.getLogger(__name__)


class PassengerRelease(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerRelease', queue, trip.release_time)
        self.__trip = trip

    def process(self, env):
        env.add_trip(self.__trip)
        env.add_non_assigned_trip(self.__trip)

        legs = env.optimization.split(self.__trip, env)

        self.__trip.assign_legs(legs)

        self.__trip.status = PassengersStatus.RELEASE

        if not self.queue.is_event_type_in_queue(optimization_event_process.Optimize, env.current_time):
            optimization_event_process.Optimize(env.current_time, self.queue).add_to_queue()

        return 'Passenger Release process is implemented'


class PassengerAssignment(Event):
    def __init__(self, passenger_update, queue):
        super().__init__('PassengerAssignment', queue)
        self.__passenger_update = passenger_update

    def process(self, env):

        trip = env.get_trip_by_id(self.__passenger_update.request_id)
        vehicle = env.get_vehicle_by_id(self.__passenger_update.assigned_vehicle_id)

        if self.__passenger_update.next_legs is not None:
            trip.current_leg = self.__passenger_update.current_leg
            trip.next_legs = self.__passenger_update.next_legs

        trip.current_leg.assigned_vehicle = vehicle

        trip.status = PassengersStatus.ASSIGNED

        env.remove_non_assigned_trip(trip.id)
        env.add_assigned_trip(trip)

        PassengerReady(trip, self.queue).add_to_queue()

        return 'Passenger Assignment process is implemented'


class PassengerReady(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerReady', queue, max(trip.ready_time, queue.env.current_time))
        self.trip = trip

    def process(self, env):
        self.trip.status = PassengersStatus.READY
        return 'Passenger Ready process is implemented'


class PassengerToBoard(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerToBoard', queue, max(trip.ready_time, queue.env.current_time))
        self.__trip = trip

    def process(self, env):
        self.__trip.status = PassengersStatus.ONBOARD

        VehicleBoarded(self.__trip, self.queue).add_to_queue()

        return 'Passenger To Board process is implemented'


class PassengerAlighting(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerAlighting', queue)
        self.__trip = trip

    def process(self, env):

        if hasattr(self.__trip, 'next_legs') is False or self.__trip.next_legs is None or len(
                self.__trip.next_legs) == 0:
            # No connection
            logger.debug("No connection")
            self.__trip.status = PassengersStatus.COMPLETE
        else:
            # Connection
            logger.debug("Connection")
            self.__trip.previous_legs.append(self.__trip.current_leg)
            self.__trip.current_leg = self.__trip.next_legs.pop(0)
            self.__trip.assigned_vehicle = self.__trip.current_leg.assigned_vehicle
            self.__trip.status = PassengersStatus.RELEASE

            # The trip is considered as non-assigned again
            env.remove_assigned_trip(self.__trip.id)
            env.add_non_assigned_trip(self.__trip)

            if not self.queue.is_event_type_in_queue(optimization_event_process.Optimize, env.current_time):
                optimization_event_process.Optimize(env.current_time, self.queue).add_to_queue()

        return 'Passenger Alighting process is implemented'
