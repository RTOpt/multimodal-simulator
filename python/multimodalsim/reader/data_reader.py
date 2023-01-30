import csv
import ast
import logging
import json
from ast import literal_eval
from datetime import datetime, timedelta
import json
from json import JSONEncoder
import networkx as nx
from networkx.readwrite import json_graph

import networkx as nx

from multimodalsim.config.data_reader_config import DataReaderConfig
from multimodalsim.simulator.network import Node
from multimodalsim.simulator.request import Trip, Leg
from multimodalsim.simulator.vehicle import LabelLocation, Stop, GPSLocation, \
    Vehicle, Route

logger = logging.getLogger(__name__)


class DataReader(object):
    def __init__(self):
        pass

    def get_vehicles(self):
        raise NotImplementedError('get_vehicle_data not implemented')

    def get_trips(self):
        raise NotImplementedError('get_request_data not implemented')


class ShuttleDataReader(DataReader):
    def __init__(self, requests_file_path, vehicles_file_path, nodes_file_path,
                 graph_from_json_file_path=None):
        super().__init__()
        self.__requests_file_path = requests_file_path
        self.__vehicles_file_path = vehicles_file_path
        self.__nodes_file_path = nodes_file_path
        self.__graph_from_json_file_path = graph_from_json_file_path

        # The time difference between the arrival and the departure time.
        self.__boarding_time = 30

    def get_trips(self):
        """ read trip from a file
                   format:
                   requestId, origin, destination, nb_passengers, ready_date,
                   due_date, release_date
            """
        trips = []
        with open(self.__requests_file_path, 'r') as rFile:
            csv_dict_reader = csv.DictReader(rFile, delimiter=';')
            requests_mode_is_car = [row for row in csv_dict_reader if row['mode'] == 'car']
            nb_requests = 1
            nb_passengers = 1
            for row in requests_mode_is_car:
                trip = Trip(nb_requests,
                            GPSLocation(Node(None, (ast.literal_eval(row['origin_x']),
                                                                     ast.literal_eval(row['origin_y'])))),
                            GPSLocation(Node(None, (ast.literal_eval(row['destination_x']), ast.literal_eval(row['destination_y'])))),
                            nb_passengers,
                            float(row['departure_time']),
                            float(row['departure_time'])+60*60*2,
                            float(row['departure_time'])
                            )
                trips.append(trip)
                nb_requests += 1

        return trips

    def get_vehicles(self):
        vehicles = []
        with open(self.__vehicles_file_path, 'r') as rFile:
            reader = csv.reader(rFile, delimiter=';')
            next(reader, None)

            for row in reader:
                vehicle_id = int(row[0])
                start_time = float(row[1])
                start_stop_location = GPSLocation(
                    Node(None, (ast.literal_eval(row[2]),
                                ast.literal_eval(row[3]))))
                capacity = int(row[4])

                start_stop = Stop(start_time,
                                  start_time + self.__boarding_time,
                                  start_stop_location)

                # Patrick: For shuttles, release time is the same as
                # start time, but it could be changed.
                vehicle = Vehicle(vehicle_id, start_time, start_stop, capacity,
                                  start_time)

                vehicles.append(vehicle)

        return vehicles

    def get_nodes(self):
        nodes = []
        with open(self.__nodes_file_path, 'r') as rFile:
            reader = csv.reader(rFile, delimiter=';')
            next(reader, None)
            for row in reader:
                nodes.append(Node(int(row[0]), (ast.literal_eval(row[1]),
                                                ast.literal_eval(row[2]))))

        return nodes

    def get_json_graph(self):
        with open(self.__graph_from_json_file_path) as f:
            js_graph = json.load(f)

            G = json_graph.node_link_graph(js_graph)
            for node in G.nodes(data=True):
                coord = (node[1]['pos'][0], node[1]['pos'][1])
                node[1]['pos'] = coord
                node[1]['Node'] = Node(node[1]['Node']['id'], coord)
                #node[1]['Node']['coordinates'] = coord

        return G


