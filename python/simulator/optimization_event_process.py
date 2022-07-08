from event import Event
from passenger_event_process import *
from vehicle import *
from network import *
from python.optimization import optimization


class Optimize(Event):
    def __init__(self, time, queue):
        super().__init__('Optimize', time, queue)
        self.queue = queue

    def process(self, env):
        #ne pas modifier la route ici
        # envoyer le vecteur de next_stops, current stops, passengers to pick up
        optimization.optimization_algo(env)
        EnvironmentUpdate(env.current_time, self.queue).add_to_queue()

        return 'Optimize process is implemented'


class EnvironmentUpdate(Event):
    def __init__(self, time, queue):
        super().__init__('EnvironmentUpdate', time, queue)


    def process(self, env):
        # free_vehicles = env.get_free_vehicles()
        # assigned_vehicle = free_vehicles[0]
        # self.request.assign_vehicle(assigned_vehicle)


        for req in env.assigned_requests:
            PassengerUpdate(req.assigned_vehicle, req)
            PassengerAssignment(req, self.queue).add_to_queue()

        passengers_to_board = []
        next_stops = []
        route_id = []

        for veh in env.assigned_vehicles:
            RouteUpdate(passengers_to_board, next_stops, route_id)



        return 'Environment Update process is implemented'
