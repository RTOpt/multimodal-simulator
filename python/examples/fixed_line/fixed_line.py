import logging  # Required to modify the log level

from multimodalsim.observer.environment_observer import \
    StandardEnvironmentObserver
from multimodalsim.optimization.fixed_line.fixed_line_dispatcher import \
    FixedLineDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.splitter import MultimodalSplitter, \
    OneLegSplitter
from multimodalsim.reader.data_reader import BusDataReader
from multimodalsim.simulator.simulation import Simulation


if __name__ == '__main__':
    # To modify the log level (at INFO, by default)
    logging.getLogger().setLevel(logging.DEBUG)

    # Read input data from files with a DataReader. The DataReader returns a
    # list of Vehicle objects and a list of Trip objects.
    requests_file_path = "../../../data/fixed_line/bus/requests_v2.csv"
    vehicles_file_path = "../../../data/fixed_line/bus/vehicles_v2.csv"

    data_reader = BusDataReader(requests_file_path, vehicles_file_path)

    vehicles, routes_by_vehicle_id = data_reader.get_vehicles()
    trips = data_reader.get_trips()

    # Initialize the optimizer.
    splitter = OneLegSplitter()
    dispatcher = FixedLineDispatcher()
    opt = Optimization(dispatcher, splitter)

    # Initialize the observer.
    environment_observer = StandardEnvironmentObserver()

    # Initialize the simulation.
    simulation = Simulation(opt, trips, vehicles, routes_by_vehicle_id,
                            environment_observer=environment_observer)

    # Execute the simulation.
    simulation.simulate()
