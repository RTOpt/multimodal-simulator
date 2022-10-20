import argparse
import logging

from logger.formatter import ColoredFormatter
from multimodalsim.visualizer.visualizer import ConsoleVisualizer
from optimization.dispatcher import ShuttleGreedyDispatcher, \
    FixedLineDispatcher
from optimization.optimization import Optimization
from optimization.splitter import OneLegSplitter, MultimodalSplitter
from reader.data_reader import BusDataReader, GTFSReader, ShuttleDataReader
from simulator.network import create_graph
from simulator.simulation import Simulation

logger = logging.getLogger(__name__)


def add_arguments(parser):
    parser.add_argument("-r", "--requests", help="path to the file "
                                                 "containing the requests")
    parser.add_argument("-v", "--vehicles", help="path to the file "
                                                 "containing the vehicles")
    parser.add_argument("-n", "--nodes", help="path to the file containing "
                                              "the nodes (with 'shuttle' "
                                              "only)")
    parser.add_argument("type", help="type of optimization ('shuttle' or "
                                     "'fixed')")
    parser.add_argument("--log-level",
                        help="the log level (by default: DEBUG)",
                        default="DEBUG")
    parser.add_argument("--gtfs", help="input files are in the GTFS format",
                        action="store_true")
    parser.add_argument("--gtfs-folder", help="the path to the folder "
                                              "containing the files in the "
                                              "GTFS format")
    parser.add_argument("--multimodal", help="fixed line optimization is "
                                             "multimodal", action="store_true")


def check_arguments(args):
    if args.type != "shuttle" and args.type != "fixed":
        raise ValueError("The type of optimization must be either 'shuttle' "
                         "or 'fixed'!")
    elif args.type == "shuttle" and args.nodes is None:
        raise ValueError("Shuttle optimization requires the path to the "
                         "nodes (--nodes)!")
    elif (args.type == "shuttle" or args.type == "fixed") \
            and args.requests is None:
        raise ValueError("Shuttle optimization requires the path to the "
                         "requests (--requests)!")
    elif (args.type == "shuttle" or args.type == "fixed") and (args.vehicles is
                                                               None and not
                                                               args.gtfs):
        raise ValueError("the path to the vehicles (--vehicles) is required!")

    numeric_log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_log_level, int):
        raise ValueError("The argument --log-level is invalid: {}"
                         .format(args.log_level))


def configure_logger(log_level=logging.INFO, log_filename=None):
    logger.info("log_level={}".format(log_level))
    logging.basicConfig(filename=log_filename, level=log_level)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Replace default handler with custom handler
    console_stream_handler = logging.StreamHandler()
    console_stream_handler.setFormatter(ColoredFormatter(fmt="%(message)s"))
    # Add fmt="%(message)s" as argument of ColoredFormatter if you only want
    # to see the output (without time and line numbers).

    root_logger = logging.getLogger()

    # Remove default handler
    for h in root_logger.handlers:
        root_logger.removeHandler(h)

    # Add custom handler
    root_logger.addHandler(console_stream_handler)

    # Add file handler
    if log_filename is not None:
        root_logger.addHandler(logging.FileHandler(log_filename, mode='w'))

    root_logger.info("log_level={}".format(log_level))


def main():
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()

    check_arguments(args)

    # log_filename = "log.txt"
    log_filename = None
    configure_logger(log_level=args.log_level, log_filename=log_filename)

    requests_file_path = args.requests
    vehicles_file_path = args.vehicles

    g = None

    if args.type == "shuttle":
        # Parameters example: shuttle -r
        # ../../data/shuttle/test0_shuttle/requests.csv -v
        # ../../data/shuttle/test0_shuttle/vehicles.csv -n
        # ../../data/shuttle/test0_shuttle/nodes.csv
        logger.info("Shuttle")

        nodes_file_path = args.nodes

        data_reader = ShuttleDataReader(requests_file_path, vehicles_file_path,
                                        nodes_file_path)
        nodes = data_reader.get_nodes()
        g = create_graph(nodes)

        splitter = OneLegSplitter()
        dispatcher = ShuttleGreedyDispatcher(g)

    elif args.type == "fixed":
        logger.info("FixedLine")

        if args.multimodal:
            splitter = MultimodalSplitter()
        else:
            splitter = OneLegSplitter()
        dispatcher = FixedLineDispatcher()

        if args.gtfs:
            # Parameters example: fixed --gtfs --gtfs-folder
            # ../../data/fixed_line/gtfs/gtfs/ -r
            # ../../data/fixed_line/gtfs/requests_gtfs_v1.csv --multimodal
            # --log-level DEBUG
            data_reader = GTFSReader(args.gtfs_folder, requests_file_path)
        else:
            # Parameters example: fixed -r
            # ../../data/fixed_line/bus/requests_v1.csv -v
            # ../../data/fixed_line/bus/vehicles_v1.csv --multimodal
            # --log-level DEBUG
            data_reader = BusDataReader(requests_file_path, vehicles_file_path)
    else:
        raise ValueError("The type of optimization must be either 'shuttle' "
                         "or 'fixed'!")

    opt = Optimization(dispatcher, splitter)

    vehicles = data_reader.get_vehicles()
    trips = data_reader.get_trips()

    visualizer = ConsoleVisualizer()

    simulation = Simulation(opt, trips, vehicles, network=g,
                            visualizer=visualizer)
    simulation.simulate()

    logger.debug("DataContainer:")
    data_container = simulation.data_collector.data_container

    data_container.save_observations_to_csv("vehicles",
                                            "vehicles_observations_df.csv")
    data_container.save_observations_to_csv("trips",
                                            "trips_observations_df.csv")
    data_container.save_observations_to_csv("events",
                                            "events_observations_df.csv")


if __name__ == '__main__':
    logger.info("MAIN")
    main()
