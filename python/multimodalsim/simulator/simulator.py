import json
import logging
import os
from typing import Optional, Any

from networkx.readwrite import json_graph

from multimodalsim.observer.data_collector import DataContainer, \
    StandardDataCollector, DataCollector
from multimodalsim.observer.environment_observer import EnvironmentObserver
from multimodalsim.observer.visualizer import ConsoleVisualizer, Visualizer
from multimodalsim.optimization.fixed_line.fixed_line_dispatcher import \
    FixedLineDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.shuttle.shuttle_greedy_dispatcher import \
    ShuttleGreedyDispatcher
from multimodalsim.optimization.splitter import MultimodalSplitter
from multimodalsim.reader.data_reader import GTFSReader, ShuttleDataReader
from multimodalsim.coordinates.coordinates import Coordinates
from multimodalsim.coordinates.coordinates_osrm import CoordinatesOSRM
from multimodalsim.coordinates.coordinates_from_polyline_file import \
    CoordinatesFromPolylineFile
from multimodalsim.simulator.request import Trip
from multimodalsim.simulator.simulation import Simulation
from multimodalsim.simulator.vehicle import Vehicle, Route
from multimodalsim.statistics.data_analyzer import FixedLineDataAnalyzer

logger = logging.getLogger(__name__)


class Simulator:
    def __init__(self, simulation_directory: str,
                 visualizers: Optional[Visualizer | list[Visualizer]] = None,
                 data_collectors: Optional[
                     DataCollector | list[DataCollector]] = None,
                 vehicles: Optional[list[Vehicle]] = None,
                 routes_by_vehicle_id: dict[str | int, Route] = None,
                 trips: Optional[list[Trip]] = None,
                 network: Optional[Any] = None,
                 optimization: Optional[Optimization] = None,
                 coordinates: Optional[Coordinates] = None,
                 parameters_file_name: Optional[str] = None):

        self.__simulation = None
        self.__parameters = None

        self.__simulation_directory = simulation_directory
        self.__visualizers = visualizers
        self.__data_collectors = data_collectors
        self.__vehicles = vehicles
        self.__routes_by_vehicle_id = routes_by_vehicle_id
        self.__trips = trips
        self.__network = network
        self.__optimization = optimization
        self.__coordinates = coordinates
        self.__parameters_file_name = "parameters.json" \
            if parameters_file_name is None else parameters_file_name

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

    def __init_environment_observer(self):
        if self.__visualizers is None or self.__data_collectors is None:
            data_container = DataContainer()

            if self.__data_collectors is None:
                self.__data_collectors = StandardDataCollector(data_container)

            if self.__visualizers is None:
                data_analyzer = FixedLineDataAnalyzer(data_container)
                self.__visualizers = ConsoleVisualizer(
                    data_analyzer=data_analyzer)

        self.__environment_observer = EnvironmentObserver(
            data_collectors=self.__data_collectors,
            visualizers=self.__visualizers)

    def __init_simulation_from_directory(self, simulation_directory):
        directory_content_list = os.listdir(simulation_directory)

        if self.__parameters_file_name in directory_content_list:
            self.__read_parameters_file()

        self.__select_simulation_type()

    def __read_parameters_file(self):
        parameters_file_path = self.__simulation_directory \
                               + self.__parameters_file_name
        with open(parameters_file_path) as f:
            self.__parameters = json.load(f)

    def __select_simulation_type(self):
        if self.__parameters is not None:
            simulation_type = self.__parameters["type"]
        elif "gtfs" in os.listdir(self.__simulation_directory):
            simulation_type = "FIXED_LINE"
        else:
            raise ValueError(
                "The simulation directory must contain the file '{}' and/or a "
                "'gtfs/' subdirectory.".format(self.__parameters_file_name))

        if simulation_type == "FIXED_LINE":
            simulation_initializer = SimulationInitializerFixedLine(
                self.__simulation_directory, self.__environment_observer,
                self.__parameters, self.__visualizers, self.__data_collectors,
                self.__vehicles, self.__trips, self.__network,
                self.__optimization, self.__coordinates)
        elif simulation_type == "SHUTTLE":
            simulation_initializer = SimulationInitializerShuttle(
                self.__simulation_directory, self.__environment_observer,
                self.__parameters, self.__visualizers, self.__data_collectors,
                self.__vehicles, self.__trips, self.__network,
                self.__optimization, self.__coordinates)
        else:
            raise ValueError("Simulation type is unknown!")

        self.__simulation = simulation_initializer.init_simulation()


