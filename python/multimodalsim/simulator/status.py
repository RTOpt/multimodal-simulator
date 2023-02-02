from enum import Enum


class PassengersStatus(Enum):
    """Represents the different status of Requests"""
    RELEASE = 1
    ASSIGNED = 2
    READY = 3
    ONBOARD = 4
    COMPLETE = 5


class VehicleStatus(Enum):
    """Represents the different status of Vehicles"""
    RELEASE = 1
    IDLE = 2
    BOARDING = 3
    ENROUTE = 4
    ALIGHTING = 5
    COMPLETE = 6


class OptimizationStatus(Enum):
    IDLE = 1
    OPTIMIZING = 2
    UPDATEENVIRONMENT = 3


# class StopType(Enum):
#     """ Represents the different types of stops """
#     DEPOT = 0
#     PICKUP = 1
#     DROPOFF = 2
#     CURRENT = 3
#     WAIT = 4
#
#
# class Action(Enum):
#     """Action to take for an event"""
#     ARRIVE = 1
#     DEPART = 2
#     BOARDING = 3
#     ALIGHT = 4
#     REQUEST = 5
#
#
# class Decision(Enum):
#     """Decision to make for an event"""
#     AFFECT = 1
#     ROUTING = 1
