from queue import PriorityQueue
from abc import ABCMeta, ABC
from vehicle import *


class Event(object):
    """An event with event_number occurs at a specific time ``event_time`` and involves a specific
        event type ``event_type``. Comparing two events amounts to figuring out which event occurs first """

    def __init__(self, event_name, event_time, queue):
        self.name = event_name
        self.time = event_time
        self.queue = queue

    def process(self, env):
        raise NotImplementedError('Process not implemented')

    def __lt__(self, other):
        """ Returns True if self.event_time < other.event_time"""
        return self.time < other.time

    def add_to_queue(self):
        self.queue.put(self)

    def get_event(self):
        """Gets the first event in the event list"""
        event = self.queue.get()
        return event

    def get_name(self):
        """ returns event name"""
        return self.name

    def get_time(self):
        """ returns event time"""
        return self.time


class RequestRelease(Event):
    def __init__(self, request, queue):
        super().__init__('RequestRelease', request.release_time, queue)
        self.request = request

    def process(self, env):
        e = VehicleAffectation(self.request, self.queue)
        e.add_to_queue()
        return 'Request Release process is implemented'


class VehicleAffectation(Event):
    def __init__(self, request, queue):
        super().__init__('VehicleAffectation', request.release_time, queue)
        self.request = request

    def process(self, env):
        free_vehicles = env.get_free_vehicles()
        route = Route(free_vehicles[0].id, free_vehicles[0].start_time, self.request.origin,
                      free_vehicles[0].capacity)

        if route.current_stop == self.request.origin:
            free_vehicles[0].status = VehicleStatus.BOARDING
            e = RequestReady(self.request, self.queue, route)
            e.add_to_queue()


        if free_vehicles[0].status.name == 'BOARDING':
            e = Boarding(self.request, self.queue, route)
            e.add_to_queue()

        return 'Vehicle Affectation process is implemented'


class Boarding(object):
    def __init__(self, request, queue, route):
        super().__init__('Boarding', request.ready_time, queue)
        self.request = request
        self.route = route

    def process(self, env):
        while self.request.nb_passengers != 0:
            e = PassengerBoarding(self.request, self.queue, self.route)
            e.add_to_queue()
            self.request.nb_passengers -= 1

        if self.request.nb_passengers == 0:
            e = VehicleDeparture(self.request, self.queue)
            e.add_to_queue()

        return 'Boarding process is implemented'


class RequestReady(Event):
    def __init__(self, request, queue, route):
        super().__init__('RequestReady', request.ready_time, queue)
        self.request = request
        self.route = route
        print(request.nb_passengers)

    def process(self, env):
        self.route.board()

        return 'Request Ready process is implemented'


class PassengerBoarding(Event):
    def __init__(self, request, queue, route):
        super().__init__('PassengerBoarding', request.ready_time, queue)
        self.request = request
        self.route = route

    def process(self, env):
        if self.request.nb_passengers == 0:
            e = Boarding(self.request, self.queue)
            e.add_to_queue()

        return 'Passenger Boarding process is implemented'


class PassengerAlighting(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerAlighting', request.due_time, queue)

    def process(self, env):
        return 'Alight process is implemented'


class VehicleRelease(Event):
    def __init__(self, vehicle, queue):
        super().__init__('VehicleRelease', vehicle.start_time, queue)

    def process(self, env):
        return 'Vehicle Release process is implemented'


class VehicleDeparture(Event):
    def __init__(self, request, queue, route):
        super().__init__('PassengerDeparture', request.ready_time, queue)
        self.request = request
        self.route = route

    def process(self, env):
        self.route = Route.depart()
        if self.route.current_stop == self.request.destination:
            e = VehicleArrival(self.request, self.queue)
            e.add_to_queue()

        return 'Vehicle Departure process is implemented'


class VehicleArrival(Event):
    def __init__(self, request, queue, route):
        super().__init__('VehicleArrival', request.due_time, queue)
        self.route = route

    def process(self, env):
        self.route = Route.arrive()
        return 'Vehicle Arrival process is implemented'


class Alighting(object):
    def __init__(self, vehicle, request, queue, route):
        super().__init__('Alighting', request.due_time, queue)
        self.vehicle = vehicle
        self.request = request
        self.route = route

    def process(self, env):
        self.route = Route.alight()
        e = Boarding(self.request, self.queue, self.route)
        e.add_to_queue()

        return 'Alight process is implemented'


class QueueEvents(object):
    def __init__(self, env):
        self.current_time = 0.0
        # self.event_list = PriorityQueue()
        # self.queue = PriorityQueue()
        self.requests = env.get_requests()
        self.vehicles = env.get_vehicles()
        self.event_counter = 0

    '''
    def add_event(self, event_type, event_time, req):
        """Adds event to the event_list"""
        self.event_list.put(Event(event_type, event_time, req))
    
    def get_event(self):
        """Gets the first event in the event list"""
        e = self.event_list.get()
        self.current_time = e.event_time
        return e.event_number, e.event_type, e.event_time, e.request_instance
    '''