class SimulationInitializer:

    def __init__(self, simulation_directory: str,
                 environment_observer: EnvironmentObserver,
                 parameters: Optional[dict[Any]] = None,
                 visualizers: Optional[Visualizer | list[Visualizer]] = None,
                 data_collectors: Optional[
                     DataCollector | list[DataCollector]] = None,
                 vehicles: Optional[list[Vehicle]] = None,
                 routes_by_vehicle_id: dict[str | int, Route] = None,
                 trips: Optional[list[Trip]] = None,
                 network: Optional[Any] = None,
                 optimization: Optional[Optimization] = None,
                 coordinates: Optional[Coordinates] = None):

        self._simulation_directory = simulation_directory
        self._parameters = parameters
        self._environment_observer = environment_observer

        self._visualizers = visualizers
        self._data_collectors = data_collectors
        self._vehicles = vehicles
        self._routes_by_vehicle_id = routes_by_vehicle_id
        self._trips = trips
        self._network = network
        self._optimization = optimization
        self._coordinates = coordinates

        self._simulation = None

        self._init_default_parameters()

    def init_simulation(self):

        if self._vehicles is None or self._trips is None \
                or self._network is None:
            self._read_input()

        if self._optimization is None:
            self._init_optimization()

        if self._coordinates is None:
            self._init_coordinates()

        self._simulation = Simulation(
            self._optimization, self._trips, self._vehicles,
            self._routes_by_vehicle_id,
            environment_observer=self._environment_observer,
            coordinates=self._coordinates)

        return self._simulation

    def _read_input(self):
        raise NotImplementedError('_read_input of {} not implemented'
                                  .format(self.__class__.__name__))

    def _init_optimization(self):
        raise NotImplementedError('_init_optimization of {} not implemented'
                                  .format(self.__class__.__name__))

    def _init_coordinates(self):
        raise NotImplementedError('_init_coordinates of {} not implemented'
                                  .format(self.__class__.__name__))

    def _init_default_parameters(self):

        if self._parameters is not None and "input_files" in self._parameters:
            self._input_files = self._parameters["input_files"]
        else:
            self._input_files = None

        if self._input_files is not None and "requests" in self._input_files:
            self._requests_file = self._input_files["requests"]
        else:
            self._requests_file = "requests.csv"

        if self._input_files is not None and "vehicles" in self._input_files:
            self._vehicles_file = self._input_files["vehicles"]
        else:
            self._vehicles_file = "vehicles.csv"


