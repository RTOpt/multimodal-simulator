import sys
import logging
import argparse

# sys.path.append('C:/Users/asmam/PycharmProjects/SimulatorMultimodal')

from event_queue import EventQueue
from python.logger.formatter import ColoredFormatter
from python.optimization.optimization import ShuttleOptimization, BusOptimization
from python.simulator.passenger_event_process import PassengerRelease
from vehicle_event_process import *

from read_data import *
from environment import *

logger = logging.getLogger(__name__)


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

        # Patrick: Should we update env.current_time here?
        env.current_time = event_time

        logger.info("current_time={} | event_time={} | current_event={}".format(env.current_time, event_time, current_event))
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
    for request in env.get_requests():
        logger.info("{}: {}".format(request.req_id, request.status))
    logger.info("***************\n")


def print_environment(env):
    logger.info("\n***************\nENVIRONMENT STATUS")
    logger.info("env.current_time={}".format(env.current_time))
    logger.info("OptimizationStatus: {}".format(env.optimization.status))
    logger.info("Vehicles:")
    for veh in env.get_vehicles():
        assigned_requests_id = [req.req_id for req in veh.route.assigned_requests]
        logger.info("{}: status: {}, start_time: {}, assigned_requests: {}".format(veh.id, veh.route.status, veh.start_time,
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
    for req in env.get_requests():
        assigned_vehicle_id = req.assigned_vehicle.id if req.assigned_vehicle is not None else None
        logger.info("{}: status: {}, OD: ({},{}), release: {}, ready: {}, due: {}, assigned_vehicle: {}".
              format(req.req_id, req.status, req.origin, req.destination, req.release_time, req.ready_time,
                     req.due_time,
                     assigned_vehicle_id))
    logger.info("***************\n")


class Visualization(object):
    """plots solutions"""


def display_instance(instances):
    for i in instances:
        logger.info(i)


def create_environment_from_files(nodes_file_path, requests_file_path, vehicles_file_path):
    nodes = read_file_nodes(nodes_file_path)
    g = create_graph(nodes)

    opt = ShuttleOptimization()
    env = Environment(opt, g)

    request_data_list = read_file_requests(requests_file_path)
    vehicle_data_list = read_file_vehicles(vehicles_file_path)

    return env, request_data_list, vehicle_data_list


def create_bus_environment_from_files(requests_file_path, vehicles_file_path):
    opt = BusOptimization()
    env = Environment(opt)

    request_data_list = read_file_bus_requests(requests_file_path)
    vehicle_data_list = read_file_bus_vehicles(vehicles_file_path)

    return env, request_data_list, vehicle_data_list


def add_arguments(parser):
    parser.add_argument("-r", "--requests", help="path to the file containing the requests")
    parser.add_argument("-v", "--vehicles", help="path to the file containing the vehicles")
    parser.add_argument("-n", "--nodes", help="path to the file containing the nodes (with 'shuttle' only)")
    parser.add_argument("--gtfs", help="input files are in the gtfs format", action="store_true")
    parser.add_argument("type", help="type of optimization ('shuttle' or 'bus')")
    parser.add_argument("--log-level", help="the log level (by default: DEBUG)", default="DEBUG")


def check_arguments(args, ):
    if args.type != "shuttle" and args.type != "bus":
        raise ValueError("The type of optimization must be either 'shuttle' or 'bus'!")
    elif args.type == "shuttle" and args.nodes is None:
        raise ValueError("Shuttle optimization requires the path to the nodes (--nodes)!")
    elif (args.type == "shuttle" or args.type == "bus") and args.requests is None:
        raise ValueError("Shuttle optimization requires the path to the requests (--requests)!")
    elif (args.type == "shuttle" or args.type == "bus") and args.vehicles is None:
        raise ValueError("Shuttle optimization requires the path to the vehicles (--vehicles)!")

    numeric_log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_log_level, int):
        raise ValueError("The argument --log-level is invalid: {}".format(loglevel))


def configure_logger(log_level=logging.DEBUG, log_filename=None):
    logging.basicConfig(filename=log_filename, level=log_level)

    # Replace default handler with custom handler
    console_stream_handler = logging.StreamHandler()
    console_stream_handler.setFormatter(ColoredFormatter())

    root_logger = logging.getLogger()

    # Remove default handler
    for h in root_logger.handlers:
        root_logger.removeHandler(h)

    # Add custom handler
    root_logger.addHandler(console_stream_handler)
    root_logger.info("log_level={}".format(log_level))


def main(argv):
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()

    check_arguments(args)

    configure_logger(log_level=args.log_level)

    requests_file_path = args.requests
    vehicles_file_path = args.vehicles

    if args.type == "shuttle":
        logger.info("SHUTTLE")
        nodes_file_path = args.nodes
        env, request_data_list, vehicle_data_list = create_environment_from_files(nodes_file_path, requests_file_path,
                                                                                  vehicles_file_path)
    elif args.type == "bus":
        logger.info("BUS")
        env, request_data_list, vehicle_data_list = create_bus_environment_from_files(requests_file_path,
                                                                                      vehicles_file_path)

    eq = EventQueue(env)
    simulate(env, eq, request_data_list, vehicle_data_list)


if __name__ == '__main__':
    main(sys.argv)
