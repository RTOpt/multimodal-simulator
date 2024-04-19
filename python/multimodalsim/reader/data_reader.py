import csv
import ast
import logging
from ast import literal_eval
from datetime import datetime, timedelta
import json
from networkx.readwrite import json_graph

import networkx as nx

import os.path
import sys
sys.path.insert(1, r"C:\Users\kklau\Desktop\Simulator")

from multimodalsim.config.data_reader_config import DataReaderConfig
from multimodalsim.simulator.network import Node
from multimodalsim.simulator.request import Trip, Leg
from multimodalsim.simulator.vehicle import LabelLocation, Stop, Vehicle, Route

logger = logging.getLogger(__name__)
sys.path

class DataReader(object):
    def __init__(self):
        pass

    def get_vehicles(self):
        raise NotImplementedError('get_vehicle_data not implemented')

    def get_trips(self):
        raise NotImplementedError('get_request_data not implemented')


class ShuttleDataReader(DataReader):
    def __init__(self, requests_file_path, vehicles_file_path,
                 graph_from_json_file_path=None, sim_end_time=None,
                 vehicles_end_time=None):
        super().__init__()
        self.__network = None
        self.__requests_file_path = requests_file_path
        self.__vehicles_file_path = vehicles_file_path
        self.__graph_from_json_file_path = graph_from_json_file_path

        # The time difference between the arrival and the departure time.
        self.__boarding_time = 30
        self.__sim_end_time = sim_end_time
        self.__vehicles_end_time = vehicles_end_time

    def get_trips(self):
        """ read trip from a file
                   format:
                   requestId, origin, destination, nb_passengers, ready_date,
                   due_date, release_date
            """
        trips = []
        with open(self.__requests_file_path, 'r') as rFile:
            csv_dict_reader = csv.DictReader(rFile, delimiter=';')
            nb_passengers = 1  # Each request corresponds to 1 passenger.
            for row in csv_dict_reader:
                orig_id = str(row['origin'])
                dest_id = str(row['destination'])

                if self.__network is not None:
                    lon_orig = self.__network.nodes[orig_id]["lon"]
                    lat_orig = self.__network.nodes[orig_id]["lat"]

                    lon_dest = self.__network.nodes[dest_id]["lon"]
                    lat_dest = self.__network.nodes[dest_id]["lat"]
                else:
                    lon_orig = lat_orig = None
                    lon_dest = lat_dest = None

                orig_location = LabelLocation(orig_id, lon=lon_orig,
                                              lat=lat_orig)
                dest_location = LabelLocation(dest_id, lon=lon_dest,
                                              lat=lat_dest)

                trip = Trip(str(row['trip_id']),
                            orig_location,
                            dest_location,
                            nb_passengers,
                            int(row['release_time']),
                            int(row['ready_time']),
                            int(row['due_time'])
                            )
                trips.append(trip)

        return trips

    def get_vehicles(self):
        vehicles = []
        routes_by_vehicle_id = {}  # Remains empty

        with open(self.__vehicles_file_path, 'r') as rFile:
            csv_dict_reader = csv.DictReader(rFile, delimiter=';')
            for row in csv_dict_reader:
                vehicle_id = str(row["vehicle_id"])
                start_time = float(row["start_time"])
                capacity = int(row["capacity"])

                stop_id = str(row["start_stop"])

                if self.__network is not None:
                    lon = self.__network.nodes[stop_id]["lon"]
                    lat = self.__network.nodes[stop_id]["lat"]
                else:
                    lon = None
                    lat = None

                mode = str(row["mode"]) if "mode" in row else None

                start_stop_location = LabelLocation(stop_id, lon=lon, lat=lat)

                start_stop = Stop(start_time,
                                  Vehicle.MAX_TIME,
                                  start_stop_location)

                # reusable=True since the vehicles are shuttles.
                vehicle = Vehicle(vehicle_id, start_time, start_stop, capacity,
                                  start_time, self.__vehicles_end_time,
                                  mode=mode, reusable=True)

                vehicles.append(vehicle)

        return vehicles, routes_by_vehicle_id

    def get_json_graph(self):
        with open(self.__graph_from_json_file_path) as f:
            js_graph = json.load(f)

            self.__network = json_graph.node_link_graph(js_graph)
            for node in self.__network.nodes(data=True):
                node[1]['lon'] = node[1]['pos'][0]
                node[1]['lat'] = node[1]['pos'][1]
                coord = (node[1]['pos'][0], node[1]['pos'][1])
                node[1]['pos'] = coord
                node[1]['Node'] = Node(node[1]['Node']['id'], coord)

        return self.__network


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
        routes_by_vehicle_id = {}

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

                routes_by_vehicle_id[vehicle.id] = Route(vehicle, next_stops)

                vehicles.append(vehicle)

        return vehicles, routes_by_vehicle_id