class SimulationInitializerFixedLine(SimulationInitializer):

    def __init__(self, simulation_directory: str,
                 environment_observer: EnvironmentObserver,
                 parameters: Optional[dict[Any]] = None,
                 visualizers: Optional[Visualizer | list[Visualizer]] = None,
                 data_collectors: Optional[
                     DataCollector | list[DataCollector]] = None,
                 vehicles: Optional[list[Vehicle]] = None,
                 routes_by_vehicle_id: dict[str | int, Route] = None,
                 trips: Optional[list[Trip]] = None,
                 network: Optional[Any] = None,
                 optimization: Optional[Optimization] = None,
                 coordinates: Optional[Coordinates] = None):
        super().__init__(simulation_directory, environment_observer,
                         parameters, visualizers, data_collectors,
                         vehicles, routes_by_vehicle_id, trips, network,
                         optimization, coordinates)

    def _init_default_parameters(self):
        super()._init_default_parameters()

        if self._input_files is not None and "gtfs" in self._input_files:
            self._gtfs_folder = self._input_files["gtfs"]
        else:
            self._gtfs_folder = "gtfs/"

        if self._input_files is not None and "graph" in self._input_files:
            self._graph_file = self._input_files["graph"]
        else:
            self._graph_file = "bus_network_graph.txt"

    def _read_input(self):
        gtfs_directory_directory = self._simulation_directory \
                                   + self._gtfs_folder
        requests_file_path = self._simulation_directory + self._requests_file

        # Read input data from files.
        data_reader = GTFSReader(gtfs_directory_directory, requests_file_path)
        self._vehicles, self._routes_by_vehicle_id = \
            data_reader.get_vehicles()
        self._trips = data_reader.get_trips()

        # Read the network graph.
        graph_path = self._simulation_directory + self._graph_file
        with open(graph_path, 'r') as f:
            graph_data = json.load(f)
            self._network = json_graph.node_link_graph(graph_data)

    def _init_optimization(self):
        freeze_interval = 5
        splitter = MultimodalSplitter(self._network,
                                      freeze_interval=freeze_interval)
        dispatcher = FixedLineDispatcher()
        self._optimization = Optimization(dispatcher, splitter,
                                          freeze_interval=freeze_interval)

    def _init_coordinates(self):
        self._coordinates = CoordinatesOSRM()


class SimulationInitializerShuttle(SimulationInitializer):

    def __init__(self, simulation_directory: str,
                 environment_observer: EnvironmentObserver,
                 parameters: Optional[dict[Any]] = None,
                 visualizers: Optional[Visualizer | list[Visualizer]] = None,
                 data_collectors: Optional[
                     DataCollector | list[DataCollector]] = None,
                 vehicles: Optional[list[Vehicle]] = None,
                 routes_by_vehicle_id: dict[str | int, Route] = None,
                 trips: Optional[list[Trip]] = None,
                 network: Optional[Any] = None,
                 optimization: Optional[Optimization] = None,
                 coordinates: Optional[Coordinates] = None):

        super().__init__(simulation_directory, environment_observer,
                         parameters, visualizers, data_collectors,
                         vehicles, routes_by_vehicle_id, trips, network,
                         optimization, coordinates)

    def _init_default_parameters(self):
        super()._init_default_parameters()

        if self._input_files is not None and "polylines" in self._input_files:
            self._polylines_file = self._input_files["polylines"]
        else:
            self._polylines_file = "polylines.json"

        if self._input_files is not None and "graph" in self._input_files:
            self._graph_file = self._input_files["graph"]
        else:
            self._graph_file = "graph.json"

    def _read_input(self):

        requests_file_path = self._simulation_directory + self._requests_file
        vehicles_file_path = self._simulation_directory + self._vehicles_file
        graph_file_path = self._simulation_directory + self._graph_file

        if "vehicles_end_time" in self._parameters:
            vehicles_end_time = self._parameters["vehicles_end_time"]
        else:
            vehicles_end_time = None

        # Read input data from files.
        data_reader = ShuttleDataReader(requests_file_path,
                                        vehicles_file_path,
                                        graph_file_path,
                                        vehicles_end_time)
        self._vehicles, self._routes_by_vehicle_id = \
            data_reader.get_vehicles()
        self._trips = data_reader.get_trips()

        # Read the network graph.
        with open(graph_file_path, 'r') as f:
            graph_data = json.load(f)
            self._network = json_graph.node_link_graph(graph_data)

    def _init_optimization(self):
        freeze_interval = self._parameters["freeze_interval"]
        dispatcher = ShuttleGreedyDispatcher(
            network=self._network,
            vehicles=self._vehicles,
            time_window=self._parameters["time_window"]
        )
        self._optimization = Optimization(dispatcher,
                                          freeze_interval=freeze_interval)

    def _init_coordinates(self):
        input_files = self._parameters["input_files"]

        if "polylines" in input_files:
            polylines_file_path = self._simulation_directory \
                                  + input_files["polylines"]
        else:
            polylines_file_path = None

        if polylines_file_path is None:
            self._coordinates = CoordinatesOSRM()
        else:
            self._coordinates = \
                CoordinatesFromPolylineFile(polylines_file_path)
