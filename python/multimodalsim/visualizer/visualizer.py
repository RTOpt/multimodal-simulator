import logging

logger = logging.getLogger(__name__)


class Visualizer(object):

    def __init__(self):
        pass

    def visualize_environment(self, env, event_time, event_index, current_event):
        pass


class ConsoleVisualizer(Visualizer):

    def __init__(self):
        super().__init__()
        self.__last_time = None

    def visualize_environment(self, env, event_time, event_index, current_event):

        if self.__last_time is None or env.current_time != self.__last_time:
            logger.info("current_time={}".format(env.current_time))
            self.__last_time = env.current_time

        logger.debug("visualize_environment")

        logger.debug(
            "current_time={} | event_time={} | event_index={} | current_event={}".format(env.current_time,
                                                                                         event_time,
                                                                                         event_index,
                                                                                         current_event))
        logger.debug("\n***************\nENVIRONMENT STATUS")
        logger.debug("env.current_time={}".format(env.current_time))
        logger.debug("OptimizationStatus: {}".format(env.optimization.status))
        logger.debug("Environment:")
        logger.debug("--trips={}".format([trip.req_id for trip in env.trips]))
        logger.debug("--assigned_trips={}".format([trip.req_id for trip in env.assigned_trips]))
        logger.debug("--non_assigned_trips={}".format([trip.req_id for trip in env.non_assigned_trips]))
        logger.debug("--vehicles={}".format([veh.id for veh in env.vehicles]))
        logger.debug("--assigned_vehicles={}".format([veh.id for veh in env.assigned_vehicles]))
        logger.debug("--non_assigned_vehicles={}".format([veh.id for veh in env.non_assigned_vehicles]))
        logger.debug("Vehicles:")
        for veh in env.get_vehicles():
            assigned_legs_id = [leg.req_id for leg in veh.route.assigned_legs]
            onboard_legs_id = [leg.req_id for leg in veh.route.onboard_legs]
            alighted_legs_id = [leg.req_id for leg in veh.route.alighted_legs]

            logger.debug(
                "{}: status: {}, start_time: {}, assigned_legs: {}, "
                "onboard_legs: {}, alighted_legs: {}".format(veh.id, veh.route.status, veh.start_time,
                                                             assigned_legs_id, onboard_legs_id, alighted_legs_id))
            logger.debug("  --previous_stops:")
            for stop in veh.route.previous_stops:
                logger.debug("   --{}: {}".format(stop.location, stop))
            logger.debug("  --current_stop:")
            if veh.route.current_stop is not None:
                logger.debug("   --{}: {}".format(veh.route.current_stop.location, veh.route.current_stop))
            else:
                logger.debug("   --{}".format(veh.route.current_stop))
            logger.debug("  --next_stops:")
            for stop in veh.route.next_stops:
                logger.debug("   --{}: {}".format(stop.location, stop))
        logger.debug("Requests:")
        for trip in env.get_trips():
            assigned_vehicle_id = trip.current_leg.assigned_vehicle.id if trip.current_leg.assigned_vehicle is not None \
                else None
            current_leg = {"O": trip.current_leg.origin.__str__(), "D": trip.current_leg.destination.__str__(),
                           "veh_id": trip.current_leg.assigned_vehicle.id} \
                if trip.current_leg.assigned_vehicle is not None \
                else {"O": trip.current_leg.origin.__str__(), "D": trip.current_leg.destination.__str__()}
            previous_legs = [
                {"O": leg.origin.__str__(), "D": leg.destination.__str__(), "vehicle": leg.assigned_vehicle.id}
                for leg in trip.previous_legs] \
                if hasattr(trip, 'previous_legs') and trip.previous_legs is not None else None
            next_legs = [{"O": leg.origin.__str__(), "D": leg.destination.__str__()} for leg in trip.next_legs] \
                if hasattr(trip, 'next_legs') and trip.next_legs is not None else None
            logger.debug("{}: status: {}, OD: ({},{}), release: {}, ready: {}, due: {}, current_leg: {}, "
                         "previous_legs: {}, next_legs: {}, assigned_vehicle_id: {}".
                         format(trip.req_id, trip.status, trip.origin, trip.destination, trip.release_time,
                                trip.ready_time,
                                trip.due_time, current_leg, previous_legs, next_legs, assigned_vehicle_id))
            logger.debug("***************\n")
