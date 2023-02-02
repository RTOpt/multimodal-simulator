import logging  # Required to modify the log level

from multimodalsim.observer.environment_observer import \
    StandardEnvironmentObserver
from multimodalsim.optimization.dispatcher import ShuttleGreedyDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.reader.data_reader import ShuttleDataReader
from multimodalsim.simulator.network import create_graph
from multimodalsim.simulator.simulation import Simulation
from multimodalsim.observer.visualizer import ConsoleVisualizer

if __name__ == '__main__':

    # To modify the log level (at INFO, by default)
    logging.getLogger().setLevel(logging.DEBUG)

    # Read input data from files
    requests_file_path = "../../data/shuttle/test3_shuttle/requests_sncf_test0.csv"
    vehicles_file_path = "../../data/shuttle/test3_shuttle/vehicles.csv"
    nodes_file_path = "../../data/shuttle/test3_shuttle/nodes.csv"

    data_reader = ShuttleDataReader(requests_file_path, vehicles_file_path,
                                    nodes_file_path)

    vehicles = data_reader.get_vehicles()
    trips = data_reader.get_trips()

    nodes = data_reader.get_nodes()
    g = create_graph(nodes)

    # Initialize the optimizer.
    dispatcher = ShuttleGreedyDispatcher(g)

    # OneLegSplitter is used by default
    opt = Optimization(dispatcher)

    # Initialize the observer.
    environment_observer = StandardEnvironmentObserver()

    # Initialize the simulation.
    simulation = Simulation(opt, trips, vehicles, network=g,
                            environment_observer=environment_observer)

    # Execute the simulation.
    simulation.simulate()
