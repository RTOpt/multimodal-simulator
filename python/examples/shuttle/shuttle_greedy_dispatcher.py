import logging  # Required to modify the log level

from multimodalsim.observer.environment_observer import \
    StandardEnvironmentObserver
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.reader.data_reader import ShuttleDataReader
from multimodalsim.optimization.shuttle.shuttle_greedy_dispatcher import \
    ShuttleGreedyDispatcher
from multimodalsim.simulator.simulation import Simulation

if __name__ == '__main__':

    # To modify the log level (at INFO, by default)
    logging.getLogger().setLevel(logging.DEBUG)

    # Read input data from files
    requests_file_path = "../../../data/shuttle/test3_shuttle/requests_sncf.csv"
    vehicles_file_path = "../../../data/shuttle/test3_shuttle/vehicles.csv"
    graph_file_path = "../../../data/shuttle/test3_shuttle/graph.json"

    data_reader = ShuttleDataReader(requests_file_path, vehicles_file_path,
                                    graph_file_path, vehicles_end_time=100000)

    vehicles, routes_by_vehicle_id = data_reader.get_vehicles()
    trips = data_reader.get_trips()
    network_graph = data_reader.get_json_graph()

    # Initialize the optimizer.
    dispatcher = ShuttleGreedyDispatcher(network_graph)

    # OneLegSplitter is used by default
    opt = Optimization(dispatcher)

    # Initialize the observer.
    environment_observer = StandardEnvironmentObserver()

    # Initialize the simulation.
    simulation = Simulation(opt, trips, vehicles, routes_by_vehicle_id,
                            network=network_graph,
                            environment_observer=environment_observer)

    # Execute the simulation.
    simulation.simulate()
