import json

import networkx as nx
from geopy import distance

from multimodalsim.config.config import RequestsGeneratorConfig
from multimodalsim.reader.requests_generator import CAPFormatter


class AvailableConnectionsExtractor:
    def __init__(self, cap_file_path, stop_times_file_path,
                 config_file="config/cap_requests_generator.ini"):
        self.__cap_formatter = CAPFormatter(cap_file_path,
                                            stop_times_file_path)

        config = RequestsGeneratorConfig(config_file)
        self.__max_connection_time = config.max_connection_time
        self.__available_connections = None

    def extract_available_connections(self, max_distance):
        formatted_cap_df = \
            self.__cap_formatter.format_cap(self.__max_connection_time)

        cap_wit_lags_df = self.__add_lags_to_cap(formatted_cap_df)
        connections_different_stops_df = \
            self.__get_connections_with_different_stops_df(cap_wit_lags_df)

        connections_connected_components = \
            self.__get_stop_connections_connected_components(
                connections_different_stops_df, max_distance)

        self.__available_connections = [sorted(list(c)) for c in
                                        connections_connected_components]

        return self.__available_connections

    def save_to_json(self, available_connections_file_path):
        if self.__available_connections is None:
            raise ValueError("Available connections must be extracted first!")

        with open(available_connections_file_path, 'w') as f:
            json.dump(self.__available_connections, f)

    def __add_lags_to_cap(self, formatted_cap_df):
        cap_columns = ["CL_ID_CLIENT", "L_CHRONOBUS",
                       "L_CHRONOBUS_DESCRIPTION", "D_CHRONOBUS_DESC",
                       "D_CHRONOBUS_DESCRIPTION_DESC", "S_H_DEP_REEL28",
                       "D_H_ARR_REEL28_DESC", "boarding_type",
                       "L_LAT_ARRET", "L_LON_ARRET", "D_LAT_STOP_DESC",
                       "D_LON_STOP_DESC"]
        cap_with_lags_df = \
            formatted_cap_df.sort_values(["CL_ID_CLIENT", "S_H_DEP_REEL28"])[
                cap_columns].dropna()

        cap_with_lags_df["STOP_MONTEE_COORD"] = list(
            zip(cap_with_lags_df["L_LAT_ARRET"],
                cap_with_lags_df["L_LON_ARRET"]))
        cap_with_lags_df["STOP_DESC_COORD"] = list(
            zip(cap_with_lags_df["D_LAT_STOP_DESC"],
                cap_with_lags_df["D_LON_STOP_DESC"]))

        cap_grouped_by_id_client_columns = cap_with_lags_df.groupby(
            "CL_ID_CLIENT")

        cap_with_lags_df["D_CHRONOBUS_DESC_lag"] = \
            cap_grouped_by_id_client_columns["D_CHRONOBUS_DESC"].shift(1)
        cap_with_lags_df["STOP_DESC_COORD_lag"] = \
            cap_grouped_by_id_client_columns["STOP_DESC_COORD"].shift(1)

        return cap_with_lags_df

    def __get_connections_with_different_stops_df(self, cap_with_lags_df):
        connections_columns = ["boarding_type", "L_CHRONOBUS",
                               "D_CHRONOBUS_DESC_lag", "STOP_MONTEE_COORD",
                               "STOP_DESC_COORD_lag"]
        connections_df = cap_with_lags_df[
            cap_with_lags_df["boarding_type"] == "Correspondance"][
            connections_columns]
        connections_different_stops_df = connections_df[
            connections_df["L_CHRONOBUS"] != connections_df[
                "D_CHRONOBUS_DESC_lag"]].dropna()

        return connections_different_stops_df

    def __get_stop_connections_connected_components(
            self, connections_different_stops_df, max_distance):
        connections_different_stops_df[
            "stops_distance"] = connections_different_stops_df.apply(
            lambda x: distance.distance(x["STOP_MONTEE_COORD"],
                                        x["STOP_DESC_COORD_lag"]).km, axis=1)

        connections_different_stops_max_dist_df = \
            connections_different_stops_df[
                connections_different_stops_df[
                    "stops_distance"] < max_distance]

        stop_connections_graph = nx.Graph()

        connections_different_stops_max_dist_df.apply(
            lambda x: stop_connections_graph.add_edge(
                int(x["L_CHRONOBUS"]), int(x["D_CHRONOBUS_DESC_lag"])), axis=1)
        connections_connected_components = sorted(
            nx.connected_components(stop_connections_graph), key=len,
            reverse=True)

        return connections_connected_components
