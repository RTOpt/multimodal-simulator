import pandas as pd
import logging
import sys
sys.path.insert(1, r"C:\Users\kklau\Desktop\Simulator")

from multimodalsim.config.request_generator_config \
    import RequestsGeneratorConfig

logger = logging.getLogger(__name__)


class RequestsGenerator:
    def __init__(self):
        pass

    def generate_requests(self):
        pass


class CAPRequestsGenerator(RequestsGenerator):

    def __init__(self, cap_file_path, stop_times_file_path, config=None):
        super().__init__()

        config = RequestsGeneratorConfig() if config is None else config
        self.__load_config(config)

        self.__cap_formatter = CAPFormatter(cap_file_path,
                                            stop_times_file_path, config)

        self.__requests_df = None

    @property
    def requests_df(self):
        return self.__requests_df

    def generate_requests(self, max_connection_time=None,
                          release_time_delta=None, ready_time_delta=None,
                          due_time_delta=None):

        if max_connection_time is None:
            max_connection_time = self.__max_connection_time
        if release_time_delta is None:
            release_time_delta = self.__release_time_delta
        if ready_time_delta is None:
            ready_time_delta = self.__ready_time_delta
        if due_time_delta is None:
            due_time_delta = self.__due_time_delta

        formatted_cap_df = self.__cap_formatter.format_cap(max_connection_time)
        self.__extract_requests_from_cap(formatted_cap_df)
        self.__format_requests(release_time_delta, ready_time_delta,
                               due_time_delta)
        self.__get_first_possible_transfers_for_requests(time_limit=180)

        return self.__requests_df

    def save_to_csv(self, requests_file_path, requests_df=None):
        if requests_df is None and self.__requests_df is None:
            raise ValueError("Requests must be generated first!")

        if requests_df is None:
            requests_df = self.__requests_df

        requests_df.to_csv(requests_file_path, sep=";")

    def __load_config(self, config):
        self.__max_connection_time = config.max_connection_time
        self.__release_time_delta = config.release_time_delta
        self.__ready_time_delta = config.ready_time_delta
        self.__due_time_delta = config.due_time_delta
        self.__id_col = config.id_col
        self.__arrival_time_col = config.arrival_time_col
        self.__boarding_time_col = config.boarding_time_col
        self.__origin_stop_id_col = config.origin_stop_id_col
        self.__destination_stop_id_col = config.destination_stop_id_col
        self.__boarding_type_col = config.boarding_type_col

    def __extract_requests_from_cap(self, formatted_cap_df):
        cap_grouped_by_id_client = formatted_cap_df.groupby(self.__id_col)

        all_request_rows_list = []
        for name, group in cap_grouped_by_id_client:
            request_legs = []
            first_row = True
            sorted_group = group.sort_values(self.__boarding_time_col)
            for index, row in sorted_group.iterrows():
                if first_row:
                    request_row = row[[self.__id_col,
                                       self.__origin_stop_id_col,
                                       self.__boarding_time_col]]
                    first_row = False

                request_legs.append(
                    (row[self.__origin_stop_id_col],
                     row[self.__destination_stop_id_col],
                     row["S_VEHJOBID_IDJOURNALIER"]))

                if row["boarding_type_lead"] == "1ère montée" or pd.isnull(
                        row["boarding_type_lead"]):
                    request_row = pd.concat([request_row, row[
                        [self.__destination_stop_id_col,
                         self.__arrival_time_col]]])
                    request_row["legs"] = request_legs
                    all_request_rows_list.append(request_row)
                    request_legs = []
                    first_row = True

        self.__requests_df = pd.concat(all_request_rows_list, axis=1).T

        return self.__requests_df

    def __format_requests(self, release_time_delta, ready_time_delta,
                          due_time_delta):

        self.__requests_df["origin"] = \
            self.__requests_df[self.__origin_stop_id_col]
        self.__requests_df["destination"] = \
            self.__requests_df[self.__destination_stop_id_col]
        self.__requests_df["nb_passengers"] = 1
        self.__requests_df["release_time"] = \
            self.__requests_df[self.__boarding_time_col] - release_time_delta
        self.__requests_df["ready_time"] = \
            self.__requests_df[self.__boarding_time_col] - ready_time_delta
        self.__requests_df["due_time"] = \
            self.__requests_df[self.__arrival_time_col] + due_time_delta

        self.__requests_df = self.__requests_df.drop(
            [self.__origin_stop_id_col, self.__boarding_time_col,
             self.__destination_stop_id_col, self.__arrival_time_col], axis=1)
        self.__requests_df["origin"] = self.__requests_df["origin"].apply(int)
        self.__requests_df["destination"] = \
            self.__requests_df["destination"].apply(int)
        self.__requests_df["release_time"] = \
            self.__requests_df["release_time"].apply(int)
        self.__requests_df["ready_time"] = \
            self.__requests_df["ready_time"].apply(int)
        self.__requests_df["due_time"] = \
            self.__requests_df["due_time"].apply(int)

        self.__requests_df.reset_index(drop=True, inplace=True)
        self.__requests_df.reset_index(inplace=True)

        self.__requests_df["ID"] = self.__requests_df[self.__id_col] + "_" \
                                   + self.__requests_df[
                                       "index"].apply(str)
        self.__requests_df.index = self.__requests_df["ID"]
        self.__requests_df.drop([self.__id_col, "index", "ID"], axis=1,
                                inplace=True)

        columns = ["origin", "destination", "nb_passengers", "release_time",
                   "ready_time", "due_time", "legs"]

        self.__requests_df = self.__requests_df[columns]

        return self.__requests_df[columns]

    def __get_first_possible_transfers_for_requests(self, time_limit = 180):
        """ This functions considers requests with multiple legs (passengers with transfers) and evaluates if these could have been earlier.
            If an earlier transfer is possible, the request is updated accordingly. All legs will be evaluated sequentially, and assigned to different vehicles if necessary.
            The function will iterate over all requests until no more improvements are possible.
            To evaluate this, the function takes into account the planned arrival time of the vehicle at the origin of the next leg and checks if any earlier vehicles could have been more beneficial.
            The function will update sef.__requests_df accordingly.

            Inputs:
                time_limit: int, maximum time window to consider before the planned boarding time of the passenger."""
        
        ### First read the stop_times file
        stop_times_df = pd.read_csv(self.__stop_times_file_path, delimiter=";")
        stop_times_df["arrival_time"] = stop_times_df["arrival_time"].apply(int)
        stop_times_df["departure_time"] = stop_times_df["departure_time"].apply(int)
        stop_times_df["stop_id"] = stop_times_df["stop_id"].apply(int)
        stop_times_df["trip_id"] = stop_times_df["trip_id"].apply(int)
        stop_times_df["planned_arrival_time"] = stop_times_df["planned_arrival_time"].apply(int)

        ### Create a dictionary with the stop times for each trip_id.
        stop_times_grouped_by_trip = stop_times_df.groupby("trip_id")
        stop_times_dict = stop_times_grouped_by_trip.apply(lambda x: list(zip(x["arrival_time"], x["departure_time"], x["stop_id"], x["planned_arrival_time"])))
        stop_times_dict = stop_times_dict.to_dict()

        ### To get route_id from trip_id we need to read the trips file
        trips_df = pd.read_csv(self.__trips_file_path, delimiter=";")
        trips_df["trip_id"] = trips_df["trip_id"].apply(int)
        trips_df["route_id"] = trips_df["route_id"].apply(str)
        ### Create a dictionary with the route_id for each trip_id
        route_id_dict = dict(zip(trips_df["trip_id"], trips_df["route_id"]))      

        ### Create a dictionary that for each route_id, and for each stop_id, contains a tuple with the
        ### (arrival time, departure time, trip_id) for all trips that stop at that stop for this route.
        passage_times_at_stops = {}
        all_route_ids = trips_df["route_id"].unique()
        for route_id in all_route_ids:
            passage_times_at_stops[route_id] = {}
        for trip_id in stop_times_dict.keys():
            route_id = route_id_dict[trip_id]
            for arrival_time, departure_time, stop_id, planned_arrival_time in stop_times_dict[trip_id]:
                if stop_id not in passage_times_at_stops[route_id]:
                    passage_times_at_stops[route_id][stop_id] = []
                passage_times_at_stops[route_id][stop_id].append((arrival_time, departure_time, trip_id, planned_arrival_time))
        for route_id in all_route_ids:
            for stop_id in passage_times_at_stops[route_id].keys():
                passage_times_at_stops[route_id][stop_id] = sorted(passage_times_at_stops[route_id][stop_id], key=lambda x: x[3])
        
        ### Read all requests
        requests_df = self.__requests_df.copy()
        ###For each request, check if there are earlier vehicles that could have been used.
        ###If so, update the request accordingly.
        ###The function will iterate over all requests until no more improvements are possible.
        counter = 0
        updated_resquests = {}
        for request_id, request in requests_df.iterrows():
            legs = request["legs"]
            for i in range(1, len(legs)):
                arrival_transfer_stop_id = legs[i-1][1]
                first_trip_id = legs[i-1][2]
                first_route_id = route_id_dict[first_trip_id]
                departure_transfer_stop_id = legs[i][0]
                second_trip_id = legs[i][2]
                second_route_id = route_id_dict[second_trip_id]
                ### Check the planned arrival time of the vehicle at the arrival_transfer_stop_id
                if arrival_transfer_stop_id not in passage_times_at_stops[first_route_id]:
                    continue
                passage_times = passage_times_at_stops[first_route_id][arrival_transfer_stop_id]
                arrival_at_transfer_tuple = next(((arrival_time, departure_time, trip_id, planned_arrival_time) for arrival_time, departure_time, trip_id, planned_arrival_time in passage_times if trip_id == first_trip_id), None)

                ### Check the planned arrival time of the vehicle at the departure_transfer_stop_id
                if departure_transfer_stop_id not in passage_times_at_stops[second_route_id] or arrival_at_transfer_tuple is None:
                    continue
                passage_times = passage_times_at_stops[second_route_id][departure_transfer_stop_id]
                first_departure_from_transfer_tuple = next((stop_tuple for stop_tuple in passage_times if stop_tuple[3] >= arrival_at_transfer_tuple[3] - time_limit), None)
                original_departure_from_transfer_tuple = next((stop_tuple for stop_tuple in passage_times if stop_tuple[2] == second_trip_id), None)
                if first_departure_from_transfer_tuple is None or original_departure_from_transfer_tuple is None:
                    continue
                new_planned_arrival_time = first_departure_from_transfer_tuple[3]
                original_planned_arrival_time = original_departure_from_transfer_tuple[3]
                if new_planned_arrival_time < original_planned_arrival_time:
                    ### Update the leg 
                    new_second_trip_id = first_departure_from_transfer_tuple[2]
                    legs[i] = (legs[i][0], legs[i][1], new_second_trip_id)
                    counter +=1
            request["legs"] = legs
            updated_resquests[request_id] = request
        ### Update the requests_df
        updated_requests_df = pd.DataFrame.from_dict(updated_resquests, orient="index")
        self.__requests_df = updated_requests_df
        print("Number of updated requests: ", counter)


