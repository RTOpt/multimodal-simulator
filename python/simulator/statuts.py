from enum import Enum


class PassengersStatus(Enum):
    """Represents the different status of Requests"""
    RELEASE = 1
    ASSIGNMENT = 2
    ASSIGNED = 3
    READY = 4
    ONBOARD = 5
    COMPLETE = 7


class VehicleStatus(Enum):
    """Represents the different status of Vehicles"""
    BOARDING = 1
    ENROUTE = 2
    ALIGHTING = 3

class EnvironmentStatus(Enum):
    IDLE = 1
    OPTIMIZING = 2
    UPDATEENVIRONMENT = 3

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
