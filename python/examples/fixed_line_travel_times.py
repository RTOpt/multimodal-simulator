import logging  # Required to modify the log level

from multimodalsim.observer.environment_observer import \
    StandardEnvironmentObserver
from multimodalsim.optimization.dispatcher import FixedLineDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.splitter import MultimodalSplitter
from multimodalsim.reader.data_reader import GTFSReader
from multimodalsim.reader.travel_times_reader import MatrixTravelTimesReader
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

    vehicles = data_reader.get_vehicles(min_departure_time_interval=60)
    trips = data_reader.get_trips()

    # Generate the network from GTFS files.
    g = data_reader.get_network_graph()

    # Set to None if coordinates of the vehicles are not available.
    coordinates_file_path = "../../data/fixed_line/gtfs/coordinates" \
                            "/coordinates_5s.csv"
    coordinates = CoordinatesFromFile(coordinates_file_path)

    # Read travel times
    travel_times_file_path = \
        "../../data/fixed_line/gtfs/actual_travel_times_late.csv"
    matrix_travel_times_reader = \
        MatrixTravelTimesReader(travel_times_file_path)
    matrix_travel_times = matrix_travel_times_reader.get_matrix_travel_times()

    # Initialize the optimizer.
    splitter = MultimodalSplitter(g)
    dispatcher = FixedLineDispatcher()
    opt = Optimization(dispatcher, splitter)

    # Initialize the observer.
    environment_observer = StandardEnvironmentObserver()

    # Initialize the simulation.
    simulation = Simulation(opt, trips, vehicles,
                            environment_observer=environment_observer,
                            coordinates=coordinates,
                            travel_times=matrix_travel_times)

    # Execute the simulation.
    simulation.simulate()

    output_folder = "../../output/fixed_line_travel_times/"
    data_container = simulation.data_collectors[0].data_container
    if data_container is not None and output_folder is not None:
        if "vehicles" in data_container.observations_tables:
            data_container.save_observations_to_csv(
                "vehicles", output_folder + "vehicles_observations_df.csv")
        if "trips" in data_container.observations_tables:
            data_container.save_observations_to_csv(
                "trips", output_folder + "trips_observations_df.csv")
        if "events" in data_container.observations_tables:
            data_container.save_observations_to_csv(
                "events", output_folder + "events_observations_df.csv")
