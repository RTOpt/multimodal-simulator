import logging  # Required to modify the log level

from multimodalsim.optimization.dispatcher import FixedLineDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.splitter import MultimodalSplitter
from multimodalsim.reader.data_reader import BusDataReader
from multimodalsim.simulator.simulation import Simulation
from multimodalsim.visualizer.visualizer import ConsoleVisualizer

if __name__ == '__main__':
    # To modify the log level (at INFO, by default)
    logging.getLogger().setLevel(logging.DEBUG)

    # Read input data from files with a DataReader. The DataReader returns a
    # list of Vehicle objects and a list of Trip objects.
    requests_file_path = "../../data/fixed_line/bus/requests_v2.csv"
    vehicles_file_path = "../../data/fixed_line/bus/vehicles_v2.csv"

    data_reader = BusDataReader(requests_file_path, vehicles_file_path)

    vehicles = data_reader.get_vehicles()
    trips = data_reader.get_trips()

    # Initialize the optimizer.
    splitter = MultimodalSplitter()
    dispatcher = FixedLineDispatcher()
    opt = Optimization(dispatcher, splitter)

    # Initialize the visualizer.
    visualizer = ConsoleVisualizer()

    # Initialize the simulation.
    simulation = Simulation(opt, trips, vehicles, visualizer=visualizer)

    # Execute the simulation.
    simulation.simulate()
