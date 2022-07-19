from networkx.algorithms.shortest_paths.generic import shortest_path


class Optimization(object):

    def __init__(self):
        pass

    def optimize(self):
        raise NotImplementedError('optimize not implemented')


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

    def optimize(self, env):

        print("\n******************\nOPTIMIZE:\n")
        print("current_time={}".format(env.current_time))

        self.__non_assigned_vehicles_list = env.get_non_assigned_vehicles()
        self.__non_assigned_released_requests_list = filter(lambda x: x.release_time <= env.current_time,
                                                            env.get_non_assigned_requests())

        request_id_vehicle_id_route_time_assignment_triplets_list = []

        for req in self.__non_assigned_released_requests_list:
            print("req={}".format(req))
            potential_vehicles_list = self.__get_vehicles_containing_stops_list(req.origin, req.destination)
            print("potential_vehicles_list={}".format(list(map(lambda x: x.id, potential_vehicles_list))))
            for veh in potential_vehicles_list:
                print("req.ready_time={}, veh.start_time={}".format(req.ready_time, veh.start_time))
                if req.ready_time <= veh.start_time:
                    next_stops_arrival_departure_times_dict_list = self.__calculate_next_stops_arrival_departure_times(
                        veh.route)
                    request_id_vehicle_id_route_time_assignment_triplets_list.append((req.req_id, veh.id,
                                                                                    next_stops_arrival_departure_times_dict_list))
                    break

        print("request_id_vehicle_id_route_time_assignment_triplets_list={}".format(request_id_vehicle_id_route_time_assignment_triplets_list))

        print("END OPTIMIZE\n*******************")

        return request_id_vehicle_id_route_time_assignment_triplets_list

    def __get_vehicles_containing_stops_list(self, first_stop_id, second_stop_id):
        print("first_stop_id={}, second_stop_id={}".format(first_stop_id, second_stop_id))
        vehicles_containing_stops_list = []
        for veh in self.__non_assigned_vehicles_list:
            current_stop_id = veh.route.current_stop.location.label
            next_stops_ids_list = list(map(lambda x: x.location.label, veh.route.next_stops))

            # print(type(first_stop_id), type(second_stop_id))
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

    def __calculate_next_stops_arrival_departure_times(self, route):

        BOARDING_TIME = 1
        TRAVEL_TIME = 2

        next_stops_arrival_departure_times_dict_list = []

        current_stop_arrival_departure_times_dict = {
            'location': route.current_stop.location,
            'arrival_time': route.current_stop.arrival_time,
            'departure_time': route.current_stop.arrival_time + BOARDING_TIME
        }
        next_stops_arrival_departure_times_dict_list.append(current_stop_arrival_departure_times_dict)

        previous_stop_time = route.current_stop.arrival_time + BOARDING_TIME
        for stop in route.next_stops:
            stop_arrival_departure_times_dict = {
                'location': stop.location,
                'arrival_time': previous_stop_time + TRAVEL_TIME,
                'departure_time': previous_stop_time + TRAVEL_TIME + BOARDING_TIME
            }
            next_stops_arrival_departure_times_dict_list.append(stop_arrival_departure_times_dict)
            previous_stop_time = previous_stop_time + TRAVEL_TIME + BOARDING_TIME

        return next_stops_arrival_departure_times_dict_list
