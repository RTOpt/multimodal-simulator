from multimodalsim.config.config import Config


class SimulationConfig(Config):
    def __init__(self, config_file="config/ini/simulation.ini"):
        super().__init__(config_file)

    @property
    def speed(self):
        return int(self._config_parser["time_sync_event"]["speed"])

    @property
    def time_step(self):
        return int(self._config_parser["time_sync_event"]["time_step"])

    @property
    def max_time(self):
        if len(self._config_parser["general"]["max_time"]) == 0:
            max_time = None
        else:
            max_time = float(self._config_parser["general"]["max_time"])

        return max_time
