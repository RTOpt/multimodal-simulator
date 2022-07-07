from event import Event
from optimization_event_process import *
from request import *

class PassengerRelease(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerRelease', request.release_time, queue)
        self.request = request

    def process(self, env):
        #TODO : modify release to wait assignment
        self.request.update_passenger_status(PassengersStatus.ASSIGNMENT)

        # Start optimization
        Optimize(self.request, self.queue).add_to_queue()
        return 'Passenger Release process is implemented'


class PassengerAssignment(Event):
    def __init__(self, passenger_update, queue):
        #TODO : passenger_update
        super().__init__('PassengerAssignment', passenger_update.release_time, queue)
        self.passenger_update = passenger_update

    def process(self, env):
        self.request.update_passenger_status(PassengersStatus.READY)
        # le cas ou la date de release différente de la ready date
        PassengerReady(self.request, self.queue).add_to_queue()

        return 'Passenger Assignment process is implemented'

class PassengerReady(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerReady', request.ready_time, queue)
        self.request = request

    def process(self, env):
        self.request.update_passenger_status(PassengersStatus.ONBOARD)
        return 'Passenger Ready process is implemented'


class PassengerToBoard(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerToBoard', request.ready_time, queue)
        self.request = request

    def process(self, env):
        #End of process


        ## Notify vehicle to board
        # TODO : VehiclePassengerBoarded
        PassengerNotification(self.request, self.request.ready_time, self.queue).add_to_queue()

        return 'Passenger On Board process is implemented'

class PassengerAlighting(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerAlighting', request.due_time, queue)

    def process(self, env):
        self.request.status = PassengersStatus.ALIGHT
        return 'Passenger Alighting process is implemented'



class PassengerNotification(Event):
    def __init__(self, passenger_update, queue):
        super().__init__('PassengerNotification', time, queue)


    def process(self, env):
        return 'Passenger Notification process is implemented'