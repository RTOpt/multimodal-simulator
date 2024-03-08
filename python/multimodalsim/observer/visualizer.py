import logging
from typing import Optional

import multimodalsim.simulator.environment as environment
from multimodalsim.simulator.event import Event
from multimodalsim.statistics.data_analyzer import DataAnalyzer

logger = logging.getLogger(__name__)


class Visualizer(object):

    def __init__(self):
        pass

    def visualize_environment(self, env: 'environment.Environment',
                              current_event: Optional[Event] = None,
                              event_index: Optional[int] = None,
                              event_priority: Optional[int] = None):
        pass


class ConsoleVisualizer(Visualizer):

    def __init__(self, data_analyzer: Optional[DataAnalyzer] = None,
                 stats_delta_time: int = 10):
        super().__init__()
        self.__data_analyzer = data_analyzer
        self.__last_time = None
        self.__stats_time = 0
        self.__stats_delta_time = stats_delta_time

    def visualize_environment(self, env: 'environment.Environment',
                              current_event: Optional[Event] = None,
                              event_index: Optional[int] = None,
                              event_priority: Optional[int] = None):

        if self.__last_time is None or env.current_time != self.__last_time:
            logger.info("current_time={}".format(env.current_time))
            self.__last_time = env.current_time

        if logger.parent.level == logging.DEBUG:
            self.__print_debug(env, current_event, event_index, event_priority)

        if self.__data_analyzer is not None and env.current_time \
                > self.__stats_time + self.__stats_delta_time:
            self.__print_statistics()
            self.__stats_time = env.current_time

    def __print_debug(self, env, current_event, event_index, event_priority):

        logger.debug("visualize_environment")

        if current_event is not None:
            logger.debug(
                "current_time={} | event_time={} | event_index={} | "
                "current_event={} | event_priority={}".format(
                    env.current_time, current_event.time, event_index,
                    current_event, event_priority))
        else:
            logger.debug(
                "event_time={} | event_index={} | current_event={} | "
                "event_priority={}".format(
                    env.current_time, event_index, current_event,
                    event_priority))
        logger.debug("\n***************\nENVIRONMENT STATUS")
        logger.debug("env.current_time={}".format(env.current_time))
        logger.debug("OptimizationStatus: {}".format(env.optimization.status))
        logger.debug("Environment:")
        logger.debug("--trips={}".format([trip.id for trip in env.trips]))
        logger.debug("--assigned_trips={}".format([trip.id for trip
                                                   in env.assigned_trips]))
        logger.debug("--non_assigned_trips={}".format(
            [trip.id for trip in env.non_assigned_trips]))
        logger.debug("--vehicles={}".format(
            [veh.id for veh in env.vehicles]))
        logger.debug("Vehicles:")
        for veh in env.vehicles:
            route = env.get_route_by_vehicle_id(veh.id)
            assigned_legs_id = [leg.id for leg in route.assigned_legs]
            onboard_legs_id = [leg.id for leg in route.onboard_legs]
            alighted_legs_id = [leg.id for leg in route.alighted_legs]

            logger.debug(
                "{}: status: {}, start_time: {}, end_time: {}, "
                "assigned_legs: {},  onboard_legs: {}, "
                "alighted_legs: {}".format(veh.id, veh.status,
                                           veh.start_time, veh.end_time,
                                           assigned_legs_id, onboard_legs_id,
                                           alighted_legs_id))
            logger.debug("  --previous_stops:")
            for stop in route.previous_stops:
                logger.debug("   --{}: {}".format(stop.location, stop))
            logger.debug("  --current_stop:")
            if route.current_stop is not None:
                logger.debug("   --{}: {}".format(
                    route.current_stop.location, route.current_stop))
            else:
                logger.debug("   --{}".format(route.current_stop))
            logger.debug("  --next_stops:")
            for stop in route.next_stops:
                logger.debug("   --{}: {}".format(stop.location, stop))
        logger.debug("Requests:")
        for trip in env.trips:
            if trip.current_leg is not None:
                current_leg = {"O": trip.current_leg.origin.__str__(),
                               "D": trip.current_leg.destination.__str__(),
                               "veh_id":
                                   trip.current_leg.assigned_vehicle.id,
                               "boarding_time": trip.current_leg.boarding_time,
                               "alighting_time":
                                   trip.current_leg.alighting_time} \
                    if trip.current_leg.assigned_vehicle is not None \
                    else {"O": trip.current_leg.origin.__str__(),
                          "D": trip.current_leg.destination.__str__()}
            else:
                current_leg = None
            previous_legs = [
                {"O": leg.origin.__str__(), "D": leg.destination.__str__(),
                 "veh_id": leg.assigned_vehicle.id,
                 "boarding_time": leg.boarding_time,
                 "alighting_time": leg.alighting_time}
                for leg in trip.previous_legs] if hasattr(
                trip, 'previous_legs') and trip.previous_legs is not None \
                else None
            next_legs = [{"O": leg.origin.__str__(),
                          "D": leg.destination.__str__()}
                         for leg in trip.next_legs] \
                if hasattr(trip, 'next_legs') and trip.next_legs is not None \
                else None
            logger.debug("{}: status: {}, OD: ({},{}), release: {}, ready: {},"
                         " due: {}, current_leg: {}, "
                         "previous_legs: {}, next_legs: {}".
                         format(trip.id, trip.status, trip.origin,
                                trip.destination, trip.release_time,
                                trip.ready_time,
                                trip.due_time, current_leg, previous_legs,
                                next_legs))
            logger.debug("***************\n")

        if current_event is not None:
            logger.debug(
                "current_time={} | event_time={} | event_index={} | "
                "current_event={} | event_priority={}".format(
                    env.current_time, current_event.time, event_index,
                    current_event, event_priority))

    def __print_statistics(self):

        vehicles_stats = self.__data_analyzer.get_vehicles_statistics()
        logger.info(vehicles_stats)
        modes = self.__data_analyzer.modes
        if len(modes) > 1:
            for mode in modes:
                mode_vehicles_stats = \
                    self.__data_analyzer.get_vehicles_statistics(mode)
                logger.info("{}: {}".format(mode, mode_vehicles_stats))

        trips_stats = self.__data_analyzer.get_trips_statistics()
        logger.info(trips_stats)
        modes = self.__data_analyzer.modes
        if len(modes) > 1:
            for mode in modes:
                mode_trips_stats = \
                    self.__data_analyzer.get_trips_statistics(mode)
                logger.info("{}: {}".format(mode, mode_trips_stats))

