import logging

logger = logging.getLogger(__name__)


class Dispatcher(object):

    def __init__(self):
        pass

    def dispatch(self, state):
        """Optimize the vehicle routing and the trip-route assignment.

        Input:
            -state: An object of type State that corresponds to a partial deep
             copy of the environment.

        Output:
            -optimization_result: An object of type OptimizationResult, that
             specifies, based on the results of the optimization, how the
             environment should be modified.
        """

        raise NotImplementedError('dispatch not implemented')



