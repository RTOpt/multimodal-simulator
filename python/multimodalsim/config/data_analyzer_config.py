from multimodalsim.config.config import Config


class DataAnalyzerConfig(Config):
    def __init__(self, config_file="config/ini/data_analyzer.ini"):
        super().__init__(config_file)

    @property
    def ghg_e(self):
        return float(self._config_parser["parameters"]["ghg_e"])

    @property
    def events_table(self):
        return self._config_parser["parameters"]["events_table"]

    @property
    def vehicles_table(self):
        return self._config_parser["parameters"]["vehicles_table"]

    @property
    def trips_table(self):
        return self._config_parser["parameters"]["trips_table"]