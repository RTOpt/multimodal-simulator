import logging  # Required to modify the log level

from multimodalsim.observer.environment_observer import \
    StandardEnvironmentObserver
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.shuttle.shuttle_hub_simple_dispatcher import \
    ShuttleHubSimpleDispatcher
from multimodalsim.reader.data_reader import ShuttleDataReader
from multimodalsim.simulator.simulation import Simulation

if __name__ == '__main__':

    # To modify the log level (at INFO, by default)
    logging.getLogger().setLevel(logging.DEBUG)

    # Read input data from files
    requests_file_path = "../../../data/shuttle/simple_dispatcher/requests.csv"
    vehicles_file_path = "../../../data/shuttle/simple_dispatcher/vehicles.csv"

    data_reader = ShuttleDataReader(requests_file_path, vehicles_file_path,
                                    vehicles_end_time=100000)

    # Read the vehicles from a file.
    vehicles, routes_by_vehicle_id = data_reader.get_vehicles()
    trips = data_reader.get_trips()

    # Initialize the optimizer.
    dispatcher = ShuttleHubSimpleDispatcher()

    # OneLegSplitter is used by default
    opt = Optimization(dispatcher)

    # Initialize the observer.
    environment_observer = StandardEnvironmentObserver()

    # Initialize the simulation.
    simulation = Simulation(opt, trips, vehicles, routes_by_vehicle_id,
                            environment_observer=environment_observer)

    # Execute the simulation.
    simulation.simulate()
