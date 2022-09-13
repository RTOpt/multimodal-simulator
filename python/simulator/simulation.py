import argparse

# sys.path.append('C:/Users/asmam/PycharmProjects/SimulatorMultimodal')

from event_queue import EventQueue
from python.logger.formatter import ColoredFormatter
from python.optimization.optimization import ShuttleOptimization, BusOptimization
from python.simulator.passenger_event_process import PassengerRelease
from vehicle_event_process import *

from environment import *

from python.reader.data_reader import GTFSReader, BusDataReader, ShuttleDataReader

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

        logger.info(
            "{}: status: {}, start_time: {}, assigned_requests: {}".format(veh.id, veh.route.status, veh.start_time,
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
        previous_legs_vehicle = [leg.assigned_vehicle for leg in req.previous_legs] \
            if hasattr(req, 'previous_legs') and req.previous_legs is not None else None
        next_legs_vehicle = [leg.assigned_vehicle for leg in req.next_legs] \
            if hasattr(req, 'next_legs') and req.next_legs is not None else None

        logger.info("{}: status: {}, OD: ({},{}), release: {}, ready: {}, due: {}, assigned_vehicle: {}, "
                    "previous_legs_vehicle: {}, next_legs_vehicle: {}".
                    format(req.req_id, req.status, req.origin, req.destination, req.release_time, req.ready_time,
                           req.due_time, assigned_vehicle_id, previous_legs_vehicle, next_legs_vehicle))
        logger.info("***************\n")


class Visualization(object):
    """plots solutions"""


def display_instance(instances):
    for i in instances:
        logger.info(i)


def add_arguments(parser):
    parser.add_argument("-r", "--requests", help="path to the file containing the requests")
    parser.add_argument("-v", "--vehicles", help="path to the file containing the vehicles")
    parser.add_argument("-n", "--nodes", help="path to the file containing the nodes (with 'shuttle' only)")
    parser.add_argument("type", help="type of optimization ('shuttle' or 'bus')")
    parser.add_argument("--log-level", help="the log level (by default: DEBUG)", default="DEBUG")
    parser.add_argument("--gtfs", help="input files are in the GTFS format", action="store_true")
    parser.add_argument("--gtfs-folder", help="the path to the folder containing the files in the GTFS format")


def check_arguments(args):
    if args.type != "shuttle" and args.type != "bus":
        raise ValueError("The type of optimization must be either 'shuttle' or 'bus'!")
    elif args.type == "shuttle" and args.nodes is None:
        raise ValueError("Shuttle optimization requires the path to the nodes (--nodes)!")
    elif (args.type == "shuttle" or args.type == "bus") and args.requests is None:
        raise ValueError("Shuttle optimization requires the path to the requests (--requests)!")
    elif (args.type == "shuttle" or args.type == "bus") and (args.vehicles is None and not args.gtfs):
        raise ValueError("the path to the vehicles (--vehicles) is required!")

    numeric_log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_log_level, int):
        raise ValueError("The argument --log-level is invalid: {}".format(args.log_level))


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


def main():
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()

    check_arguments(args)

    configure_logger(log_level=args.log_level)

    requests_file_path = args.requests
    vehicles_file_path = args.vehicles

    g = None

    if args.type == "shuttle":
        # Parameters example: shuttle -r ../../data/test0_shuttle/requests.csv -v ../../data/test0_shuttle/vehicles.csv -n ../../data/test0_shuttle/nodes.csv
        logger.info("SHUTTLE")

        nodes_file_path = args.nodes

        data_reader = ShuttleDataReader(requests_file_path, vehicles_file_path, nodes_file_path)
        nodes = data_reader.get_node_data()
        g = create_graph(nodes)

    elif args.type == "bus":
        logger.info("BUS")

        if args.gtfs:
            # Parameters example: bus - -gtfs - -gtfs - folder.. /../ data / bus_test / gtfs_test / -r.. /../ data / bus_test / gtfs_test / requests_gtfs.csv
            data_reader = GTFSReader(args.gtfs_folder, requests_file_path)
        else:
            data_reader = BusDataReader(requests_file_path, vehicles_file_path)

    if g is not None:
        opt = ShuttleOptimization()
        env = Environment(opt, g)
    else:
        opt = BusOptimization()
        env = Environment(opt)

    vehicle_data_list = data_reader.get_vehicle_data()
    request_data_list = data_reader.get_request_data()

    eq = EventQueue(env)
    simulate(env, eq, request_data_list, vehicle_data_list)


if __name__ == '__main__':
    main()
