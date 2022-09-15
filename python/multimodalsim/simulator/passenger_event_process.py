import logging

from python.multimodalsim.simulator.event import Event
from python.multimodalsim.simulator.optimization_event_process import Optimize
from python.multimodalsim.simulator.status import PassengersStatus
from python.multimodalsim.simulator.vehicle_event_process import VehicleBoarded

logger = logging.getLogger(__name__)


class PassengerRelease(Event):
    def __init__(self, request_data_dict, queue):
        super().__init__('PassengerRelease', queue, request_data_dict['release_time'])
        self.request_data_dict = request_data_dict

    def process(self, env):
        trip = env.add_trip(self.request_data_dict['nb_requests'], self.request_data_dict['origin'],
                            self.request_data_dict['destination'], self.request_data_dict['nb_passengers'],
                            self.request_data_dict['ready_time'], self.request_data_dict['due_time'],
                            self.request_data_dict['release_time'])

        legs = env.optimization.split(trip, env)
        trip.assign_legs(legs)

        logger.debug("legs={}".format(legs))
        logger.debug("trip={}".format(trip))

        trip.update_status(PassengersStatus.RELEASE)

        Optimize(env.current_time, self.queue).add_to_queue()

        return 'Passenger Release process is implemented'


class PassengerAssignment(Event):
    def __init__(self, passenger_update, queue):
        super().__init__('PassengerAssignment', queue)
        self.passenger_update = passenger_update

    def process(self, env):

        trip = env.get_trip_by_id(self.passenger_update.request_id)
        vehicle = env.get_vehicle_by_id(self.passenger_update.assigned_vehicle_id)

        if self.passenger_update.next_legs is not None:
            trip.current_leg = self.passenger_update.current_leg
            trip.next_legs = self.passenger_update.next_legs

            # Replace the vehicle copy of each leg with the actual vehicle object.
            # for leg in trip.next_legs:
            #     leg_vehicle = env.get_vehicle_by_id(leg.assigned_vehicle.id)
            #     leg.assigned_vehicle = leg_vehicle

            # Assign the first leg to current_leg.
            # trip.current_leg = trip.next_legs.pop(0)

        trip.current_leg.assign_vehicle(vehicle)

        trip.update_status(PassengersStatus.ASSIGNED)

        PassengerReady(trip, self.queue).add_to_queue()

        return 'Passenger Assignment process is implemented'


class PassengerReady(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerReady', queue, max(trip.ready_time, queue.env.current_time))
        self.trip = trip

    def process(self, env):
        self.trip.update_status(PassengersStatus.READY)
        return 'Passenger Ready process is implemented'


class PassengerToBoard(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerToBoard', queue, max(trip.ready_time, queue.env.current_time))
        self.trip = trip

    def process(self, env):
        self.trip.update_status(PassengersStatus.ONBOARD)

        VehicleBoarded(self.trip, self.queue).add_to_queue()

        return 'Passenger To Board process is implemented'


class PassengerAlighting(Event):
    def __init__(self, trip, queue):
        super().__init__('PassengerAlighting', queue)
        self.trip = trip

    def process(self, env):

        if hasattr(self.trip, 'next_legs') is False or self.trip.next_legs is None or len(
                self.trip.next_legs) == 0:
            # No connection
            logger.debug("No connection")
            self.trip.update_status(PassengersStatus.COMPLETE)
        else:
            # Connection
            logger.debug("Connection")
            self.trip.previous_legs.append(self.trip.current_leg)
            self.trip.current_leg = self.trip.next_legs.pop(0)
            logger.debug("self.trip.current_leg.assigned_vehicle={}".format(self.trip.current_leg.assigned_vehicle))
            self.trip.assigned_vehicle = self.trip.current_leg.assigned_vehicle
            logger.debug("self.trip.assigned_vehicle={}".format(self.trip.assigned_vehicle))
            self.trip.update_status(PassengersStatus.RELEASE)
            Optimize(env.current_time, self.queue).add_to_queue()
        return 'Passenger Alighting process is implemented'
