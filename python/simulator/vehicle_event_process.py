from event import Event
from vehicle import *
from optimization_event_process import *
from passenger_event_process import *


class VehicleReady(Event):
    def __init__(self, vehicle, queue):
        super().__init__('VehicleReady', queue, vehicle.start_time)
        self.vehicle = vehicle

        # Patrick: In the case of buses, the route is assigned to a Vehicle when the Vehicle is created.
        if vehicle.route is None:
            self.vehicle.new_route()
        # Patrick: OLD
        # self.vehicle.route = Route(self.vehicle)

    def process(self, env):
        # Assign the vehicle to a route
        # route = Route(self.vehicle)
        # self.vehicle.route = route

        # TODO : OPTIMIZE EVENT

        Optimize(env.current_time, self.queue).add_to_queue()
        VehicleBoarding(self.vehicle.route, self.queue).add_to_queue()

        return 'Vehicle Ready process is implemented'


class VehicleBoarding(Event):
    def __init__(self, route, queue):
        # Patrick: What is the event time here? Is it self.route.request_to_pickup().ready_time?
        # Or route.current_stop.arrival_time?
        # super().__init__('VehicleBoarding', route.request_to_pickup().ready_time, queue)

        super().__init__('VehicleBoarding', queue, route.current_stop.arrival_time)
        self.route = route

    def process(self, env):
        # self.route.board(self.request)

        # TODO : add PASSENGER TO BOARD EVENT for each passenger to board

        # Old:
        # for passenger in self.route.request_to_pickup().nb_passengers:
        #     PassengerToBoard(self.route.request_to_pickup(), self.queue).add_to_queue()

        # Patrick: Temporary solution. Is it possible that no requests are assigned to the route at this point?
        # if len(self.route.request_to_pickup()) != 0:
        for req in self.route.requests_to_pickup():
            PassengerToBoard(req, self.queue).add_to_queue()

        nb_next_stops = len(self.route.next_stops)
        if len(self.route.requests_to_pickup()) == 0 and nb_next_stops != 0:
            VehicleDeparture(self.route, self.queue).add_to_queue()

        return 'Vehicle Boarding process is implemented'


class VehicleDeparture(Event):
    def __init__(self, route, queue):
        super().__init__('Vehicle Departure', queue, route.current_stop.departure_time)
        self.route = route

    def process(self, env):
        # TODO : modifier status ... pour enroute
        self.route.update_vehicle_status(VehicleStatus.ENROUTE)

        # Patrick: Why is there a request here?
        self.route.arrive(None)
        # OLD
        # self.route.arrive(self.request)

        VehicleArrival(self.route, self.queue).add_to_queue()

        return 'Vehicle Departure process is implemented'


class VehicleArrival(Event):
    def __init__(self, route, queue):
        super().__init__('VehicleArrival', queue, route.current_stop.arrival_time)
        self.route = route

    def process(self, env):
        self.route.update_vehicle_status(VehicleStatus.ALIGHTING)

        # TODO: modify request

        # TODO:  for each passenger to alight
        # Patrick: Is it OK?
        for request in self.route.current_stop.passengers_to_alight:
            self.route.alight(request)
            PassengerAlighting(request, self.queue)

        VehicleBoarding(self.route, self.queue).add_to_queue()

        return 'Vehicle Alighting process is implemented'


# modifier vehicle passenger update
class VehicleNotification(Event):
    def __init__(self, route_update, queue):
        super().__init__('VehicleNotification', queue)
        self.route_update = route_update

    def process(self, env):

        vehicle = env.get_vehicle_by_id(self.route_update.vehicle_id)

        if self.route_update.passengers_to_board_at_current_stop is not None:
            vehicle.route.current_stop = self.route_update.passengers_to_board_at_current_stop

        if self.route_update.next_stops is not None:
            for stop in  ([vehicle.route.current_stop] + vehicle.route.next_stops):
                for next_stop_info in self.route_update.next_stops:
                    if stop.location == next_stop_info['location']:
                        stop.arrival_time = next_stop_info['arrival_time']
                        stop.departure_time = next_stop_info['departure_time']
                print("stop={}".format(stop))

        return 'Notify Vehicle process is implemented'


# Mettre dans vehicle
class VehicleBoarded(Event):
    def __init__(self, request, queue):
        super().__init__('VehicleBoarded', queue, request.ready_time)

    def process(self, env):
        return 'Vehicle Boarded process is implemented'
