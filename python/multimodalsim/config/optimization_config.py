from multimodalsim.config.config import Config

import os


class OptimizationConfig(Config):
    def __init__(self,
                 config_file: str = os.path.join(os.path.dirname(__file__),
                                                 "ini/optimization.ini")):
        super().__init__(config_file)

    @property
    def freeze_interval(self) -> int:
        return int(self._config_parser["general"]["freeze_interval"])

    @property
    def multiple_optimize_events(self) -> str:
        return self._config_parser.getboolean("general",
                                              "multiple_optimize_events")

    @property
    def batch(self) -> float:
        config_batch = \
            self._config_parser["general"]["batch"]
        if len(config_batch) == 0:
            batch = None
        else:
            batch = float(config_batch)

        return batch

    @property
    def asynchronous(self) -> bool:
        return self._config_parser.getboolean("asynchronous", "asynchronous")

    @property
    def max_optimization_time(self) -> float:
        config_max_optimization_time = \
            self._config_parser["asynchronous"]["max_optimization_time"]
        if len(config_max_optimization_time) == 0:
            max_optimization_time = None
        else:
            max_optimization_time = float(config_max_optimization_time)

        return max_optimization_time

    @property
    def termination_waiting_time(self) -> float:
        return float(self._config_parser["asynchronous"][
                         "termination_waiting_time"])
