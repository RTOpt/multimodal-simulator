import math

from networkx import shortest_path

from multimodalsim.optimization.dispatcher import ShuttleDispatcher
from multimodalsim.shuttle.solution_construction import cvrp_pdp_tw_he_obj_cost
from multimodalsim.simulator.vehicle import GPSLocation, Stop


class ShuttleGreedyDispatcher(ShuttleDispatcher):

    def __init__(self, network):
        super().__init__()
        self.__network = network

        # The time difference between the arrival and the departure time (10
        # seconds).
        self.__boarding_time = 10

    def optimize(self, trips, vehicles):

        vehicles_with_current_stops = \
            [veh for veh in vehicles if veh.route.current_stop
             is not None]
        non_assigned_vehicles_sorted_by_departure_time = sorted(
            vehicles_with_current_stops,
            key=lambda x: x.route.current_stop.departure_time)

        potential_non_assigned_trips = trips

        routes, shuttle_dispatcher = cvrp_pdp_tw_he_obj_cost(
            self.__network, potential_non_assigned_trips,
            non_assigned_vehicles_sorted_by_departure_time)

        current_stop_departure_time_by_vehicle_id = {}
        next_stops_by_vehicle_id = {}
        vehicle_trips_by_vehicle_id = {}

        for dispatch in shuttle_dispatcher:
            vehicle = dispatch['vehicle']
            vehicle_trips_by_vehicle_id[vehicle.id] = {"vehicle": vehicle,
                                                          "trips": []}
            for req in dispatch['assigned_requests']:

                path = self.__get_path(
                    self.__network,
                    req.origin.gps_coordinates.get_coordinates(),
                    req.destination.gps_coordinates.get_coordinates())

                # TODO: departure_time may not be defined correctly.
                current_stop_departure_time_by_vehicle_id[vehicle.id] \
                    = req.ready_time

                if hasattr(vehicle.route.current_stop.location,
                           'gps_coordinates'):
                    previous_node = \
                        vehicle.route.current_stop.location.gps_coordinates
                else:
                    previous_node = \
                        vehicle.route.current_stop.location

                departure_time = \
                    current_stop_departure_time_by_vehicle_id[vehicle.id]
                next_stops_by_vehicle_id[vehicle.id] = []
                for node in path:
                    if previous_node.get_node_id() != node:
                        distance = \
                            self.__network[previous_node.get_node_id()][
                                node][
                                'length']
                        if distance > 0:
                            arrival_time = departure_time + distance
                            departure_time = \
                                arrival_time + self.__boarding_time \
                                    if node != path[-1] else math.inf

                            location = GPSLocation(
                                self.__network.nodes[node]['Node'])
                            stop = Stop(arrival_time, departure_time,
                                        location)

                            next_stops_by_vehicle_id[vehicle.id].append(stop)

                            previous_node = self.__network.nodes[node][
                                'Node']

                vehicle_trips_by_vehicle_id[vehicle.id]["trips"].append(req)

        return current_stop_departure_time_by_vehicle_id, \
               next_stops_by_vehicle_id, vehicle_trips_by_vehicle_id

    def __find_shortest_path(self, G, o, d):
        path = shortest_path(G, source=o, target=d, weight='length')
        # path_length = path_weight(G, path, weight='length')

        return path

    def __get_path(self, G, node1, node2):
        for node in G.nodes(data=True):
            if (node[1]['pos'][0], node[1]['pos'][1]) == node1:
                origin = node[0]
            if (node[1]['pos'][0], node[1]['pos'][1]) == node2:
                destination = node[0]
        path = self.__find_shortest_path(G, origin, destination)
        # path_cost = get_manhattan_distance(node1, node2)
        return path