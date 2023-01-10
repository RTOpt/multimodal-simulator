import pandas as pd
import logging

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

                request_legs.append(
                    (row[self.__origin_stop_id_col], row[self.__destination_stop_id_col],
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

        self.__requests_df["origin"] = self.__requests_df[self.__origin_stop_id_col]
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
        # self.__filter()
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
