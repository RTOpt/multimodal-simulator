from event import Event
from optimization_event_process import Optimize
from python.simulator.vehicle_event_process import VehicleBoarded
from request import *


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

        if self.passenger_update.next_vehicles_ids is not None:
            next_vehicles = [env.get_vehicle_by_id(veh_id) for veh_id in self.passenger_update.next_vehicles_ids]
        else:
            next_vehicles = None

        request.assign_vehicle(vehicle)
        request.next_vehicles = next_vehicles

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
        if self.request.next_vehicles is None or len(self.request.next_vehicles) == 0:
            self.request.update_passenger_status(PassengersStatus.COMPLETE)
        else:
            self.request.previous_vehicles.append(self.request.assigned_vehicle)
            self.request.assigned_vehicle = self.request.next_vehicles.pop(0)
            self.request.update_passenger_status(PassengersStatus.READY)
        return 'Passenger Alighting process is implemented'
