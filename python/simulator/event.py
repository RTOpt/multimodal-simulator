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


class PassengerRelease(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerRelease', request.release_time, queue)
        self.request = request

    def process(self, env):
        e = PassengerAssignment(self.request, self.queue)
        e.add_to_queue()
        return 'Passenger Release process is implemented'


class PassengerAssignment(Event):
    def __init__(self, request, assigned_vehicle, queue):
        super().__init__('PassengerAssignment', request.release_time, queue)
        self.request = request

    def process(self, env):
        #optimizing
        free_vehicles = env.get_free_vehicles()
        assigned_vehicle = free_vehicles[0]

        assigned_vehicle.route.depart(self.request)
        self.request.assign(assigned_vehicle)

        e = PassengerReady(self.request, self.queue, assigned_vehicle)
        e.add_to_queue()

        return 'Passenger Assignment process is implemented'

class PassengerReady(Event):
    def __init__(self, request, queue, assigned_vehicle):
        super().__init__('PassengerReady', request.ready_time, queue)
        self.request = request
        self.assigned_vehicle = assigned_vehicle


    def process(self, env):
        e = PassengerOnBoard(self.request, self.queue)
        e.add_to_queue()

        # Notify vehicle to board
        e = VehicleBoarding(self.request, self.queue)
        e.add_to_queue()

        #for passenger in self.request.nb_passengers:
        self.assigned_vehicle.route.board(self.request)

        return 'Passenger Ready process is implemented'


class PassengerOnBoard(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerOnBoard', request.ready_time, queue)
        self.request = request

    def process(self, env):
        # Notify vehicle to alight
        e = VehicleAlighting(self.request, self.queue, self.request.assigned_vehicle)
        e.add_to_queue()

        return 'Passenger On Board process is implemented'

class VehicleReady(Event):
    def __init__(self, vehicle, queue):
        super().__init__('VehicleReady', vehicle.start_time, queue)
        self.vehicle = vehicle

    def process(self, env):
        #Assign the vehicle to a route
        route = Route(self.vehicle)
        self.vehicle.new_route()
        # e = VehicleBoarding(self.queue)
        # e.add_to_queue()

        return 'Vehicle Ready process is implemented'


class VehicleBoarding(Event):
    def __init__(self, request, queue):
        super().__init__('Boarding', request.ready_time, queue)
        self.request = request

    def process(self, env):
        while self.request.nb_passengers != 0:
            e = PassengerReady(self.request, self.queue, self.request.assigned_vehicle)
            e.add_to_queue()
            self.request.nb_passengers -= 1

        if self.request.nb_passengers == 0 :
            e = VehicleEnRoute(self.request, self.queue, self.request.assigned_vehicle.route)
            e.add_to_queue()

        return 'Vehicle Boarding process is implemented'


class VehicleEnRoute(Event):
    def __init__(self, request, queue, route):
        super().__init__('VehicleEnRoute', request.ready_time, queue)
        self.request = request
        self.route = route

    def process(self, env):
        if self.route.current_stop == self.request.destination:
            self.route.arrive(self.request)
            e = VehicleAlighting(self.request, self.queue, self.request.assigned_vehicle)
            e.add_to_queue()


        return 'Vehicle En Route process is implemented'


class VehicleAlighting(Event):
    def __init__(self, request, queue, vehicle):
        super().__init__('VehicleAlighting', request.due_time, queue)
        self.vehicle = vehicle
        self.request = request

    def process(self, env):
        e = VehicleBoarding(self.request, self.queue)
        e.add_to_queue()

        while self.request.nb_passengers != 0:
            e = PassengerAlighting(self.request, self.queue)
            e.add_to_queue()
            self.request.nb_passengers -= 1

        return 'Vehicle Alighting process is implemented'

class PassengerAlighting(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerAlighting', request.due_time, queue)

    def process(self, env):
        # Notify vehicle to alight
        e = VehicleAlighting(self.request, self.queue)
        e.add_to_queue()

        return 'Passenger Alighting process is implemented'


