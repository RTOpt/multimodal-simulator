from enum import Enum


class RequestStatus(Enum):
    """Represents the different status of Requests"""
    PENDING = 1
    PICKING = 2
    ONBOARD = 3
    COMPLETE = 4


class VehicleStatus(Enum):
    """Represents the different status of Vehicles"""
    ACTIVE = 1
    INACTIVE = 2


class StopType:
    """ Represents the different type of stops """
    DEPOT = 0
    PICKUP = 1
    DROPOFF = 2
    CURRENT = 3
    WAIT = 4


class Action(Enum):
    """Action to take for an event"""
    ARRIVE = 1
    DEPART = 2
    BOARDING = 3
    ALIGHT = 4
    REQUEST = 5


class Decision(Enum):
    """Decision to make for an event"""
    AFFECT = 1
    ROUTING = 1
