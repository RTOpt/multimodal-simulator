import logging

from event import Event
from optimization_event_process import Optimize
from python.simulator.vehicle_event_process import VehicleBoarded
from request import *

logger = logging.getLogger(__name__)


class PassengerRelease(Event):
    def __init__(self, request_data_dict, queue):
        super().__init__('PassengerRelease', queue, request_data_dict['release_time'])
        self.request_data_dict = request_data_dict

    def process(self, env):

        request = env.add_request(self.request_data_dict['nb_requests'], self.request_data_dict['origin'],
                                  self.request_data_dict['destination'], self.request_data_dict['nb_passengers'],
                                  self.request_data_dict['ready_time'], self.request_data_dict['due_time'],
                                  self.request_data_dict['release_time'])

        request.update_passenger_status(PassengersStatus.RELEASE)

        Optimize(env.current_time, self.queue).add_to_queue()

        return 'Passenger Release process is implemented'


class PassengerAssignment(Event):
    def __init__(self, passenger_update, queue):
        super().__init__('PassengerAssignment', queue)
        self.passenger_update = passenger_update

    def process(self, env):

        request = env.get_request_by_id(self.passenger_update.request_id)
        vehicle = env.get_vehicle_by_id(self.passenger_update.assigned_vehicle_id)

        if self.passenger_update.next_legs is not None:
            request.next_legs = self.passenger_update.next_legs

            # Replace the vehicle copy of each leg with the actual vehicle object.
            for leg in request.next_legs:
                leg_vehicle = env.get_vehicle_by_id(leg.assigned_vehicle.id)
                leg.assigned_vehicle = leg_vehicle

            # Assign the first leg to current_leg.
            request.current_leg = request.next_legs.pop(0)

        request.assign_vehicle(vehicle)

        request.update_passenger_status(PassengersStatus.ASSIGNED)

        PassengerReady(request, self.queue).add_to_queue()

        return 'Passenger Assignment process is implemented'


class PassengerReady(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerReady', queue, max(request.ready_time, queue.env.current_time))
        self.request = request

    def process(self, env):
        self.request.update_passenger_status(PassengersStatus.READY)
        return 'Passenger Ready process is implemented'


class PassengerToBoard(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerToBoard', queue, max(request.ready_time, queue.env.current_time))
        self.request = request

    def process(self, env):
        self.request.update_passenger_status(PassengersStatus.ONBOARD)

        VehicleBoarded(self.request, self.queue).add_to_queue()

        return 'Passenger To Board process is implemented'


class PassengerAlighting(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerAlighting', queue)
        self.request = request

    def process(self, env):

        # logger.debug("PassengerAlighting(Event)")
        # logger.debug("hasattr(self.request, 'next_legs')={}".format(hasattr(self.request, 'next_legs')))
        # logger.debug("self.request.next_legs={}".format(self.request.next_legs))
        # logger.debug("len(self.request.next_legs)={}".format(len(self.request.next_legs)))

        if hasattr(self.request, 'next_legs') is False or self.request.next_legs is None or len(self.request.next_legs) == 0:
            # No connection
            logger.debug("No connection")
            self.request.update_passenger_status(PassengersStatus.COMPLETE)
        else:
            # Connection: Request is a Trip
            logger.debug("Connection")
            self.request.previous_legs.append(self.request.current_leg)
            self.request.current_leg = self.request.next_legs.pop(0)
            logger.debug("self.request.assigned_vehicle={}".format(self.request.assigned_vehicle))
            self.request.assigned_vehicle = self.request.current_leg.assigned_vehicle
            logger.debug("self.request.assigned_vehicle={}".format(self.request.assigned_vehicle))
            self.request.update_passenger_status(PassengersStatus.RELEASE)
            # self.request.update_passenger_status(PassengersStatus.READY)
        return 'Passenger Alighting process is implemented'
