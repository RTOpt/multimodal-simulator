import logging

from multimodalsim.simulator.event import Event
import multimodalsim.simulator.optimization_event_process as optimization_event_process
from multimodalsim.simulator.vehicle_event_process import VehicleBoarded
from multimodalsim.state_machine.decorator import next_state

logger = logging.getLogger(__name__)


class PassengerRelease(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerRelease', queue, trip.release_time, state_machine=trip.state_machine)
        self.__trip = trip

    @next_state
    def process(self, env):

        env.add_trip(self.__trip)
        env.add_non_assigned_trip(self.__trip)

        legs = env.optimization.split(self.__trip, env)

        self.__trip.assign_legs(legs)

        if not self.queue.is_event_type_in_queue(optimization_event_process.Optimize, env.current_time):
            optimization_event_process.Optimize(env.current_time, self.queue).add_to_queue()

        return 'Passenger Release process is implemented'


class PassengerAssignment(Event):
    def __init__(self, passenger_update, queue):
        self.__passenger_update = passenger_update
        self.__trip = queue.env.get_trip_by_id(self.__passenger_update.request_id)
        super().__init__('PassengerAssignment', queue, state_machine=self.__trip.state_machine)

    @next_state
    def process(self, env):

        vehicle = env.get_vehicle_by_id(self.__passenger_update.assigned_vehicle_id)

        if self.__passenger_update.next_legs is not None:
            self.__trip.current_leg = self.__passenger_update.current_leg
            self.__trip.next_legs = self.__passenger_update.next_legs

        self.__trip.current_leg.assigned_vehicle = vehicle

        env.remove_non_assigned_trip(self.__trip.id)
        env.add_assigned_trip(self.__trip)

        PassengerReady(self.__trip, self.queue).add_to_queue()

        return 'Passenger Assignment process is implemented'


class PassengerReady(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerReady', queue, max(trip.ready_time, queue.env.current_time),
                         state_machine=trip.state_machine)
        self.__trip = trip

    @next_state
    def process(self, env):
        return 'Passenger Ready process is implemented'


class PassengerToBoard(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerToBoard', queue, max(trip.ready_time, queue.env.current_time),
                         state_machine=trip.state_machine)
        self.__trip = trip

    @next_state
    def process(self, env):
        VehicleBoarded(self.__trip, self.queue).add_to_queue()

        return 'Passenger To Board process is implemented'


class PassengerAlighting(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerAlighting', queue, state_machine=trip.state_machine)
        self.__trip = trip

    @next_state
    def process(self, env):

        if self.__trip.next_legs is None or len(self.__trip.next_legs) == 0:
            # No connection
            logger.debug("No connection")
        else:
            # Connection
            logger.debug("Connection")
            self.__trip.previous_legs.append(self.__trip.current_leg)
            self.__trip.current_leg = self.__trip.next_legs.pop(0)
            self.__trip.assigned_vehicle = self.__trip.current_leg.assigned_vehicle

            # The trip is considered as non-assigned again
            env.remove_assigned_trip(self.__trip.id)
            env.add_non_assigned_trip(self.__trip)

            if not self.queue.is_event_type_in_queue(optimization_event_process.Optimize, env.current_time):
                optimization_event_process.Optimize(env.current_time, self.queue).add_to_queue()

        return 'Passenger Alighting process is implemented'
