import logging

from multimodalsim.optimization.splitter import OneLegSplitter
from multimodalsim.simulator.status import OptimizationStatus

logger = logging.getLogger(__name__)


class Optimization(object):

    def __init__(self, dispatcher, splitter=None, fixed_time_interval=5):
        self.__status = OptimizationStatus.IDLE
        self.__splitter = OneLegSplitter() if splitter is None else splitter
        self.__dispatcher = dispatcher
        self.__fixed_time_interval = fixed_time_interval

    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, status):
        if isinstance(status, OptimizationStatus):
            self.__status = status
        else:
            raise TypeError("status must be an Enum of type OptimizationStatus.")

    @property
    def fixed_time_interval(self):
        return self.__fixed_time_interval

    def split(self, request, state):
        return self.__splitter.split(request, state)

    def dispatch(self, state):
        return self.__dispatcher.dispatch(state)


class OptimizationResult(object):

    def __init__(self, state, modified_requests, modified_vehicles):
        self.state = state
        self.modified_requests = modified_requests
        self.modified_vehicles = modified_vehicles
