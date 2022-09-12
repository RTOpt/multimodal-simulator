from optimization_event_process import *


class VehicleReady(Event):
    def __init__(self, vehicle_data_dict, queue):
        super().__init__('VehicleReady', queue, vehicle_data_dict['release_time'])
        self.vehicle_data_dict = vehicle_data_dict

    def process(self, env):
        vehicle = env.add_vehicle(self.vehicle_data_dict['vehicle_id'], self.vehicle_data_dict['start_time'],
                                  self.vehicle_data_dict['start_stop'], self.vehicle_data_dict['capacity'])

        # Patrick: self.vehicle_data_dict['next_stops'] may be empty (in the case of shuttles, for example).
        vehicle.route = Route(vehicle, self.vehicle_data_dict['next_stops'])

        Optimize(env.current_time, self.queue).add_to_queue()
        VehicleBoarding(vehicle.route, self.queue).add_to_queue()

        return 'Vehicle Ready process is implemented'


class VehicleBoarding(Event):
    def __init__(self, route, queue):

        # Patrick: Is the time current_stop.arrival_time or current_stop.departure_time?
        super().__init__('VehicleBoarding', queue, route.current_stop.departure_time)
        self.route = route

    def process(self, env):

        self.route.update_vehicle_status(VehicleStatus.BOARDING)

        # Patrick: Temporary solution to prevent circular import. Maybe the code should be rearranged.
        from python.simulator.passenger_event_process import PassengerToBoard

        if len(self.route.requests_to_pickup()) > 0:
            # Passengers to board
            passengers_to_board_copy = self.route.current_stop.passengers_to_board.copy()
            for req in passengers_to_board_copy:
                self.route.current_stop.initiate_boarding(req)
                PassengerToBoard(req, self.queue).add_to_queue()
        elif len(self.route.next_stops) > 0:
            # No passengers to board
            VehicleDeparture(self.route, self.queue).add_to_queue()
        else:
            # End of route
            # Patrick: Should we set the status to COMPLETE if there are no next stops?
            self.route.update_vehicle_status(VehicleStatus.COMPLETE)
            Optimize(env.current_time, self.queue).add_to_queue()

        return 'Vehicle Boarding process is implemented'


class VehicleDeparture(Event):
    def __init__(self, route, queue):
        super().__init__('Vehicle Departure', queue, route.current_stop.departure_time)
        self.route = route

    def process(self, env):
        self.route.update_vehicle_status(VehicleStatus.ENROUTE)

        self.route.depart()

        VehicleArrival(self.route, self.queue).add_to_queue()

        return 'Vehicle Departure process is implemented'


class VehicleArrival(Event):
    def __init__(self, route, queue):
        super().__init__('VehicleArrival', queue, route.next_stops[0].arrival_time)
        self.route = route

    def process(self, env):
        self.route.update_vehicle_status(VehicleStatus.ALIGHTING)

        self.route.arrive()

        from python.simulator.passenger_event_process import PassengerAlighting
        passengers_to_alight_copy = self.route.current_stop.passengers_to_alight.copy()
        for request in passengers_to_alight_copy:
            self.route.alight(request)
            PassengerAlighting(request, self.queue).add_to_queue()

        VehicleBoarding(self.route, self.queue).add_to_queue()

        return 'Vehicle Alighting process is implemented'


class VehicleNotification(Event):
    def __init__(self, route_update, queue):
        super().__init__('VehicleNotification', queue)
        self.route_update = route_update

    def process(self, env):

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

        if self.route_update.assigned_requests is not None:
            vehicle.route.assigned_requests = \
                self.__replace_copy_requests_with_actual_requests(env,
                                                                  self.route_update.assigned_requests)

        return 'Notify Vehicle process is implemented'

    def __update_stop_with_actual_requests(self, env, stop):

        stop.passengers_to_board = self.__replace_copy_requests_with_actual_requests(env, stop.passengers_to_board)
        stop.boarding_passengers = self.__replace_copy_requests_with_actual_requests(env, stop.boarding_passengers)
        stop.boarded_passengers = self.__replace_copy_requests_with_actual_requests(env, stop.boarded_passengers)
        stop.passengers_to_alight = self.__replace_copy_requests_with_actual_requests(env, stop.passengers_to_alight)

    def __replace_copy_requests_with_actual_requests(self, env, requests_list):

        return list(env.get_request_by_id(req.req_id) for req in requests_list)


class VehicleBoarded(Event):
    def __init__(self, request, queue):
        super().__init__('VehicleBoarded', queue)
        self.request = request

    def process(self, env):
        route = self.request.assigned_vehicle.route

        route.board(self.request)

        if len(route.current_stop.boarding_passengers) == 0:
            # All passengers are on board
            VehicleDeparture(route, self.queue).add_to_queue()
            # Else we wait until all the boarding passengers are on board before creating the event VehicleDeparture.

        return 'Vehicle Boarded process is implemented'
