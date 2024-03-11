from multimodalsim.config.config import Config

import os


class DataAnalyzerConfig(Config):
    def __init__(
            self,
            config_file: str = os.path.join(os.path.dirname(__file__),
                                            "ini/data_analyzer.ini")) -> None:
        super().__init__(config_file)

    @property
    def ghg_e(self) -> float:
        return float(self._config_parser["parameters"]["ghg_e"])

    @property
    def events_table(self) -> str:
        return self._config_parser["parameters"]["events_table"]

    @property
    def vehicles_table(self) -> str:
        return self._config_parser["parameters"]["vehicles_table"]

    @property
    def trips_table(self) -> str:
        return self._config_parser["parameters"]["trips_table"]
