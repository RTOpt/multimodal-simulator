import logging

from python.multimodalsim.logger.formatter import ColoredFormatter
from python.multimodalsim.simulator.passenger_event_process import PassengerRelease
from python.multimodalsim.simulator.vehicle_event_process import VehicleReady

logger = logging.getLogger(__name__)


def configure_logger(log_level=logging.DEBUG, log_filename=None):
    logging.basicConfig(filename=log_filename, level=log_level)

    # Replace default handler with custom handler
    console_stream_handler = logging.StreamHandler()
    console_stream_handler.setFormatter(ColoredFormatter())
    # Add fmt="%(message)s" as argument if you only want to see the output (without time and line numbers).

    root_logger = logging.getLogger()

    # Remove default handler
    for h in root_logger.handlers:
        root_logger.removeHandler(h)

    # Add custom handler
    root_logger.addHandler(console_stream_handler)
    root_logger.info("log_level={}".format(log_level))


def init_simulation(queue, request_data_list, vehicle_data_list):
    for vehicle_data_dict in vehicle_data_list:
        VehicleReady(vehicle_data_dict, queue).add_to_queue()

    for request_data_dict in request_data_list:
        PassengerRelease(request_data_dict, queue).add_to_queue()


def simulate(env, queue, request_data_list, vehicle_data_list):
    init_simulation(queue, request_data_list, vehicle_data_list)

    # main loop of the simulation
    while not queue.is_empty():
        print_environment(queue.env)

        event_time, event_index, current_event = queue.pop()

        env.current_time = event_time

        logger.info(
            "current_time={} | event_time={} | current_event={}".format(env.current_time, event_time, current_event))
        process_event = current_event.process(env)
        logger.info("process_event: {}".format(process_event))

    logger.info("\n***************\nEND OF SIMULATION\n***************")
    print_environment(queue.env)


def print_environment_status(env):
    logger.info("\n***************\nENVIRONMENT STATUS")
    logger.info("env.current_time={}".format(env.current_time))
    logger.info("OptimizationStatus: {}".format(env.optimization.status))
    logger.info("Vehicles:")
    for vehicle in env.get_vehicles():
        logger.info("{}: {}".format(vehicle.id, vehicle.route.status))
    logger.info("Requests:")
    for request in env.get_trips():
        logger.info("{}: {}".format(request.req_id, request.status))
    logger.info("***************\n")


def print_environment(env):
    logger.info("\n***************\nENVIRONMENT STATUS")
    logger.info("env.current_time={}".format(env.current_time))
    logger.info("OptimizationStatus: {}".format(env.optimization.status))
    logger.info("Vehicles:")
    for veh in env.get_vehicles():
        assigned_requests_id = [req.req_id for req in veh.route.assigned_trips]

        logger.info(
            "{}: status: {}, start_time: {}, assigned_trips: {}".format(veh.id, veh.route.status, veh.start_time,
                                                                        assigned_requests_id))
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
        trip.current_leg.assigned_vehicle
        assigned_vehicle_id = trip.current_leg.assigned_vehicle.id if trip.current_leg.assigned_vehicle is not None \
            else None
        current_leg = {"O": trip.current_leg.origin.__str__(), "D": trip.current_leg.destination.__str__(),
                       "veh_id": trip.current_leg.assigned_vehicle.id} \
            if trip.current_leg.assigned_vehicle is not None \
            else {"O": trip.current_leg.origin.__str__(), "D": trip.current_leg.destination.__str__()}
        previous_legs = [{"O": leg.origin.__str__(), "D": leg.destination.__str__(), "vehicle": leg.assigned_vehicle.id}
                         for leg in trip.previous_legs] \
            if hasattr(trip, 'previous_legs') and trip.previous_legs is not None else None
        next_legs = [{"O": leg.origin.__str__(), "D": leg.destination.__str__()} for leg in trip.next_legs] \
            if hasattr(trip, 'next_legs') and trip.next_legs is not None else None
        logger.info("{}: status: {}, OD: ({},{}), release: {}, ready: {}, due: {}, current_leg: {}, "
                    "previous_legs: {}, next_legs: {}, assigned_vehicle_id: {}".
                    format(trip.req_id, trip.status, trip.origin, trip.destination, trip.release_time, trip.ready_time,
                           trip.due_time, current_leg, previous_legs, next_legs, assigned_vehicle_id))
        logger.info("***************\n")


class Visualization(object):
    """plots solutions"""


def display_instance(instances):
    for i in instances:
        logger.info(i)