class GTFSReader(DataReader):
    RELEASE_TIME_INTERVAL = 900

    def __init__(self, data_folder, requests_file_path,
                 stops_file_name="stops.txt",
                 stop_times_file_name="stop_times.txt",
                 calendar_dates_file_name="calendar_dates.txt",
                 trips_file_name="trips.txt",
                 routes_file_name="routes.txt",
                 config=None):
        super().__init__()
        self.__data_folder = data_folder
        self.__requests_file_path = requests_file_path
        self.__stops_path = os.path.join(data_folder, stops_file_name)
        self.__stop_times_path = os.path.join(data_folder,stop_times_file_name)
        self.__calendar_dates_path = os.path.join(data_folder,calendar_dates_file_name)
        self.__trips_path = os.path.join(data_folder,trips_file_name)
        self.__routes_path = os.path.join(data_folder,routes_file_name)

        config = DataReaderConfig() if config is None else config
        self.__trips_columns = config.get_trips_columns()

        self.__CAPACITY = 80

        self.__stop_by_stop_id_dict = None
        self.__stop_times_by_trip_id_dict = None
        self.__service_dates_dict = None
        self.__trip_service_dict = None
        self.__trip_route_dict = None
        self.__route_mode_dict = None
        self.__network_graph = None

        self.__release_time_interval = None
        self.__min_departure_time_interval = None

    def save_stop_by_stop_id_dict(self, data_folder):
        """ Save the stop_by_stop_id_dict to a .scv file. """
        savepath = os.path.join(data_folder, "stop_by_stop_id_dict.csv")
        with open(savepath, 'w') as f:
            for key in self.__stop_by_stop_id_dict.keys():
                f.write("%s,%s\n" % (key, self.__stop_by_stop_id_dict[key]))

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
                name = trip_id
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
                            nb_passengers, release_time, ready_time, due_time,
                            name=name)

                if legs_stops_pairs_list is not None:
                    leg_number = 1
                    legs = []
                    for stops_pair in legs_stops_pairs_list:
                        leg_id = trip_id + "_" + str(leg_number)
                        first_stop_id = str(stops_pair[0])
                        second_stop_id = str(stops_pair[1])
                        cap_vehicle_id = str(stops_pair[2])

                        leg = Leg(leg_id, LabelLocation(first_stop_id),
                                  LabelLocation(second_stop_id),
                                  nb_passengers, release_time,
                                  ready_time, due_time, trip)
                        leg.set_cap_vehicle_id(cap_vehicle_id)
                        legs.append(leg)
                        leg_number += 1
                    trip.assign_legs(legs)

                trips.append(trip)
                nb_requests += 1
        return trips

    def get_vehicles(self, release_time_interval=None,
                     min_departure_time_interval=None):

        self.__release_time_interval = self.RELEASE_TIME_INTERVAL \
            if release_time_interval is None else release_time_interval
        self.__min_departure_time_interval = min_departure_time_interval

        self.__read_stops()
        self.__read_stop_times()
        self.__read_calendar_dates()
        self.__read_trips()
        if self.__routes_path is not None:
            self.__read_routes()

        vehicles = []
        routes_by_vehicle_id = {}

        for trip_id, stop_time_list in self.__stop_times_by_trip_id_dict. \
                items():
            vehicle, next_stops = self.__get_vehicle_and_next_stops(
                trip_id, stop_time_list)

            routes_by_vehicle_id[vehicle.id] = Route(vehicle, next_stops)

            vehicles.append(vehicle)

        return vehicles, routes_by_vehicle_id

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

                if current_node[2] - previous_node[2] <= 0 \
                        and previous_node != current_node:
                    logger.warning("{}: previous_node: {} -> current_node: {}"
                                   .format(current_node[2] - previous_node[2],
                                           previous_node, current_node))

                self.__network_graph.add_edge(
                    previous_node, current_node,
                    weight=current_node[2] - previous_node[2])
                previous_node = current_node
        for node1 in self.__network_graph.nodes:
            for node2 in self.__network_graph.nodes:
                if (node1[0] == node2[0] or int(node1[0]) in available_connections
                    and int(node2[0]) in available_connections[int(node1[0])]) \
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

    def __get_vehicle_and_next_stops(self, trip_id, stop_time_list):

        vehicle_id = trip_id

        start_stop_time = stop_time_list[0]  # Initial stop

        start_stop_arrival_time = int(start_stop_time.arrival_time)
        start_stop_departure_time = int(start_stop_time.departure_time)
        start_stop_min_departure_time = \
            start_stop_departure_time - self.__min_departure_time_interval \
                if self.__min_departure_time_interval is not None else None

        start_stop_gtfs = self.__stop_by_stop_id_dict[start_stop_time.stop_id]
        start_stop_location = LabelLocation(start_stop_time.stop_id,
                                            start_stop_gtfs.stop_lon,
                                            start_stop_gtfs.stop_lat)
        start_stop_shape_dist_traveled = \
            float(start_stop_time.shape_dist_traveled) \
                if start_stop_time.shape_dist_traveled is not None else None

        start_stop = Stop(start_stop_arrival_time, start_stop_departure_time,
                          start_stop_location, start_stop_shape_dist_traveled,
                          min_departure_time=start_stop_min_departure_time)

        next_stops = self.__get_next_stops(stop_time_list)

        release_time = start_stop_arrival_time - self.__release_time_interval

        end_time = next_stops[-1].arrival_time if len(next_stops) > 0 \
            else start_stop.arrival_time

        route_id = self.__trip_route_dict[trip_id]
        mode = self.__route_mode_dict[route_id] \
            if self.__route_mode_dict is not None else None

        vehicle = Vehicle(vehicle_id, start_stop_arrival_time, start_stop,
                          self.__CAPACITY, release_time, end_time, mode)

        return vehicle, next_stops

    def __get_next_stops(self, stop_time_list):
        next_stops = []
        for stop_time in stop_time_list[1:]:
            arrival_time = int(stop_time.arrival_time)
            departure_time = int(stop_time.departure_time)
            min_departure_time = \
                departure_time - self.__min_departure_time_interval \
                    if self.__min_departure_time_interval is not None else None
            shape_dist_traveled = float(stop_time.shape_dist_traveled) \
                if stop_time.shape_dist_traveled is not None else None

            stop_gtfs = self.__stop_by_stop_id_dict[
                stop_time.stop_id]
            next_stop = Stop(arrival_time, departure_time,
                             LabelLocation(stop_time.stop_id,
                                           stop_gtfs.stop_lon,
                                           stop_gtfs.stop_lat),
                             shape_dist_traveled,
                             min_departure_time=min_departure_time)
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
        # data_folder = os.path.join("data","fixed_line","gtfs","gtfs-generated-small")
        # self.save_stop_by_stop_id_dict(data_folder)

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
        self.__trip_route_dict = {}
        with open(self.__trips_path, 'r') as trips_file:
            trips_reader = csv.reader(trips_file, delimiter=',')
            next(trips_reader, None)
            for trips_row in trips_reader:
                route_id = trips_row[0]
                service_id = trips_row[1]
                trip_id = trips_row[2]
                self.__trip_service_dict[trip_id] = service_id
                self.__trip_route_dict[trip_id] = route_id

    def __read_routes(self):
        if os.path.isfile(self.__routes_path):
            self.__route_mode_dict = {}
            with open(self.__routes_path, 'r') as routes_file:
                routes_reader = csv.reader(routes_file, delimiter=',')
                next(routes_reader, None)
                for routes_row in routes_reader:
                    route_id = routes_row[0]
                    mode_id = routes_row[4]
                    self.__route_mode_dict[route_id] = mode_id

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
