import logging
from typing import Optional

from multimodalsim.simulator.stop import Location
from multimodalsim.simulator.vehicle import Vehicle, Route

logger = logging.getLogger(__name__)


class Coordinates:

    def __init__(self) -> None:
        pass

    def update_position(self, vehicle: Vehicle,
                        route: Route, time: float) -> Location:
        raise NotImplementedError(
            'Coordinates.update_position not implemented')

    def update_polylines(
            self, route) -> Optional[dict[str, tuple[str, list[float]]]]:
        raise NotImplementedError(
            'Coordinates.update_polylines not implemented')
