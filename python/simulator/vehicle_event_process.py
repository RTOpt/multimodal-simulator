from event import Event

from vehicle import *
from optimization_event_process import *
# from passenger_event_process import *
# from passenger_event_process import PassengerAlighting


class VehicleReady(Event):
    def __init__(self, queue, vehicle_data_dict):
        # Patrick: What is the "release time" of a vehicle? Is it at the beginning of the simulation (at time 0)?
        # Should the event_time of VehicleReady be the current_time (and not the start_time of the Vehicle)?
        super().__init__('VehicleReady', queue)
        # super().__init__('VehicleReady', queue, vehicle_data_dict['start_time'])
        self.vehicle_data_dict = vehicle_data_dict

        # Patrick: OLD
        # self.vehicle.route = Route(self.vehicle)

    def process(self, env):
        vehicle = env.add_vehicle(self.vehicle_data_dict['vehicle_id'], self.vehicle_data_dict['start_time'],
                                  self.vehicle_data_dict['start_stop'], self.vehicle_data_dict['capacity'],
                                  self.vehicle_data_dict['next_stops'])

        # Patrick: In the case of buses, the route is assigned to a Vehicle when the Vehicle is created.
        if vehicle.route is None:
            vehicle.new_route()

        # TODO : OPTIMIZE EVENT

        Optimize(env.current_time, self.queue).add_to_queue()
        VehicleBoarding(vehicle.route, self.queue).add_to_queue()

        return 'Vehicle Ready process is implemented'


class VehicleBoarding(Event):
    def __init__(self, route, queue):
        # Patrick: What is the event time here? Is it self.route.request_to_pickup().ready_time?
        # Or route.current_stop.arrival_time?
        # super().__init__('VehicleBoarding', route.request_to_pickup().ready_time, queue)

        # Patrick: Is the time current_stop.arrival_time or current_stop.departure_time
        super().__init__('VehicleBoarding', queue, route.current_stop.departure_time)
        self.route = route

    def process(self, env):

        # Patrick: Do we update the status here?
        self.route.update_vehicle_status(VehicleStatus.BOARDING)

        # self.route.board(self.request)

        # TODO : add PASSENGER TO BOARD EVENT for each passenger to board

        # Old:
        # for passenger in self.route.request_to_pickup().nb_passengers:
        #     PassengerToBoard(self.route.request_to_pickup(), self.queue).add_to_queue()

        # Patrick: Temporary solution.
        from python.simulator.passenger_event_process import PassengerToBoard

        if len(self.route.requests_to_pickup()) > 0:
            # Passengers to board
            passengers_to_board_copy = self.route.current_stop.passengers_to_board.copy()
            print("len(passengers_to_board_copy)={}".format(len(passengers_to_board_copy)))
            for req in passengers_to_board_copy:
                print("req={}".format(req))
                self.route.current_stop.initiate_boarding(req)
                PassengerToBoard(req, self.queue).add_to_queue()
        elif len(self.route.next_stops) > 0:
            # No passengers to board
            VehicleDeparture(self.route, self.queue).add_to_queue()
        else:
            # End of route
            # Patrick: Should we set the status to COMPLETE if there are no next stops?
            self.route.update_vehicle_status(VehicleStatus.COMPLETE)

        return 'Vehicle Boarding process is implemented'


class VehicleDeparture(Event):
    def __init__(self, route, queue):
        super().__init__('Vehicle Departure', queue, route.current_stop.departure_time)
        self.route = route

    def process(self, env):
        # TODO : modifier status ... pour enroute
        self.route.update_vehicle_status(VehicleStatus.ENROUTE)

        self.route.depart()
        # OLD
        # self.route.arrive(self.request)

        VehicleArrival(self.route, self.queue).add_to_queue()

        return 'Vehicle Departure process is implemented'


class VehicleArrival(Event):
    def __init__(self, route, queue):
        super().__init__('VehicleArrival', queue, route.next_stops[0].arrival_time)
        self.route = route

    def process(self, env):
        self.route.update_vehicle_status(VehicleStatus.ALIGHTING)

        self.route.arrive()

        # TODO: modify request

        # TODO:  for each passenger to alight
        # Patrick: Is it OK?
        from python.simulator.passenger_event_process import PassengerAlighting
        passengers_to_alight_copy = self.route.current_stop.passengers_to_alight.copy()
        for request in passengers_to_alight_copy:
            self.route.alight(request)
            PassengerAlighting(request, self.queue).add_to_queue()

        VehicleBoarding(self.route, self.queue).add_to_queue()

        return 'Vehicle Alighting process is implemented'


# modifier vehicle passenger update
class VehicleNotification(Event):
    def __init__(self, route_update, queue):
        super().__init__('VehicleNotification', queue)
        self.route_update = route_update

    def process(self, env):

        # TODO: ALL THESES OBJECTS ARE FROM STATE. GET THE CORRESPONDING OBJECTS FROM ENV.

        vehicle = env.get_vehicle_by_id(self.route_update.vehicle_id)

        if self.route_update.next_stops is not None:
            for stop in self.route_update.next_stops:
                self.__update_stop_with_actual_requests(env, stop)
            vehicle.route.next_stops = self.route_update.next_stops

        if self.route_update.current_stop_passengers_to_board is not None:
            vehicle.route.current_stop.passengers_to_board = \
                self.__replace_copy_requests_with_actual_requests(env,
                                                                  self.route_update.current_stop_passengers_to_board)

        if self.route_update.current_stop_departure_time is not None:
            vehicle.route.current_stop.departure_time = self.route_update.current_stop_departure_time

        # if self.route_update.next_stops is not None:
        #     for stop in ([vehicle.route.current_stop] + vehicle.route.next_stops):
        #         for next_stop_info in self.route_update.next_stops:
        #             if stop.location == next_stop_info['location']:
        #                 stop.arrival_time = next_stop_info['arrival_time']
        #                 stop.departure_time = next_stop_info['departure_time']
        #         print("stop={}".format(stop))

        return 'Notify Vehicle process is implemented'

    def __update_stop_with_actual_requests(self, env, stop):

        stop.passengers_to_board = self.__replace_copy_requests_with_actual_requests(env, stop.passengers_to_board)
        stop.boarding_passengers = self.__replace_copy_requests_with_actual_requests(env, stop.boarding_passengers)
        stop.boarded_passengers = self.__replace_copy_requests_with_actual_requests(env, stop.boarded_passengers)
        stop.passengers_to_alight = self.__replace_copy_requests_with_actual_requests(env, stop.passengers_to_alight)

    def __replace_copy_requests_with_actual_requests(self, env, requests_list):

        return list(env.get_request_by_id(req.req_id) for req in requests_list)


# Mettre dans vehicle
class VehicleBoarded(Event):
    def __init__(self, request, queue):
        super().__init__('VehicleBoarded', queue)
        self.request = request

    def process(self, env):

        route = self.request.assigned_vehicle.route

        route.board(self.request)

        if len(route.current_stop.boarding_passengers) == 0:
            # All passengers are on board
            # TODO: CORRECT IT! DOES NOT WORK PROPERLY!
            VehicleDeparture(route, self.queue).add_to_queue()

        return 'Vehicle Boarded process is implemented'
