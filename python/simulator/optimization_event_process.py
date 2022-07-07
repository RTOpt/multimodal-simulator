from event import Event
from passenger_event_process import *
from vehicle import *
from network import *
from python.optimization import optimization

time = 0

class Optimize(Event):
    def __init__(self, queue):
        super().__init__('Optimize', time, queue)
        self.queue = queue

    def process(self, env):
        #ne pas modifier la route ici
        # envoyer le vecteur de next_stops, current stops, passengers to pick up
        optimization.optimization_algo(env)
        EnvironmentUpdate(self.queue).add_to_queue()

        return 'Optimize process is implemented'


class EnvironmentUpdate(Event):
    def __init__(self, queue):
        super().__init__('EnvironmentUpdate', time, queue)


    def process(self, env):
        # free_vehicles = env.get_free_vehicles()
        # assigned_vehicle = free_vehicles[0]
        # self.request.assign_vehicle(assigned_vehicle)

        PassengerUpdate(assigned_vehicle, self.request)
        passengers_to_board = []
        next_stops = []
        route_id = []
        RouteUpdate(passengers_to_board, next_stops, route_id)

        PassengerAssignment(self.request, self.queue).add_to_queue()

        return 'Environment Update process is implemented'
