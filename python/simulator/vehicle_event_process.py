from event import Event
from vehicle import *
from optimization_event_process import *
from passenger_event_process import *
time = 0

class VehicleReady(Event):
    def __init__(self, vehicle, queue):
        super().__init__('VehicleReady', vehicle.start_time, queue)
        self.vehicle = vehicle

    def process(self, env):

        #Assign the vehicle to a route
        route = Route(self.vehicle)

        # TODO : OPTIMIZE EVENT
        Optimize(self.queue).add_to_queue()
        VehicleBoarding(route, self.queue).add_to_queue()

        return 'Vehicle Ready process is implemented'


class VehicleBoarding(Event):
    def __init__(self, route, queue):
        super().__init__('VehicleBoarding', time, queue)
        self.route = route

    def process(self, env):
        #self.route.board(self.request)

        #TODO : add PASSENGER TO BOARD EVENT for each passenger to board
        for passenger in self.route.request_to_pickup().nb_passengers:
            PassengerToBoard(self.route.request_to_pickup(), self.queue).add_to_queue()

        next_stop = len(self.route.next_stops)
        if self.route.request_to_pickup().nb_passengers == 0 and next_stop != 0:
            VehicleDeparture(self.route, self.queue).add_to_queue()

        return 'Vehicle Boarding process is implemented'


class VehicleDeparture(Event):
    def __init__(self, route, queue):
        super().__init__('Vehicle Departure', time, queue)
        self.route = route

    def process(self, env):
        # TODO : modifier status ... pour enroute
        self.route.update_vehicle_status(VehicleStatus.ENROUTE)
        self.route.arrive(self.request)
        VehicleArrival(self.request, self.queue).add_to_queue()

        return 'Vehicle Departure process is implemented'


class VehicleArrival(Event):
    def __init__(self, route, queue):
        super().__init__('VehicleArrival', time, queue)
        self.route = route

    def process(self, env):
        self.route.update_vehicle_status(VehicleStatus.ALIGHTING)

        #TODO: modify request
        self.route.alight(self.request)
        #TODO:  for each passenger to alight
        for passenger in passengers_to_alight:
            VehicleBoarding(self.request, self.queue).add_to_queue()

        return 'Vehicle Alighting process is implemented'


#modifier vehicle passenger update
class VehicleNotification(Event):
    def __init__(self, route_update, queue, time):
        super().__init__('VehicleNotification', time, queue)


    def process(self, env):

        return 'Notify Vehicle process is implemented'