class BusDataReader(DataReader):
    def __init__(self, requests_file_path, vehicles_file_path):
        super().__init__()
        self.__requests_file_path = requests_file_path
        self.__vehicles_file_path = vehicles_file_path

        # The time difference between the arrival and the departure time.
        self.__boarding_time = 100
        # The time required to travel from one stop to the next stop.
        self.__travel_time = 200

    def get_trips(self):
        trips_list = []
        with open(self.__requests_file_path, 'r') as file:
            reader = csv.reader(file, delimiter=';')
            next(reader, None)
            nb_requests = 1
            for row in reader:
                trip = Trip(str(nb_requests), LabelLocation(str(row[0])),
                            LabelLocation(str(row[1])), int(row[2]),
                            int(row[3]), int(row[4]), int(row[5]))

                trips_list.append(trip)
                nb_requests += 1

        return trips_list

    def get_vehicles(self):

        vehicles = []

        with open(self.__vehicles_file_path, 'r') as rFile:
            reader = csv.reader(rFile, delimiter=';')
            next(reader, None)

            for row in reader:
                vehicle_id = int(row[0])
                start_time = int(row[1])

                # For buses, the bus schedule is known at the beginning of the
                # simulation.
                release_time = 0

                stop_ids_list = list(str(x) for x
                                     in list(ast.literal_eval(row[2])))
                start_stop_location = LabelLocation(stop_ids_list[0])

                stop_arrival_time = start_time
                stop_departure_time = stop_arrival_time + self.__boarding_time
                start_stop = Stop(start_time, stop_departure_time,
                                  start_stop_location)

                next_stops = []
                for next_stop_id in stop_ids_list[1:]:
                    next_stop_location = LabelLocation(next_stop_id)
                    stop_arrival_time = \
                        stop_departure_time + self.__travel_time
                    stop_departure_time = \
                        stop_arrival_time + self.__boarding_time
                    next_stop = Stop(stop_arrival_time, stop_departure_time,
                                     next_stop_location)
                    next_stops.append(next_stop)

                capacity = int(row[3])

                vehicle = Vehicle(vehicle_id, start_time, start_stop, capacity,
                                  release_time)

                vehicle.route = Route(vehicle, next_stops)

                vehicles.append(vehicle)

        return vehicles


