from event import Event
# from optimization_event_process import *
from optimization_event_process import Optimize
from python.simulator.vehicle_event_process import VehicleBoarded
from request import *


class PassengerRelease(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerRelease', queue, request.release_time)
        self.request = request

    def process(self, env):
        # TODO : modify release to wait assignment
        self.request.update_passenger_status(PassengersStatus.ASSIGNMENT)

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

        print("request.req_id={}".format(request.req_id))
        request.assign_vehicle(vehicle)

        # Patrick: Do we assign the Request to the Vehicle here?
        vehicle.route.assign(request)

        # Patrick: Where do we update the (non)-assigned requests/vehicles in the environment?

        # Mettre à jour l'objet Request (ou Trip) assign
        # Patrick: Why is the status READY? Shouldn't it be ASSIGNMENT?
        request.update_passenger_status(PassengersStatus.READY)

        # le cas ou la date de release différente de la ready date
        PassengerReady(request, self.queue).add_to_queue()

        return 'Passenger Assignment process is implemented'


class PassengerReady(Event):
    def __init__(self, request, queue):
        # max(ready_time, current_time)
        super().__init__('PassengerReady', queue, max(request.ready_time, queue.env.current_time))
        self.request = request

    def process(self, env):
        # Patrick: Why is the status ONBOARD? Shouldn't it be READY?
        self.request.update_passenger_status(PassengersStatus.ONBOARD)
        return 'Passenger Ready process is implemented'


class PassengerToBoard(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerToBoard', queue, request.ready_time)
        self.request = request

    def process(self, env):
        # End of process

        ## Notify vehicle to board
        # TODO : VehiclePassengerBoarded
        VehicleBoarded(self.request, self.queue).add_to_queue()

        return 'Passenger On Board process is implemented'


class PassengerAlighting(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerAlighting', queue)
        self.__request = request

    def process(self, env):
        self.request.status = PassengersStatus.ALIGHT
        return 'Passenger Alighting process is implemented'
