from event import Event
# from optimization_event_process import *
from optimization_event_process import Optimize
from python.simulator.vehicle_event_process import VehicleBoarded
from request import *


class PassengerRelease(Event):
    def __init__(self, queue, request_data_dict):
        super().__init__('PassengerRelease', queue, request_data_dict['release_time'])
        self.request_data_dict = request_data_dict

    def process(self, env):
        # TODO : modify release to wait assignment

        request = env.add_request(self.request_data_dict['nb_requests'], self.request_data_dict['origin'],
                                  self.request_data_dict['destination'], self.request_data_dict['nb_passengers'],
                                  self.request_data_dict['ready_time'], self.request_data_dict['due_time'],
                                  self.request_data_dict['release_time'])

        request.update_passenger_status(PassengersStatus.RELEASE)

        # Start optimization
        Optimize(env.current_time, self.queue).add_to_queue()
        return 'Passenger Release process is implemented'


class PassengerAssignment(Event):
    # def __init__(self, passenger_update, queue):
    #     #TODO : passenger_update
    #     super().__init__('PassengerAssignment', passenger_update.release_time, queue)
    #     self.passenger_update = passenger_update

    def __init__(self, passenger_update, queue):
        # TODO : passenger_update
        super().__init__('PassengerAssignment', queue)
        self.passenger_update = passenger_update
        # self.request = request

    def process(self, env):

        request = env.get_request_by_id(self.passenger_update.request_id)
        vehicle = env.get_vehicle_by_id(self.passenger_update.assigned_vehicle_id)

        request.assign_vehicle(vehicle)

        # Patrick: Do we assign the Request to the Vehicle here or in VehicleNotification?
        vehicle.route.assign(request)

        # Patrick: Where do we update the (non)-assigned requests/vehicles in the environment?

        # Mettre à jour l'objet Request (ou Trip) assign
        # Patrick: Why is the status READY? Shouldn't it be ASSIGNMENT?
        request.update_passenger_status(PassengersStatus.ASSIGNED)

        # le cas ou la date de release différente de la ready date
        PassengerReady(request, self.queue).add_to_queue()

        return 'Passenger Assignment process is implemented'


class PassengerReady(Event):
    def __init__(self, request, queue):
        # max(ready_time, current_time)
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
        # End of process
        self.request.update_passenger_status(PassengersStatus.ONBOARD)

        VehicleBoarded(self.request, self.queue).add_to_queue()

        return 'Passenger To Board process is implemented'


class PassengerAlighting(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerAlighting', queue)
        self.request = request

    def process(self, env):
        self.request.update_passenger_status(PassengersStatus.COMPLETE)
        return 'Passenger Alighting process is implemented'
