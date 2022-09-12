from event import Event
# from passenger_event_process import PassengerAssignment
from request import PassengerUpdate
from vehicle import *
from network import *
from python.optimization import optimization

import copy

logger = logging.getLogger(__name__)


class Optimize(Event):
    def __init__(self, time, queue):
        super().__init__('Optimize', queue, time)
        self.queue = queue

    def process(self, env):
        if env.optimization.status.name != 'IDLE':
            self.time += 1
            self.add_to_queue()
            return 'Optimize event has been put back in the queue'

        env.optimization.update_status(OptimizationStatus.OPTIMIZING)

        # The variable state contains a deep copy of the environment so that we do not modify the environment during the
        # optimization.
        state = copy.deepcopy(env)
        optimization_result = env.optimization.optimize(state)

        # OLD Code :
        # EnvironmentUpdate(optimization_result, self.queue).process(env)

        EnvironmentUpdate(optimization_result, self.queue).add_to_queue()

        return 'Optimize process is implemented'


class EnvironmentUpdate(Event):
    def __init__(self, optimization_result, queue):
        super().__init__('EnvironmentUpdate', queue)
        self.optimization_result = optimization_result

    def process(self, env):

        env.optimization.update_status(OptimizationStatus.UPDATEENVIRONMENT)

        # Patrick: Temporary solution to prevent circular import. Maybe the code should be rearranged.
        from passenger_event_process import PassengerAssignment
        for req in self.optimization_result.modified_requests:
            # next_vehicles_ids = [veh.id for veh in req.next_vehicles] if req.next_legs is not None else None
            logger.debug("req.next_legs={}".format(req.next_legs))
            next_legs = req.next_legs if hasattr(req, 'next_legs') else None
            passenger_update = PassengerUpdate(req.assigned_vehicle.id, req.req_id, next_legs)
            PassengerAssignment(passenger_update, self.queue).add_to_queue()

        # Patrick: Temporary solution to prevent circular import. Maybe the code should be rearranged.
        from vehicle_event_process import VehicleNotification, VehicleBoarding
        for veh in self.optimization_result.modified_vehicles:
            if (veh.route.current_stop is not None) and (len(veh.route.current_stop.boarding_passengers) != 0):
                current_stop_passengers_to_board = veh.route.current_stop.passengers_to_board
                current_stop_departure_time = veh.route.current_stop.departure_time
            else:
                current_stop_passengers_to_board = None
                current_stop_departure_time = None

            next_stops = veh.route.next_stops
            route_update = RouteUpdate(veh.id, current_stop_passengers_to_board=current_stop_passengers_to_board,
                                       next_stops=next_stops,
                                       current_stop_departure_time=current_stop_departure_time,
                                       assigned_requests=veh.route.assigned_requests)
            VehicleNotification(route_update, self.queue).add_to_queue()

        EnvironmentIdle(self.queue).add_to_queue()

        return 'Environment Update process is implemented'


class EnvironmentIdle(Event):
    def __init__(self, queue):
        super().__init__('EnvironmentIdle', queue)

    def process(self, env):
        env.optimization.update_status(OptimizationStatus.IDLE)

        return 'Environment Idle process is implemented'
