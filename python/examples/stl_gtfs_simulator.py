import logging  # Required to modify the log level

from multimodalsim.observer.environment_observer import \
    StandardEnvironmentObserver
from multimodalsim.optimization.fixed_line.fixed_line_dispatcher import \
    FixedLineDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.splitter import MultimodalSplitter, \
    OneLegSplitter
from multimodalsim.reader.data_reader import GTFSReader, os
from multimodalsim.simulator.coordinates import CoordinatesFromFile, CoordinatesOSRM
from multimodalsim.simulator.simulation import Simulation

def stl_gtfs_simulator(gtfs_folder_path=os.path.join("data","fixed_line","gtfs","gtfs-generated-small"),
                       requests_file_path=os.path.join("data","fixed_line","gtfs","gtfs-generated-small","requests.csv"),
                       coordinates_file_path=None,
                       freeze_interval=5,
                       logger=logging.getLogger(__name__),
                       loggin_level=logging.INFO):
    # To modify the log level (at INFO, by default)
    logging.getLogger().setLevel(loggin_level)
    logger.info(" Start simulation for small instance")

    # Read input data from files with a DataReader. The DataReader returns a
    # list of Vehicle objects and a list of Trip objects.
    data_reader = GTFSReader(gtfs_folder_path, requests_file_path)

    # Set to None if coordinates of the vehicles are not available.
    if coordinates_file_path is not None:
        coordinates = CoordinatesFromFile(coordinates_file_path)
    else:
        coordinates = CoordinatesOSRM()

    vehicles, routes_by_vehicle_id = data_reader.get_vehicles()
    trips = data_reader.get_trips()

    # Generate the network from GTFS files.
    g = data_reader.get_network_graph()

    # Initialize the optimizer.
    splitter = MultimodalSplitter(g, freeze_interval=freeze_interval)
    dispatcher = FixedLineDispatcher()
    opt = Optimization(dispatcher, splitter, freeze_interval=freeze_interval)

    # Initialize the observer.
    environment_observer = StandardEnvironmentObserver()

    # Initialize the simulation.
    simulation = Simulation(opt,
                            trips,
                            vehicles,
                            routes_by_vehicle_id,
                            environment_observer=environment_observer,
                            coordinates=coordinates)

    # Execute the simulation.
    simulation.simulate()