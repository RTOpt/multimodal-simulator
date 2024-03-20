from enum import Enum
from typing import TypeVar


Status = TypeVar('Status', bound=Enum)


class PassengerStatus(Enum):
    """Represent the different status of Requests"""
    RELEASE = 1
    ASSIGNED = 2
    READY = 3
    ONBOARD = 4
    COMPLETE = 5


class VehicleStatus(Enum):
    """Represent the different status of Vehicles"""
    RELEASE = 1
    IDLE = 2
    BOARDING = 3
    ENROUTE = 4
    ALIGHTING = 5
    COMPLETE = 6


class OptimizationStatus(Enum):
    """Represent the different status of Optimization"""
    IDLE = 1
    OPTIMIZING = 2
    UPDATEENVIRONMENT = 3
