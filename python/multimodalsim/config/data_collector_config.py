from multimodalsim.config.config import Config

import os


class DataCollectorConfig(Config):
    def __init__(self,
                 config_file=os.path.join(os.path.dirname(__file__),
                                          "ini/data_collector.ini")):
        super().__init__(config_file)

    def get_vehicles_columns(self):
        vehicles_columns = {
            "id": self._config_parser["vehicles"]["id"],
            "time": self._config_parser["vehicles"]["time"],
            "status": self._config_parser["vehicles"]["status"],
            "previous_stops":
                self._config_parser["vehicles"]["previous_stops"],
            "current_stop": self._config_parser["vehicles"]["current_stop"],
            "next_stops": self._config_parser["vehicles"]["next_stops"],
            "assigned_legs": self._config_parser["vehicles"]["assigned_legs"],
            "onboard_legs": self._config_parser["vehicles"]["onboard_legs"],
            "alighted_legs": self._config_parser["vehicles"]["alighted_legs"],
            "cumulative_distance":
                self._config_parser["vehicles"]["cumulative_distance"],
            "stop_lon": self._config_parser["vehicles"]["stop_lon"],
            "stop_lat": self._config_parser["vehicles"]["stop_lat"],
            "lon": self._config_parser["vehicles"]["lon"],
            "lat": self._config_parser["vehicles"]["lat"],
            "polylines": self._config_parser["vehicles"]["polylines"],
            "mode": self._config_parser["vehicles"]["mode"]
        }

        return vehicles_columns

    def get_trips_columns(self):
        trips_columns = {
            "id": self._config_parser["trips"]["id"],
            "time": self._config_parser["trips"]["time"],
            "status": self._config_parser["trips"]["status"],
            "assigned_vehicle": self._config_parser["trips"][
                "assigned_vehicle"],
            "current_location": self._config_parser["trips"][
                "current_location"],
            "previous_legs": self._config_parser["trips"]["previous_legs"],
            "current_leg": self._config_parser["trips"]["current_leg"],
            "next_legs": self._config_parser["trips"]["next_legs"],
            "name": self._config_parser["trips"]["name"]
        }

        return trips_columns
    
    def get_trips_details_columns(self):
        trips_details_columns = {
            "id": self._config_parser["trips_details"]["id"],
            "wait_before_boarding": self._config_parser["trips_details"]["wait_before_boarding"],
            "onboard_time": self._config_parser["trips_details"]["onboard_time"],
            "transfer_time": self._config_parser["trips_details"]["transfer_time"],
        }

        return trips_details_columns

    def get_events_columns(self):
        events_columns = {
            "name": self._config_parser["events"]["name"],
            "time": self._config_parser["events"]["time"],
            "priority": self._config_parser["events"]["priority"],
            "index": self._config_parser["events"]["index"]
        }

        return events_columns
