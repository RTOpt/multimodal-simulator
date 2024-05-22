import logging

from multimodalsim.simulator.event import Event, ActionEvent
import multimodalsim.simulator.optimization_event \
    as optimization_event_process
from multimodalsim.simulator.vehicle_event import VehicleBoarded, \
    VehicleAlighted

logger = logging.getLogger(__name__)


class PassengerRelease(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerRelease', queue, trip.release_time)
        self.__trip = trip

    @property
    def trip(self):
        return self.__trip

    def _process(self, env):
        env.add_trip(self.__trip)
        env.add_non_assigned_trip(self.__trip)

        if self.__trip.current_leg is None:
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
        # if 'walk' in self.__trip.next_legs[0].id or ('walk' in self.__trip.current_leg.id if self.__trip.current_leg is not None else False):
        #     print('Assigned walk leg: ', self.__trip.id)
        #     print('Passenger assigned to walk vehicle: ', self.__trip.id)
        #     print('Passenger current leg: ', self.__trip.current_leg.id if self.__trip.current_leg is not None else None)
        #     print('Passenger update current leg: ', self.__passenger_update.current_leg.id if self.__passenger_update.current_leg is not None else None)
        #     print('Passenger next legs: ', [leg.id for leg in self.__trip.next_legs] if self.__trip.next_legs is not None else None)
        #     print('Passenger update next legs: ', [leg.id for leg in self.__passenger_update.next_legs] if self.__passenger_update.next_legs is not None else None)
        #     print('Passenger assigned to walk vehicle: ', vehicle.id)
        #     input('Press Enter to continue...')
        
        if self.__passenger_update.current_leg is not None:
            self.__trip.current_leg =\
                self.__env.get_leg_by_id(self.__passenger_update.current_leg.id)
            
        if self.__passenger_update.next_legs is not None:
            self.__trip.next_legs =\
                self.__replace_copy_legs_with_actual_legs(
                    self.__passenger_update.next_legs)

        self.__trip.next_legs[0].assigned_vehicle = vehicle

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
                         state_machine=trip.state_machine,
                         event_priority=Event.HIGH_PRIORITY)
        self.__trip = trip
        # if 'walk' in trip.next_legs[0].id or ('walk' in trip.current_leg.id if trip.current_leg is not None else False):
        #     print('Ready walk leg: ', trip.id)
        #     input('Press Enter to continue...')

    def _process(self, env):
        return 'Passenger Ready process is implemented'


class PassengerToBoard(ActionEvent):
    def __init__(self, trip, queue):
        super().__init__('PassengerToBoard', queue,
                         max(trip.ready_time, queue.env.current_time),
                         state_machine=trip.state_machine)
        # if 'walk' in trip.next_legs[0].id or ('walk' in trip.current_leg.id if trip.current_leg is not None else False):
        #     print('ToBoard walk leg: ', trip.id)
        #     input('Press Enter to continue...')
        self.__trip = trip

    def _process(self, env):
        # input('Passenger to board: ' + self.__trip.id)
        self.__trip.start_next_leg()
        self.__trip.current_leg.boarding_time = env.current_time

        VehicleBoarded(self.__trip, self.queue).add_to_queue()

        return 'Passenger To Board process is implemented'


class PassengerAlighting(ActionEvent):
    def __init__(self, trip, queue):
        super().__init__('PassengerAlighting', queue,
                         state_machine=trip.state_machine)
        self.__trip = trip

    def _process(self, env):
        ### Show trip information
        print('Alighting trip: ', self.__trip.id)
        print('Alighting current leg: ', self.__trip.current_leg.id if self.__trip.current_leg is not None else None)
        print('Alighting next legs: ', [leg.id for leg in self.__trip.next_legs] if self.__trip.next_legs is not None else None)
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
            print('trip id: ', self.__trip.id, ' is added to non_assigned_trips bis.')
            # input()

            # if 'walk' in self.__trip.next_legs[0].id: 
            #     print('Next leg is WALKING: ', self.__trip.next_legs[0].id)
            #     input('Press Enter to continue...')

            optimization_event_process.Optimize(
                env.current_time, self.queue).add_to_queue()

        return 'Passenger Alighting process is implemented'
