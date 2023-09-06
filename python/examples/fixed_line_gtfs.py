import logging  # Required to modify the log level

from multimodalsim.observer.environment_observer import \
    StandardEnvironmentObserver
from multimodalsim.optimization.dispatcher import FixedLineDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.splitter import MultimodalSplitter
from multimodalsim.reader.data_reader import GTFSReader
from multimodalsim.simulator.coordinates import CoordinatesFromFile, \
    CoordinatesOSRM
from multimodalsim.simulator.simulation import Simulation

logger = logging.getLogger(__name__)


if __name__ == '__main__':
    # To modify the log level (at INFO, by default)
    logging.getLogger().setLevel(logging.DEBUG)

    # Read input data from files with a DataReader. The DataReader returns a
    # list of Vehicle objects and a list of Trip objects.
    gtfs_folder_path = "../../data/fixed_line/gtfs/gtfs/"
    requests_file_path = "../../data/fixed_line/gtfs/requests_gtfs_v1.csv"
    data_reader = GTFSReader(gtfs_folder_path, requests_file_path)

    # Set to None if coordinates of the vehicles are not available.
    coordinates_file_path = "../../data/fixed_line/gtfs/coordinates" \
                            "/coordinates_30s.csv"
    coordinates = CoordinatesFromFile(coordinates_file_path)

    vehicles = data_reader.get_vehicles()
    trips = data_reader.get_trips()

    # Generate the network from GTFS files.
    g = data_reader.get_network_graph()

    # Initialize the optimizer.
    splitter = MultimodalSplitter(g)
    dispatcher = FixedLineDispatcher()
    opt = Optimization(dispatcher, splitter)

    # Initialize the observer.
    environment_observer = StandardEnvironmentObserver()

    # Initialize the simulation.
    simulation = Simulation(opt, trips, vehicles,
                            environment_observer=environment_observer,
                            coordinates=coordinates)

    # Execute the simulation.
    simulation.simulate()
