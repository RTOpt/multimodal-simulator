from event import Event
# from passenger_event_process import PassengerAssignment
from request import PassengerUpdate
from vehicle import *
from network import *
from python.optimization import optimization

import copy


class Optimize(Event):
    def __init__(self, time, queue):
        super().__init__('Optimize', queue, time)
        self.queue = queue

    def process(self, env):
        # ne pas modifier la route ici
        # envoyer le vecteur de next_stops, current stops, passengers to pick up

        env.optimization.update_status(OptimizationStatus.OPTIMIZING)

        # Patrick: Added optimization to Environment
        # env.optimization.optimization_algo(env)

        state = copy.deepcopy(env)

        optimization_result = env.optimization.optimize(state)

        EnvironmentUpdate(optimization_result, self.queue).process(env)



        # vehicle_to_update_id_route_time_pairs_list = []
        # for request_id_vehicle_id_route_time_assignment_triplet in request_id_vehicle_id_route_time_assignment_triplets_list:
        #     request_id = request_id_vehicle_id_route_time_assignment_triplet[0]
        #     vehicle_id = request_id_vehicle_id_route_time_assignment_triplet[1]
        #
        #     passenger_update = PassengerUpdate(vehicle_id, request_id)
        #     PassengerAssignment(passenger_update, self.queue).add_to_queue()
        #
        #     next_stops_info_dict_list = request_id_vehicle_id_route_time_assignment_triplet[2]
        #     vehicle_to_update_id_route_time_pairs_list.append((vehicle_id, next_stops_info_dict_list))


        # for vehicle_id, next_stops_arrival_departure_times_dict_list in vehicle_to_update_id_route_time_pairs_list:
        #     passengers_to_board = None
        #     next_stops = next_stops_info_dict_list
        #     route_update = RouteUpdate(vehicle_id, current_stop_passengers_to_board=)
        #     VehicleNotification(route_update, self.queue).add_to_queue()

        return 'Optimize process is implemented'


class EnvironmentUpdate(Event):
    def __init__(self, optimization_result, queue):
        super().__init__('EnvironmentUpdate', queue)
        self.optimization_result = optimization_result

    def process(self, env):
        # free_vehicles = env.get_free_vehicles()
        # assigned_vehicle = free_vehicles[0]
        # self.request.assign_vehicle(assigned_vehicle)

        # Patrick: Temporary solution to prevent circular import. Maybe the code should be rearranged.
        # from passenger_event_process import PassengerAssignment
        # for req in env.assigned_requests:
        #     # Patrick: Do we still use PassengerUpdate?
        #     passenger_update = PassengerUpdate(req.assigned_vehicle, req)
        #     PassengerAssignment(req, self.queue).add_to_queue()
        #
        # passengers_to_board = []
        # next_stops = []
        # route_id = []
        #
        # for veh in env.assigned_vehicles:
        #     RouteUpdate(passengers_to_board, next_stops, route_id)

        env.optimization.update_status(OptimizationStatus.UPDATEENVIRONMENT)

        from passenger_event_process import PassengerAssignment
        for req in self.optimization_result.modified_requests:
            passenger_update = PassengerUpdate(req.assigned_vehicle.id, req.req_id)
            PassengerAssignment(passenger_update, self.queue).add_to_queue()

        from vehicle_event_process import VehicleNotification
        for veh in self.optimization_result.modified_vehicles:
            current_stop_passengers_to_board = veh.route.current_stop.passengers_to_board
            next_stops = veh.route.next_stops
            route_update = RouteUpdate(veh.id, current_stop_passengers_to_board=current_stop_passengers_to_board,
                                       next_stops=next_stops,
                                       current_stop_departure_time=veh.route.current_stop.departure_time)
            VehicleNotification(route_update, self.queue).add_to_queue()

        env.optimization.update_status(OptimizationStatus.IDLE)

        return 'Environment Update process is implemented'
