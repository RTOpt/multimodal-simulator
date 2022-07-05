from queue import PriorityQueue
from vehicle import *
from network import *


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

        return 'Passenger Ready process is implemented'


class PassengerToBoard(Event):
    def __init__(self, request, queue):
        super().__init__('PassengerOnBoard', request.ready_time, queue)
        self.request = request

    def process(self, env):
        #End of process
        self.request.update_passenger_status(PassengersStatus.ONBOARD)

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

class VehicleReady(Event):
    def __init__(self, vehicle, queue):
        super().__init__('VehicleReady', vehicle.start_time, queue)
        self.vehicle = vehicle

    def process(self, env):

        #Assign the vehicle to a route
        route = Route(self.vehicle)

        # TODO : OPTIMIZE EVENT
        Optimize(self.request, self.queue).add_to_queue()

        return 'Vehicle Ready process is implemented'


class VehicleBoarding(Event):
    def __init__(self, route, queue):
        super().__init__('Boarding', time, queue)
        self.route = route

    def process(self, env):
        self.route.board(self.request)

        #TODO : add PASSENGER TO BOARD EVENT for each passenger to board
        for passenger in self.request.nb_passengers:
            PassengerToBoard(self.request, self.queue).add_to_queue()

        next_stop = len(self.request.assigned_vehicle.route.next_stops)
        if self.request.nb_passengers == 0 and next_stop != 0:
            VehicleDeparture(self.route, self.queue).add_to_queue()

        return 'Vehicle Boarding process is implemented'


class VehicleDeparture(Event):
    def __init__(self, route, queue):
        super().__init__('VehicleEnRoute', route.time, queue)
        self.route = route

    def process(self, env):
        # TODO : modifier status ... pour enroute
        self.route.update_vehicle_status(VehicleStatus.ENROUTE)
        self.route.arrive(self.request)
        VehicleArrival(self.request, self.queue).add_to_queue()

        return 'Vehicle En Route process is implemented'


class VehicleArrival(Event):
    def __init__(self, route, queue):
        super().__init__('VehicleAlighting', time, queue)
        self.route = self.request.assigned_vehicle.route

    def process(self, env):
        self.route.alight(self.request)
        #TODO:  for each passenger to alight
        for passenger in passengers_to_alight:
            VehicleBoarding(self.request, self.queue).add_to_queue()

        return 'Vehicle Alighting process is implemented'

class PassengerNotification(Event):
    def __init__(self, passenger_update, queue):
        super().__init__('PassengerNotification', time, queue)


    def process(self, env):
        return 'Passenger Notification process is implemented'

#modifier vehicle passenger update
class VehicleNotification(Event):
    def __init__(self, route_update, queue, time):
        super().__init__('VehicleNotification', time, queue)


    def process(self, env):
        self.route.board(self.request)

        return 'Notify Vehicle process is implemented'

class Optimizing(Event):
    def __init__(self, request, queue):
        super().__init__('Optimizing', request.release_time, queue)
        self.request = request

    def process(self, env):
        #ne pas modifier la route ici
        # envoyer le vecteur de next_stops, current stops, passengers to pick up (min 30)
        self.request.assign_route(get_path(env.network, self.request.origin, self.request.destination))
        e = EnvironmentUpdate(self.request, self.queue)
        e.add_to_queue()

        return 'Optimizing process is implemented'



class EnvironmentUpdate(Event):
    def __init__(self, request, queue):
        super().__init__('EnvironmentUpdate', request.release_time, queue)
        self.request = request

    def process(self, env):
        free_vehicles = env.get_free_vehicles()
        assigned_vehicle = free_vehicles[0]
        free_vehicles[0].update_vehicleStatus(VehicleStatus.ACTIVE)
        self.request.assign_vehicle(assigned_vehicle)

        PassengerAssignment(self.request, self.queue).add_to_queue()

        Optimize(self.request, self.queue).add_to_queue()

        return 'Environment Update process is implemented'

class Optimize(Event):
    def __init__(self, request, queue):
        super().__init__('Idle', request.release_time, queue)
        self.request = request

    def process(self, env):
        e = Optimizing()
        e.add_to_queue()

        return 'Idle process is implemented'
