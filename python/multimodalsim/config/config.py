import configparser
import logging

logger = logging.getLogger(__name__)


class Config:

    def __init__(self, config_file):
        self.__config_file = config_file
        self._config_parser = configparser.ConfigParser()
        self._config_parser.read(self.__config_file)


class DataContainerConfig(Config):

    def __init__(self, config_file="config/data_container.ini"):
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
            "alighted_legs": self._config_parser["vehicles"]["alighted_legs"]
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
            "next_legs": self._config_parser["trips"]["next_legs"]
        }

        return trips_columns

    def get_events_columns(self):

        events_columns = {
            "name": self._config_parser["events"]["name"],
            "time": self._config_parser["events"]["time"],
            "priority": self._config_parser["events"]["priority"],
            "index": self._config_parser["events"]["index"]
        }

        return events_columns