class CAPFormatter:
    def __init__(self, cap_file_path, stop_times_file_path, config):

        self.__load_config(config)

        self.__read_cap_csv(cap_file_path)
        self.__read_stop_times_csv(stop_times_file_path)

    @property
    def cap_df(self):
        return self.__cap_df

    def format_cap(self, max_connection_time):
        self.__preformat()
        self.__filter()
        self.__add_boarding_type(max_connection_time)

        return self.__cap_df

    def __load_config(self, config):
        self.__id_col = config.id_col
        self.__arrival_time_col = config.arrival_time_col
        self.__boarding_time_col = config.boarding_time_col
        self.__origin_stop_id_col = config.origin_stop_id_col
        self.__destination_stop_id_col = config.destination_stop_id_col
        self.__boarding_type_col = config.boarding_type_col
        self.__origin_stop_lat_col = config.origin_stop_lat_col
        self.__origin_stop_lon_col = config.origin_stop_lon_col
        self.__destination_stop_lat_col = config.destination_stop_lat_col
        self.__destination_stop_lon_col = config.destination_stop_lon_col

    def __read_cap_csv(self, cap_file_path):
        self.__cap_df = pd.read_csv(cap_file_path, delimiter=";")

    def __read_stop_times_csv(self, stop_times_file_path):
        self.__stop_times_df = pd.read_csv(stop_times_file_path,
                                           dtype={"stop_id": str})

    def __preformat(self):
        cap_columns = [self.__origin_stop_id_col,
                       self.__destination_stop_id_col,
                       self.__boarding_time_col, self.__arrival_time_col,
                       self.__boarding_type_col, self.__id_col,
                       self.__origin_stop_lat_col, self.__origin_stop_lon_col,
                       self.__destination_stop_lat_col,
                       self.__destination_stop_lon_col,
                       "S_VEHJOBID_IDJOURNALIER"]
        self.__cap_df = self.__cap_df.sort_values(
            [self.__id_col, self.__boarding_time_col])[cap_columns].dropna()
        self.__cap_df = self.__cap_df.astype(
            {self.__origin_stop_id_col: int,
             self.__destination_stop_id_col: int,
             "S_VEHJOBID_IDJOURNALIER": int})
        self.__cap_df = self.__cap_df.astype(
            {self.__origin_stop_id_col: str,
             self.__destination_stop_id_col: str})

        return self.__cap_df

    def __filter(self):

        stop_times_grouped_by_id = self.__stop_times_df.groupby("trip_id")
        stops_by_trip_series = stop_times_grouped_by_id["stop_id"].apply(list)

        cap_with_stops_list_df = self.__cap_df.merge(
            stops_by_trip_series, left_on="S_VEHJOBID_IDJOURNALIER",
            right_index=True)

        cap_with_stops_list_df["trip_exists"] = cap_with_stops_list_df.apply(
            lambda x: x[self.__origin_stop_id_col] in x["stop_id"] and x[
                self.__destination_stop_id_col] in x["stop_id"], axis=1)

        self.__cap_df = cap_with_stops_list_df[
            cap_with_stops_list_df["trip_exists"]]

        non_existent_trips_df = \
            cap_with_stops_list_df[~cap_with_stops_list_df["trip_exists"]]
        non_existent_trips_df.to_csv("non_existent_trips.csv")

        return self.__cap_df

    def __add_boarding_type(self, max_connection_time):
        self.__cap_df.sort_values([self.__id_col, self.__boarding_time_col],
                                  inplace=True)
        cap_grouped_by_id_client = self.__cap_df.groupby(self.__id_col)

        self.__cap_df["arrival_time_lag_lag"] = cap_grouped_by_id_client[
            self.__arrival_time_col].shift(1)
        self.__cap_df["arr_dep_diff"] = \
            self.__cap_df[self.__boarding_time_col] \
            - self.__cap_df["arrival_time_lag_lag"]
        self.__cap_df["boarding_type"] = self.__cap_df.apply(
            lambda x: x[self.__boarding_type_col]
            if x["arr_dep_diff"] < max_connection_time
            else "1ère montée", axis=1)
        self.__cap_df["boarding_type_lead"] = cap_grouped_by_id_client[
            "boarding_type"].shift(-1)

        self.__cap_df[self.__origin_stop_id_col] = self.__cap_df[self.__origin_stop_id_col].apply(
            int)
        self.__cap_df[self.__destination_stop_id_col] = self.__cap_df[
            self.__destination_stop_id_col].apply(int)

        return self.__cap_df
