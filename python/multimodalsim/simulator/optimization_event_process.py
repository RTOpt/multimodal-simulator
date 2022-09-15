import copy
import logging

from python.multimodalsim.simulator.event import Event
from python.multimodalsim.simulator.request import PassengerUpdate
from python.multimodalsim.simulator.status import OptimizationStatus
from python.multimodalsim.simulator.vehicle import RouteUpdate

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
        optimization_result = env.optimization.dispatch(state)

        EnvironmentUpdate(optimization_result, self.queue).add_to_queue()

        return 'Optimize process is implemented'


class EnvironmentUpdate(Event):
    def __init__(self, optimization_result, queue):
        super().__init__('EnvironmentUpdate', queue)
        self.optimization_result = optimization_result

    def process(self, env):

        env.optimization.update_status(OptimizationStatus.UPDATEENVIRONMENT)

        # Patrick: Temporary solution to prevent circular import. Maybe the code should be rearranged.
        from python.multimodalsim.simulator.passenger_event_process import PassengerAssignment
        for trip in self.optimization_result.modified_requests:
            # next_vehicles_ids = [veh.id for veh in trip.next_vehicles] if trip.next_legs is not None else None
            # logger.debug("trip.next_legs={}".format(trip.next_legs))
            current_leg = trip.current_leg
            next_legs = trip.next_legs

            passenger_update = PassengerUpdate(trip.current_leg.assigned_vehicle.id, trip.req_id, current_leg,
                                               next_legs)
            PassengerAssignment(passenger_update, self.queue).add_to_queue()

        # Patrick: Temporary solution to prevent circular import. Maybe the code should be rearranged.
        from python.multimodalsim.simulator.vehicle_event_process import VehicleNotification
        for veh in self.optimization_result.modified_vehicles:
            if veh.route.current_stop is not None:
                current_stop_modified_passengers_to_board = [trip for trip in veh.route.current_stop.passengers_to_board
                                                             if trip in self.optimization_result.modified_requests]
                logger.debug("modified passengers: {}".format([trip.req_id for trip in current_stop_modified_passengers_to_board]))
                current_stop_departure_time = veh.route.current_stop.departure_time
            else:
                current_stop_modified_passengers_to_board = None
                current_stop_departure_time = None

            next_stops = veh.route.next_stops
            route_update = RouteUpdate(veh.id,
                                       current_stop_modified_passengers_to_board=
                                       current_stop_modified_passengers_to_board,
                                       next_stops=next_stops,
                                       current_stop_departure_time=current_stop_departure_time,
                                       assigned_trips=veh.route.assigned_trips)
            VehicleNotification(route_update, self.queue).add_to_queue()

        EnvironmentIdle(self.queue).add_to_queue()

        return 'Environment Update process is implemented'


class EnvironmentIdle(Event):
    def __init__(self, queue):
        super().__init__('EnvironmentIdle', queue)

    def process(self, env):
        env.optimization.update_status(OptimizationStatus.IDLE)

        return 'Environment Idle process is implemented'
