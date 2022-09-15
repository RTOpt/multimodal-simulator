import logging

from python.multimodalsim.simulator.status import OptimizationStatus

logger = logging.getLogger(__name__)


class Optimization(object):

    def __init__(self, splitter, dispatcher):
        self.status = OptimizationStatus.IDLE
        self.splitter = splitter
        self.dispatcher = dispatcher

    def split(self, request, state):
        return self.splitter.split(request, state)

    def dispatch(self, state):
        return self.dispatcher.dispatch(state)

    def update_status(self, status):
        self.status = status


class ShuttleGreedyOptimization(Optimization):

    def __init__(self, splitter, dispatcher):
        super().__init__(splitter, dispatcher)


class FixedLineOptimization(Optimization):

    def __init__(self, splitter, dispatcher):
        super().__init__(splitter, dispatcher)


class OptimizationResult(object):

    def __init__(self, state, modified_requests, modified_vehicles):
        self.state = state
        self.modified_requests = modified_requests
        self.modified_vehicles = modified_vehicles
