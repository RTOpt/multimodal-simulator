from multimodalsim.config.config import Config

import os


class RequestsGeneratorConfig(Config):
    def __init__(self,
                 config_file=os.path.join(os.path.dirname(__file__),
                                          "ini/cap_requests_generator.ini")):
        super().__init__(config_file)

    @property
    def max_connection_time(self):
        return int(self._config_parser["connections"]["max_connection_time"])

    @property
    def release_time_delta(self):
        return int(self._config_parser["requests"]["release_time_delta"])

    @property
    def ready_time_delta(self):
        return int(self._config_parser["requests"]["ready_time_delta"])

    @property
    def due_time_delta(self):
        return int(self._config_parser["requests"]["due_time_delta"])

    @property
    def id_col(self):
        return self._config_parser["cap_columns"]["id"]

    @property
    def arrival_time_col(self):
        return self._config_parser["cap_columns"]["arrival_time"]

    @property
    def boarding_time_col(self):
        return self._config_parser["cap_columns"]["boarding_time"]

    @property
    def origin_stop_id_col(self):
        return self._config_parser["cap_columns"]["origin_stop_id"]

    @property
    def destination_stop_id_col(self):
        return self._config_parser["cap_columns"]["destination_stop_id"]

    @property
    def boarding_type_col(self):
        return self._config_parser["cap_columns"]["boarding_type"]

    @property
    def origin_stop_lat_col(self):
        return self._config_parser["cap_columns"]["origin_stop_lat"]

    @property
    def origin_stop_lon_col(self):
        return self._config_parser["cap_columns"]["origin_stop_lon"]

    @property
    def destination_stop_lat_col(self):
        return self._config_parser["cap_columns"]["destination_stop_lat"]

    @property
    def destination_stop_lon_col(self):
        return self._config_parser["cap_columns"]["destination_stop_lon_col"]
    
    @property
    def planned_arrival_time_col(self):
        return self._config_parser["cap_columns"]["planned_arrival_time"]
