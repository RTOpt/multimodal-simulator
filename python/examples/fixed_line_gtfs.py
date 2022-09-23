from multimodalsim.optimization.dispatcher import FixedLineDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.splitter import MultimodalSplitter
from multimodalsim.reader.data_reader import GTFSReader
from multimodalsim.simulator.simulation import Simulation
from multimodalsim.visualizer.visualizer import ConsoleVisualizer

if __name__ == '__main__':

    # Read input data from files with a DataReader. The DataReader returns a list of Vehicle objects and a list of Trip
    # objects.
    gtfs_folder_path = "../../data/fixed_line/gtfs/gtfs/"
    requests_file_path = "../../data/fixed_line/gtfs/requests_gtfs_v1.csv"

    data_reader = GTFSReader(gtfs_folder_path, requests_file_path)

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