class GTFSReader(DataReader):
    def __init__(self, data_folder, requests_file_path,
                 stops_file_name="stops.txt",
                 stop_times_file_name="stop_times.txt",
                 calendar_dates_file_name="calendar_dates.txt",
                 trips_file_name="trips.txt",
                 config=None):
        super().__init__()
        self.__data_folder = data_folder
        self.__requests_file_path = requests_file_path
        self.__stops_path = data_folder + stops_file_name
        self.__stop_times_path = data_folder + stop_times_file_name
        self.__calendar_dates_path = data_folder + calendar_dates_file_name
        self.__trips_path = data_folder + trips_file_name

        config = DataReaderConfig() if config is None else config
        self.__trips_columns = config.get_trips_columns()

        self.__CAPACITY = 10

        self.__stop_by_stop_id_dict = None
        self.__stop_times_by_trip_id_dict = None
        self.__service_dates_dict = None
        self.__trip_service_dict = None
        self.__network_graph = None

    def get_trips(self):
        trips = []
        with open(self.__requests_file_path, 'r') as requests_file:
            requests_reader = csv.reader(requests_file, delimiter=';')
            next(requests_reader, None)
            nb_requests = 1
            for row in requests_reader:
                # release_date_string, release_time_string = row[3].split(" ")
                # release_time = self.__get_timestamp_from_date_and_time_strings(
                #     release_date_string, release_time_string)
                #
                # ready_date_string, ready_time_string = row[4].split(" ")
                # ready_time = self.__get_timestamp_from_date_and_time_strings(
                #     ready_date_string, ready_time_string)
                #
                # due_date_string, due_time_string = row[5].split(" ")
                # due_time = self.__get_timestamp_from_date_and_time_strings(
                #     due_date_string, due_time_string)

                trip_id = str(row[self.__trips_columns["id"]])
                origin = str(row[self.__trips_columns["origin"]])
                destination = str(row[self.__trips_columns["destination"]])
                nb_passengers = int(row[self.__trips_columns["nb_passengers"]])
                release_time = int(row[self.__trips_columns["release_time"]])
                ready_time = int(row[self.__trips_columns["ready_time"]])
                due_time = int(row[self.__trips_columns["due_time"]])

                legs_stops_pairs_list = None
                if len(row) - 1 == self.__trips_columns["legs"]:
                    legs_stops_pairs_list = literal_eval(
                        row[self.__trips_columns["legs"]])

                trip = Trip(trip_id,
                            LabelLocation(origin), LabelLocation(destination),
                            nb_passengers, release_time, ready_time, due_time)

                if legs_stops_pairs_list is not None:
                    leg_number = 1
                    legs = []
                    for stops_pair in legs_stops_pairs_list:
                        leg_id = trip_id + "_" + str(leg_number)
                        first_stop_id = str(stops_pair[0])
                        second_stop_id = str(stops_pair[1])

                        leg = Leg(leg_id, LabelLocation(first_stop_id),
                                  LabelLocation(second_stop_id),
                                  nb_passengers, release_time,
                                  ready_time, due_time, trip)
                        legs.append(leg)
                        leg_number += 1
                    trip.assign_legs(legs)

                trips.append(trip)
                nb_requests += 1

        return trips

    def get_vehicles(self, release_time_interval=900):
        self.__read_stops()
        self.__read_stop_times()
        self.__read_calendar_dates()
        self.__read_trips()

        vehicles = []

        for trip_id, stop_time_list in self.__stop_times_by_trip_id_dict. \
                items():
            vehicle, next_stops = self.__get_vehicle_and_next_stops(
                trip_id, stop_time_list, release_time_interval)

            vehicle.route = Route(vehicle, next_stops)

            vehicles.append(vehicle)

        return vehicles

    def get_network_graph(self, available_connections=None, freeze_interval=5):

        available_connections = {} if available_connections is None \
            else available_connections

        if self.__stop_times_by_trip_id_dict is None:
            self.__read_stop_times()

        logger.debug("get_network_graph")

        self.__network_graph = nx.DiGraph()

        for trip_id, stop_time_list in self.__stop_times_by_trip_id_dict. \
                items():

            first_stop_time = stop_time_list[0]
            previous_node = (first_stop_time.stop_id, first_stop_time.trip_id,
                             first_stop_time.arrival_time,
                             first_stop_time.departure_time)

            for stop_time in stop_time_list:

                current_node = (stop_time.stop_id, stop_time.trip_id,
                                stop_time.arrival_time,
                                stop_time.departure_time)

                if current_node[2] - previous_node[2] < 0:
                    logger.warning("{}: previous_node: {} -> current_node: {}"
                                   .format(current_node[2] - previous_node[2],
                                           previous_node, current_node))

                self.__network_graph.add_edge(
                    previous_node, current_node,
                    weight=current_node[2] - previous_node[2])
                previous_node = current_node

        for node1 in self.__network_graph.nodes:
            for node2 in self.__network_graph.nodes:
                if (node1[0] == node2[0] or node1[0] in available_connections
                    and node2[0] in available_connections[node1[0]]) \
                        and node1[1] != node2[1]:
                    # Nodes correspond to same stop but different vehicles
                    if (node2[3] - node1[2]) >= freeze_interval:
                        # Departure time of the second node is greater than or
                        # equal to the arrival time of the first
                        # node. A connection is possible.
                        if node2[3] - node1[2] < 0:
                            logger.warning(
                                "{}: node2: {} -> node1: {}".format(
                                    node2[3] - node1[2], node2, node1))
                        self.__network_graph.add_edge(
                            node1, node2, weight=node2[3] - node1[2])

        return self.__network_graph

    def get_available_connections(self, locations_connected_comp_file_path):

        available_connections = {}

        with open(locations_connected_comp_file_path) as f:
            locations_connected_comp_list = json.load(f)

            for locations_cc in locations_connected_comp_list:
                locations_cc_set = set(locations_cc)
                for location in locations_cc:
                    available_connections[location] = locations_cc_set

        return available_connections

    def __get_vehicle_and_next_stops(self, trip_id, stop_time_list,
                                     release_time_interval):

        vehicle_id = trip_id

        start_stop_time = stop_time_list[0]  # Initial stop

        start_stop_arrival_time = int(start_stop_time.arrival_time)
        start_stop_departure_time = int(start_stop_time.departure_time)

        start_stop_gtfs = self.__stop_by_stop_id_dict[start_stop_time.stop_id]
        start_stop_location = LabelLocation(start_stop_time.stop_id,
                                            start_stop_gtfs.stop_lon,
                                            start_stop_gtfs.stop_lat)
        start_stop_shape_dist_traveled = \
            float(start_stop_time.shape_dist_traveled) \
            if start_stop_time.shape_dist_traveled is not None else None

        start_stop = Stop(start_stop_arrival_time, start_stop_departure_time,
                          start_stop_location, start_stop_shape_dist_traveled)

        next_stops = self.__get_next_stops(stop_time_list)

        release_time = start_stop_arrival_time - release_time_interval

        vehicle = Vehicle(vehicle_id, start_stop_arrival_time, start_stop,
                          self.__CAPACITY, release_time)

        return vehicle, next_stops

    def __get_next_stops(self, stop_time_list):
        next_stops = []
        for stop_time in stop_time_list[1:]:
            arrival_time = int(stop_time.arrival_time)
            departure_time = int(stop_time.departure_time)
            shape_dist_traveled = float(stop_time.shape_dist_traveled) \
                if stop_time.shape_dist_traveled is not None else None

            stop_gtfs = self.__stop_by_stop_id_dict[
                stop_time.stop_id]
            next_stop = Stop(arrival_time, departure_time,
                             LabelLocation(stop_time.stop_id,
                                           stop_gtfs.stop_lon,
                                           stop_gtfs.stop_lat),
                             shape_dist_traveled)
            next_stops.append(next_stop)

        return next_stops

    def __get_timestamp_from_date_and_time_strings(self, date_string,
                                                   time_string):
        date = datetime.strptime(date_string, "%Y%m%d").timestamp()
        hours = int(time_string.split(":")[0])
        minutes = int(time_string.split(":")[1])
        seconds = int(time_string.split(":")[2])
        timestamp = date + timedelta(hours=hours, minutes=minutes,
                                     seconds=seconds).total_seconds()

        return timestamp

    def __read_stops(self):
        self.__stop_by_stop_id_dict = {}
        with open(self.__stops_path, 'r') as stops_file:
            stops_reader = csv.reader(stops_file, delimiter=',')
            next(stops_reader, None)
            for stops_row in stops_reader:
                stop = self.GTFSStop(*stops_row)
                self.__stop_by_stop_id_dict[stop.stop_id] = stop

    def __read_stop_times(self):
        self.__stop_times_by_trip_id_dict = {}
        with open(self.__stop_times_path, 'r') as stop_times_file:
            stop_times_reader = csv.reader(stop_times_file, delimiter=',')
            next(stop_times_reader, None)
            for stop_times_row in stop_times_reader:
                stop_time = self.GTFSStopTime(*stop_times_row)
                if stop_time.trip_id in self.__stop_times_by_trip_id_dict:
                    self.__stop_times_by_trip_id_dict[stop_time.trip_id] \
                        .append(stop_time)
                else:
                    self.__stop_times_by_trip_id_dict[stop_time.trip_id] = \
                        [stop_time]

    def __read_calendar_dates(self):
        self.__service_dates_dict = {}
        with open(self.__calendar_dates_path, 'r') as calendar_dates_file:
            calendar_dates_reader = csv.reader(calendar_dates_file,
                                               delimiter=',')
            next(calendar_dates_reader, None)
            for calendar_dates_row in calendar_dates_reader:
                service_id = calendar_dates_row[0]
                date = calendar_dates_row[1]
                if service_id in self.__service_dates_dict:
                    self.__service_dates_dict[service_id].append(date)
                else:
                    self.__service_dates_dict[service_id] = [date]

    def __read_trips(self):
        self.__trip_service_dict = {}
        with open(self.__trips_path, 'r') as trips_file:
            trips_reader = csv.reader(trips_file, delimiter=',')
            next(trips_reader, None)
            for trips_row in trips_reader:
                service_id = trips_row[1]
                trip_id = trips_row[2]
                self.__trip_service_dict[trip_id] = service_id

    class GTFSStop:
        def __init__(self, stop_id, stop_name, stop_lon, stop_lat):
            self.stop_id = stop_id
            self.stop_name = stop_name
            self.stop_lon = float(stop_lon)
            self.stop_lat = float(stop_lat)

    class GTFSStopTime:
        def __init__(self, trip_id, arrival_time, departure_time, stop_id,
                     stop_sequence, pickup_type, drop_off_type,
                     shape_dist_traveled=None):
            self.trip_id = trip_id
            self.arrival_time = int(arrival_time)
            self.departure_time = int(departure_time)
            self.stop_id = stop_id
            self.stop_sequence = stop_sequence
            self.pickup_type = pickup_type
            self.drop_off_type = drop_off_type
            self.shape_dist_traveled = shape_dist_traveled
