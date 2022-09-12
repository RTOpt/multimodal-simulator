from networkx.algorithms.shortest_paths.generic import shortest_path

from python.simulator.network import get_manhattan_distance
from python.simulator.status import OptimizationStatus, PassengersStatus
from python.simulator.vehicle import Stop, GPSLocation
from python.simulator.vehicle_event_process import VehicleNotification


class Optimization(object):

    def __init__(self):
        self.status = OptimizationStatus.IDLE

    def optimize(self):
        raise NotImplementedError('optimize not implemented')

    # Patrick: Added
    def update_status(self, status):
        self.status = status


class ShuttleOptimization(Optimization):

    def __init__(self):
        super().__init__()

    def optimize(self, state):
        BOARDING_TIME = 1 # Time between arrival_time and departure_time

        print("\n******************\nOPTIMIZE (GreedyOptimization):\n")
        print("current_time={}".format(state.current_time))

        non_assigned_requests = state.get_non_assigned_requests()
        non_assigned_vehicles = state.get_non_assigned_vehicles()

        print("non_assigned_requests={}".format(list(req.req_id for req in non_assigned_requests)))
        print("non_assigned_vehicles={}".format(list(veh.id for veh in non_assigned_vehicles)))

        request_vehicle_pairs_list = []
        modified_requests = []
        modified_vehicles = []

        non_assigned_vehicles_sorted_by_departure_time = sorted(non_assigned_vehicles,
                                                                key=lambda x: x.route.current_stop.departure_time)
        for req in non_assigned_requests:
            potential_non_assigned_vehicles = list(x for x in non_assigned_vehicles_sorted_by_departure_time
                                                          if x.route.current_stop.departure_time >= req.ready_time)
            # The passenger must be ready before the departure time.
            print("potential_non_assigned_vehicles={}".format(list(veh.id for veh in potential_non_assigned_vehicles)))
            if len(potential_non_assigned_vehicles) != 0:

                assigned_vehicle = potential_non_assigned_vehicles.pop(0)
                # Asma : The assigned vehicle must be removed from the non_assigned_vehicles_sorted_by_departure_time
                non_assigned_vehicles_sorted_by_departure_time = [x for x in non_assigned_vehicles_sorted_by_departure_time
                                                                   if not assigned_vehicle.id == x.id]

                path = self.__get_path(state.network, req.origin.gps_coordinates.get_coordinates(),
                                       req.destination.gps_coordinates.get_coordinates())

                req.assign_route(path)
                print("req.path={}".format(list("(" + str(node.get_coordinates()[0]) + "," +
                                                str(node.get_coordinates()[1]) + ")" for node in req.path)))

                departure_time = assigned_vehicle.route.current_stop.departure_time
                # previous_node = path[0]

                # Asma : temporary solution - the code should be rearranged to
                if hasattr(assigned_vehicle.route.current_stop.location, 'gps_coordinates'):
                    previous_node = assigned_vehicle.route.current_stop.location.gps_coordinates
                else:
                    previous_node = assigned_vehicle.route.current_stop.location

                next_stops = []
                # OLD CODE : for node in path[1:]:
                for node in path:
                    # First node is excluded because it is the current_stop. Asma not necessarily
                    distance = get_manhattan_distance(previous_node.get_coordinates(), node.get_coordinates())
                    arrival_time = departure_time + distance
                    departure_time = arrival_time + BOARDING_TIME
                    location = node
                    stop = Stop(None, arrival_time, departure_time, location)
                    next_stops.append(stop)
                    previous_node = node

                assigned_vehicle.route.next_stops.extend(next_stops)
                req.assign_vehicle(assigned_vehicle)
                assigned_vehicle.route.assign(req)
                req.update_passenger_status(PassengersStatus.ASSIGNED)

                print(assigned_vehicle)

                print("assigned_vehicle={}".format(req.assigned_vehicle.id))
                print("assigned_requests={}".format(list(req.req_id for req in
                                                         assigned_vehicle.route.assigned_requests)))

                request_vehicle_pairs_list.append((req, assigned_vehicle))
                modified_requests.append(req)
                modified_vehicles.append(assigned_vehicle)



        print("request_vehicle_pairs_list:")
        for req, veh in request_vehicle_pairs_list:
            print("---(req_id={},veh_id={})".format(req.req_id, veh.id))

        for req, veh in request_vehicle_pairs_list:
            veh.route.current_stop.passengers_to_board.append(req)

            for stop in veh.route.next_stops:
                if req.origin.gps_coordinates.get_coordinates() == stop.location.get_coordinates():
                    stop.passengers_to_board.append(req)
                elif req.destination.gps_coordinates.get_coordinates() == stop.location.get_coordinates():
                    stop.passengers_to_alight.append(req)

        print("END OPTIMIZE\n*******************")

        return OptimizationResult(state, modified_requests, modified_vehicles)

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
        self.__all_vehicles = None

    def optimize(self, state):
        print("\n******************\nOPTIMIZE (BusOptimization):\n")
        print("current_time={}".format(state.current_time))

        self.__non_assigned_vehicles_list = state.get_non_assigned_vehicles()
        self.__non_assigned_released_requests_list = state.get_non_assigned_requests()
        self.__all_vehicles = state.vehicles

        request_vehicle_pairs_list = []
        modified_requests = []
        modified_vehicles = []

        for req in self.__non_assigned_released_requests_list:
            potential_vehicles_list = self.__get_vehicles_containing_stops_list(req.origin.label, req.destination.label)
            for veh in potential_vehicles_list:
                if veh.route.current_stop is not None and req.origin.label == veh.route.current_stop.location.label:
                    req_origin_stop_departure_time = veh.route.current_stop.departure_time
                else:
                    req_origin_stop_departure_time = self.__get_stop_departure_time_by_stop_id(req.origin.label,
                                                                                               veh.route.next_stops)
                if req_origin_stop_departure_time is not None and req.ready_time <= req_origin_stop_departure_time:
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

        return OptimizationResult(state, modified_requests, modified_vehicles)

    def __get_vehicles_containing_stops_list(self, first_stop_id, second_stop_id):
        vehicles_containing_stops_list = []
        for veh in self.__all_vehicles:
            # self.__all_vehicles instead of self.__non_assigned_vehicles_list since requests can be assigned to
            # vehicles that were already assigned other requests.
            if veh.route.current_stop is not None:
                current_stop_id = veh.route.current_stop.location.label
            else:
                current_stop_id = None
            next_stops_ids_list = list(x.location.label for x in veh.route.next_stops)

            if first_stop_id == current_stop_id and second_stop_id in next_stops_ids_list:
                vehicles_containing_stops_list.append(veh)
            elif first_stop_id != current_stop_id and first_stop_id in next_stops_ids_list and second_stop_id in next_stops_ids_list:
                if next_stops_ids_list.index(first_stop_id) < next_stops_ids_list.index(second_stop_id):
                    vehicles_containing_stops_list.append(veh)

        return vehicles_containing_stops_list

    def __get_stop_departure_time_by_stop_id(self, stop_id, stops_list):
        stop_departure_time = None
        for stop in stops_list:
            if stop_id == stop.location.label:
                stop_departure_time = stop.departure_time

        return stop_departure_time


class OptimizationResult(object):

    def __init__(self, state, modified_requests, modified_vehicles):
        self.state = state
        self.modified_requests = modified_requests
        self.modified_vehicles = modified_vehicles
