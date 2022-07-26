from networkx.algorithms.shortest_paths.generic import shortest_path

from python.simulator.status import OptimizationStatus, PassengersStatus


class Optimization(object):

    def __init__(self):
        self.status = OptimizationStatus.IDLE

    def optimize(self):
        raise NotImplementedError('optimize not implemented')

    # Patrick: Added
    def update_status(self, status):
        self.status = status


class GreedyOptimization(Optimization):

    def __init__(self):
        super().__init__()

    def optimize(self, env):
        non_assigned_requests = env.get_non_assigned_requests()
        non_assigned_vehicles = env.get_non_assigned_vehicles()

        print("non_assigned_requests={}".format(non_assigned_requests))

        veh = 0
        for req in non_assigned_requests:
            print("req.assigned_vehicle={}".format(req.assigned_vehicle))
            if veh < len(non_assigned_vehicles) + 1:
                req.assign_route(self.__get_path(env.network, req.origin, req.destination))
                assigned_vehicle = non_assigned_vehicles[veh]
                req.assign_vehicle(assigned_vehicle)

                # Patrick: Shouldn't we also assign the request to assigned_vehicle.route?
                assigned_vehicle.route.assign(req)

                veh += 1

    def __find_shortest_path(self, G, o, d):
        path = shortest_path(G, source=o, target=d, weight='length')
        # path_length = path_weight(G, path, weight='length')

        return path

    def __get_path(self, G, node1, node2):
        for node in G.nodes:
            if node.coordinates == node1:
                origin = node
            if node.coordinates == node2:
                destination = node
        path = self.__find_shortest_path(G, origin, destination)
        # path_cost = get_manhattan_distance(node1, node2)
        return path


class BusOptimization(Optimization):

    def __init__(self):
        super().__init__()
        self.__non_assigned_released_requests_list = None
        self.__non_assigned_vehicles_list = None

    def optimize(self, state):
        # state: copie profonde (peut-être partielle) de l'environnement
        # optimization_result: state, modified_passengers, modified_routes, etc.
        print("\n******************\nOPTIMIZE:\n")
        print("current_time={}".format(state.current_time))

        self.__non_assigned_vehicles_list = state.get_non_assigned_vehicles()
        self.__non_assigned_released_requests_list = state.get_non_assigned_requests()
        # self.__non_assigned_released_requests_list = list(
        #     x for x in state.get_non_assigned_requests() if x.release_time <= state.current_time)

        request_vehicle_pairs_list = []
        modified_requests = []
        modified_vehicles = []

        for req in self.__non_assigned_released_requests_list:
            print("req={}".format(req))
            potential_vehicles_list = self.__get_vehicles_containing_stops_list(req.origin.label, req.destination.label)
            # Modifier map avec list
            print("potential_vehicles_list={}".format(list(map(lambda x: x.id, potential_vehicles_list))))
            for veh in potential_vehicles_list:
                print("req.ready_time={}, veh.start_time={}".format(req.ready_time, veh.start_time))
                if req.ready_time <= veh.start_time:
                    request_vehicle_pairs_list.append((req, veh))
                    req.assign_vehicle(veh)
                    veh.route.assign(req)
                    req.update_passenger_status(PassengersStatus.ASSIGNED)
                    modified_requests.append(req)
                    modified_vehicles.append(veh)
                    break

        print("request_vehicle_pairs_list:")
        for req, veh in request_vehicle_pairs_list:
            print("---(req_id={},veh_id={})".format(req.req_id, veh.id))

        for req, veh in request_vehicle_pairs_list:
            if veh.route.current_stop is not None and req.origin.label == veh.route.current_stop.location.label:
                veh.route.current_stop.passengers_to_board.append(req)

            for stop in veh.route.next_stops:
                if req.origin.label == stop.location.label:
                    stop.passengers_to_board.append(req)
                elif req.destination.label == stop.location.label:
                    stop.passengers_to_alight.append(req)



        print("END OPTIMIZE\n*******************")

        # Remplacer request_id_vehicle_id_route_time_assignment_triplets_list par une classe container.
        # liste des objets requêtes et véhicules modifiés.

        return OptimizationResult(state, modified_requests, modified_vehicles)

    def __get_vehicles_containing_stops_list(self, first_stop_id, second_stop_id):
        print("first_stop_id={}, second_stop_id={}".format(first_stop_id, second_stop_id))
        vehicles_containing_stops_list = []
        for veh in self.__non_assigned_vehicles_list:
            current_stop_id = veh.route.current_stop.location.label
            next_stops_ids_list = list(x.location.label for x in veh.route.next_stops)

            # print(type(current_stop_id), type(first_stop_id), type(second_stop_id))
            # print("current_stop_id={}, next_stops_ids_list={}".format(current_stop_id, next_stops_ids_list))
            # print("type(current_stop_id)={}, type(next_stops_ids[0])={}".format(type(current_stop_id), type(next_stops_ids_list[0])))
            # print("first_stop_id == current_stop_id={}".format(first_stop_id == current_stop_id))
            # print("second_stop_id in next_stops_ids_list={}".format(second_stop_id in next_stops_ids_list))

            if first_stop_id == current_stop_id and second_stop_id in next_stops_ids_list:
                vehicles_containing_stops_list.append(veh)
            elif first_stop_id != current_stop_id and first_stop_id in next_stops_ids_list and second_stop_id in next_stops_ids_list:
                if next_stops_ids_list.index(first_stop_id) < next_stops_ids_list.index(second_stop_id):
                    vehicles_containing_stops_list.append(veh)

        return vehicles_containing_stops_list

    # def __calculate_next_stops_arrival_departure_times(self, route):
    #
    #     next_stops_arrival_departure_times_dict_list = []
    #
    #     current_stop_arrival_departure_times_dict = {
    #         'location': route.current_stop.location,
    #         'arrival_time': route.current_stop.arrival_time,
    #         'departure_time': route.current_stop.arrival_time + BOARDING_TIME
    #     }
    #     next_stops_arrival_departure_times_dict_list.append(current_stop_arrival_departure_times_dict)
    #
    #     previous_stop_time = route.current_stop.arrival_time + BOARDING_TIME
    #     for stop in route.next_stops:
    #         stop_arrival_departure_times_dict = {
    #             'location': stop.location,
    #             'arrival_time': previous_stop_time + TRAVEL_TIME,
    #             'departure_time': previous_stop_time + TRAVEL_TIME + BOARDING_TIME
    #         }
    #         next_stops_arrival_departure_times_dict_list.append(stop_arrival_departure_times_dict)
    #         previous_stop_time = previous_stop_time + TRAVEL_TIME + BOARDING_TIME
    #
    #     return next_stops_arrival_departure_times_dict_list


class OptimizationResult(object):

    def __init__(self, state, modified_requests, modified_vehicles):
        self.state = state
        self.modified_requests = modified_requests
        self.modified_vehicles = modified_vehicles
