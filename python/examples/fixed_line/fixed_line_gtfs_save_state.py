import logging  # Required to modify the log level
import random

from multimodalsim.observer.environment_observer import \
    StandardEnvironmentObserver
from multimodalsim.optimization.fixed_line.fixed_line_dispatcher import \
    FixedLineDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.splitter import OneLegSplitter
from multimodalsim.reader.data_reader import GTFSReader
from multimodalsim.simulator.coordinates import CoordinatesFromFile
from multimodalsim.simulator.simulation import Simulation
from multimodalsim.simulator.state_storage import StateStoragePickle

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # To modify the log level (at INFO, by default)
    logging.getLogger().setLevel(logging.INFO)

    # Read input data from files with a DataReader. The DataReader returns a
    # list of Vehicle objects and a list of Trip objects.
    gtfs_folder_path = "../../../data/fixed_line/gtfs/gtfs/"
    requests_file_path = "../../../data/fixed_line/gtfs/requests_gtfs_v2.csv"
    data_reader = GTFSReader(gtfs_folder_path, requests_file_path)

    # Set to None if coordinates of the vehicles are not available.
    coordinates_file_path = \
        "../../../data/fixed_line/gtfs/coordinates/coordinates_30s.csv"
    coordinates = CoordinatesFromFile(coordinates_file_path)

    # To estimate the coordinates from an OSRM server, use the following:
    # coordinates = CoordinatesOSRM()

    vehicles, routes_by_vehicle_id = data_reader.get_vehicles()
    trips = data_reader.get_trips()

    # Time interval during which the current state of the environment is frozen
    # at each optimization. It prevents the optimization from making decisions
    # that would have an impact too near in the future.
    freeze_interval = 5
    # Initialize the optimizer.
    splitter = OneLegSplitter()
    dispatcher = FixedLineDispatcher()
    opt = Optimization(dispatcher, splitter, freeze_interval=freeze_interval)

    # Initialize the observer.
    environment_observer = StandardEnvironmentObserver()

    random.seed(1)

    # Initialize the simulation.
    simulation = Simulation(opt, trips, vehicles, routes_by_vehicle_id,
                            environment_observer=environment_observer,
                            coordinates=coordinates,
                            state_storage=StateStoragePickle(
                                "../../../data/saved_simulations/"))

    # Execute the simulation.
    simulation.simulate()

    state_storage = StateStoragePickle("../../../data/saved_simulations/",
                                       save=False)

    # Pickle files can be converted to a json file.
    state_storage.convert_pickle_to_json("state.pkl")

    # The state can be loaded from both a json file and a pickle file.
    state_storage.load_state("state.json")

    environment_observer2 = StandardEnvironmentObserver()

    coordinates2 = CoordinatesFromFile(coordinates_file_path)

    loaded_simulation = Simulation(opt, [], [], {},
                                   environment_observer=environment_observer2,
                                   coordinates=coordinates2,
                                   state_storage=state_storage)

    # Execute the simulation.
    loaded_simulation.simulate()
