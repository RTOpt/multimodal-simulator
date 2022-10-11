import csv
import ast
from datetime import datetime, timedelta

from multimodalsim.simulator.network import Node
from multimodalsim.simulator.request import Trip
from multimodalsim.simulator.vehicle import LabelLocation, Stop, GPSLocation, \
    Vehicle, Route


class DataReader(object):
    def __init__(self):
        pass

    def get_vehicles(self):
        raise NotImplementedError('get_vehicle_data not implemented')

    def get_trips(self):
        raise NotImplementedError('get_request_data not implemented')


class ShuttleDataReader(DataReader):
    def __init__(self, requests_file_path, vehicles_file_path,
                 nodes_file_path):
        super().__init__()
        self.__requests_file_path = requests_file_path
        self.__vehicles_file_path = vehicles_file_path
        self.__nodes_file_path = nodes_file_path

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
            reader = csv.reader(rFile, delimiter=';')
            next(reader, None)
            nb_requests = 1
            for row in reader:
                trip = Trip(str(nb_requests),
                            GPSLocation(Node(None,
                                             (ast.literal_eval(row[0]),
                                              ast.literal_eval(row[1])))),
                            GPSLocation(Node(None,
                                             (ast.literal_eval(row[2]),
                                              ast.literal_eval(row[3])))),
                            int(row[4]),
                            int(row[5]), int(row[6]), int(row[7]))

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
                start_time = int(row[1])
                start_stop_location = GPSLocation(Node(None, (ast.literal_eval(
                    row[2]), ast.literal_eval(row[3]))))
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
                nodes.append(Node(row[0], (ast.literal_eval(row[1]),
                                           ast.literal_eval(row[2]))))

        return nodes


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
                 stop_times_file_name="stop_times.txt",
                 calendar_dates_file_name="calendar_dates.txt",
                 trips_file_name="trips.txt"):
        super().__init__()
        self.__data_folder = data_folder
        self.__requests_file_path = requests_file_path
        self.__stop_times_path = data_folder + stop_times_file_name
        self.__calendar_dates_path = data_folder + calendar_dates_file_name
        self.__trips_path = data_folder + trips_file_name

        self.__CAPACITY = 10

    def get_trips(self):
        trips = []
        with open(self.__requests_file_path, 'r') as requests_file:
            requests_reader = csv.reader(requests_file, delimiter=';')
            next(requests_reader, None)
            nb_requests = 1
            for row in requests_reader:
                ready_date_string, ready_time_string = row[3].split(" ")
                ready_time = self.__get_timestamp_from_date_and_time_strings(
                    ready_date_string, ready_time_string)

                due_date_string, due_time_string = row[4].split(" ")
                due_time = self.__get_timestamp_from_date_and_time_strings(
                    due_date_string, due_time_string)

                release_date_string, release_time_string = row[5].split(" ")
                release_time = self.__get_timestamp_from_date_and_time_strings(
                    release_date_string, release_time_string)

                trip = Trip(str(nb_requests), LabelLocation(str(row[0])),
                            LabelLocation(str(row[1])), int(row[2]),
                            ready_time, due_time, release_time)

                trips.append(trip)
                nb_requests += 1

        return trips

    def get_vehicles(self):
        self.__read_stop_times()
        self.__read_calendar_dates()
        self.__read_trips()

        vehicles = []

        for trip_id, stop_time_list in self.__stop_times_by_trip_id_dict. \
                items():
            service_id = self.__trip_service_dict[trip_id]
            dates_list = self.__service_dates_dict[service_id]
            for date in dates_list:
                vehicle, next_stops = self.__get_vehicle_and_next_stops(
                    trip_id, stop_time_list, date)

                vehicle.route = Route(vehicle, next_stops)

                vehicles.append(vehicle)

        return vehicles

    def __get_vehicle_and_next_stops(self, trip_id, stop_time_list,
                                     date_string):

        vehicle_id = trip_id

        # For buses, the bus schedule is known at the beginning of the
        # simulation.
        release_time = 0

        start_stop_time = stop_time_list[0]  # Initial stop
        start_stop_arrival_time = \
            self.__get_timestamp_from_date_and_time_strings(
                date_string, start_stop_time.arrival_time)
        start_stop_departure_time = \
            self.__get_timestamp_from_date_and_time_strings(
                date_string, start_stop_time.departure_time)
        start_stop_location = LabelLocation(start_stop_time.stop_id)
        start_stop = Stop(start_stop_arrival_time, start_stop_departure_time,
                          start_stop_location)

        next_stops = self.__get_next_stops(stop_time_list, date_string)

        vehicle = Vehicle(vehicle_id, start_stop_arrival_time, start_stop,
                          self.__CAPACITY, release_time)

        return vehicle, next_stops

    def __get_next_stops(self, stop_time_list, date_string):
        next_stops = []
        for stop_time in stop_time_list[1:]:
            arrival_time = self.__get_timestamp_from_date_and_time_strings(
                date_string, stop_time.arrival_time)
            departure_time = self.__get_timestamp_from_date_and_time_strings(
                date_string, stop_time.departure_time)

            next_stop = Stop(arrival_time, departure_time, LabelLocation(
                stop_time.stop_id))
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

    def __read_stop_times(self):
        self.__stop_times_by_trip_id_dict = {}
        with open(self.__stop_times_path, 'r') as stop_times_file:
            stop_times_reader = csv.reader(stop_times_file, delimiter=',')
            next(stop_times_reader, None)
            for stop_times_row in stop_times_reader:
                stop_time = self.StopTime(*stop_times_row)
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

    class StopTime:
        def __init__(self, trip_id, arrival_time, departure_time, stop_id,
                     stop_sequence, pickup_type, drop_off_type):
            self.trip_id = trip_id
            self.arrival_time = arrival_time
            self.departure_time = departure_time
            self.stop_id = stop_id
            self.stop_sequence = stop_sequence
            self.pickup_type = pickup_type
            self.drop_off_type = drop_off_type
