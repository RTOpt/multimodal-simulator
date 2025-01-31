import json
import logging
import os

from networkx.readwrite import json_graph

from multimodalsim.observer.data_collector import DataContainer, \
    StandardDataCollector
from multimodalsim.observer.environment_observer import EnvironmentObserver
from multimodalsim.observer.visualizer import ConsoleVisualizer
from multimodalsim.optimization.fixed_line.fixed_line_dispatcher import \
    FixedLineDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.splitter import MultimodalSplitter
from multimodalsim.reader.data_reader import GTFSReader
from multimodalsim.simulator.coordinates import CoordinatesOSRM
from multimodalsim.simulator.simulation import Simulation
from multimodalsim.statistics.data_analyzer import FixedLineDataAnalyzer

logger = logging.getLogger(__name__)


class Simulator:
    def __init__(self, simulation_directory, visualizers=None,
                 data_collectors=None, vehicles=None, trips=None, network=None,
                 optimization=None, coordinates=None):

        self.__simulation = None

        self.__visualizers = visualizers
        self.__data_collectors = data_collectors
        self.__vehicles = vehicles
        self.__trips = trips
        self.__network = network
        self.__optimization = optimization
        self.__coordinates = coordinates

        self.__init_environment_observer()

        self.__init_simulation_from_directory(simulation_directory)

    @property
    def simulation(self) -> Simulation:
        return self.__simulation

    def simulate(self) -> None:
        self.__simulation.simulate()

    def pause(self) -> None:
        self.__simulation.pause()

    def resume(self) -> None:
        self.__simulation.resume()

    def stop(self) -> None:
        self.__simulation.stop()

    def __init_simulation_from_directory(self, simulation_directory):
        directory_content_list = os.listdir(simulation_directory)

        if "gtfs" in directory_content_list:
            self.__init_fixed_line_simulation(simulation_directory)
        else:
            logger.warning("The directory is not a standard format.")

    def __init_environment_observer(self):
        if self.__visualizers is None or self.__data_collectors is None:
            data_container = DataContainer()

            if self.__data_collectors is None:
                self.__data_collectors = StandardDataCollector(data_container)

            if self.__visualizers is None:
                data_analyzer = FixedLineDataAnalyzer(data_container)
                self.__visualizers = ConsoleVisualizer(data_analyzer=data_analyzer)

        self.__environment_observer = EnvironmentObserver(
            data_collectors=self.__data_collectors,
            visualizers=self.__visualizers)

    def __init_fixed_line_simulation(self, simulation_directory_path):

        gtfs_directory_directory = simulation_directory_path + "gtfs/"
        requests_file_path = simulation_directory_path + "requests.csv"

        if self.__vehicles is None or self.__trips is None \
                or self.__network is None:
            self.__read_input_fixed_line(simulation_directory_path,
                                         gtfs_directory_directory,
                                         requests_file_path)

        if self.__optimization is None:
            self.__initialize_optimization_fixed_line()

        if self.__coordinates is None:
            self.__coordinates = CoordinatesOSRM()

        self.__initialize_simulation()

    def __read_input_fixed_line(self, simulation_directory_path,
                                gtfs_directory_directory,
                                requests_file_path):
        # Read input data from files.
        data_reader = GTFSReader(gtfs_directory_directory, requests_file_path)
        self.__vehicles, self.__routes_by_vehicle_id = \
            data_reader.get_vehicles()
        self.__trips = data_reader.get_trips()

        # Read the network graph.
        graph_path = simulation_directory_path + "bus_network_graph.txt"
        with open(graph_path, 'r') as f:
            graph_data = json.load(f)
            self.__network = json_graph.node_link_graph(graph_data)

    def __initialize_optimization_fixed_line(self):
        freeze_interval = 5
        splitter = MultimodalSplitter(self.__network,
                                      freeze_interval=freeze_interval)
        dispatcher = FixedLineDispatcher()
        self.__optimization = Optimization(dispatcher, splitter,
                                  freeze_interval=freeze_interval)

    def __initialize_simulation(self):
        self.__simulation = Simulation(
            self.__optimization, self.__trips, self.__vehicles,
            self.__routes_by_vehicle_id,
            environment_observer=self.__environment_observer,
            coordinates=self.__coordinates)
