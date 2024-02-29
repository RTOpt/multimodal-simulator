from multimodalsim.optimization.dispatcher import ShuttleGreedyDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.splitter import OneLegSplitter
from multimodalsim.reader.data_reader import ShuttleDataReader, os
from multimodalsim.simulator.network import create_graph
from multimodalsim.simulator.simulation import Simulation
from multimodalsim.visualizer.visualizer import ConsoleVisualizer

if __name__ == '__main__':

    # Read input data from files
    requests_file_path =  os.path.join("data","shuttle","test0_shuttle","requests.csv")
    vehicles_file_path = os.path.join("data","shuttle","test0_shuttle","vehicles.csv")
    nodes_file_path = os.path.join("data","shuttle","test0_shuttle","nodes.csv")

    data_reader = ShuttleDataReader(requests_file_path, vehicles_file_path, nodes_file_path)

    vehicles = data_reader.get_vehicles()
    trips = data_reader.get_trips()

    nodes = data_reader.get_nodes()
    g = create_graph(nodes)

    # Initialize the optimizer.
    splitter = OneLegSplitter()
    dispatcher = ShuttleGreedyDispatcher(g)
    opt = Optimization(dispatcher, splitter)

    # Initialize the visualizer.
    visualizer = ConsoleVisualizer()

    # Initialize the simulation.
    simulation = Simulation(opt, trips, vehicles, network=g, visualizer=visualizer)

    # Execute the simulation.
    simulation.simulate()

