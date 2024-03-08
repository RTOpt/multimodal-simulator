from multimodalsim.config.config import Config

import os


class CoordinatesOSRMConfig(Config):
    def __init__(self,
                 config_file: str = os.path.join(os.path.dirname(__file__),
                                                 "ini/coordinates_osrm.ini")):
        super().__init__(config_file)

    @property
    def url(self) -> str:
        return self._config_parser["parameters"]["url"]
