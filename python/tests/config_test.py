import unittest

from multimodalsim.config.optimization_config import OptimizationConfig
from multimodalsim.observer.data_collector import DataContainer, \
    StandardDataCollector
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.shuttle.shuttle_hub_simple_dispatcher import \
    ShuttleHubSimpleDispatcher
from multimodalsim.reader.data_reader import ShuttleDataReader, GTFSReader
from multimodalsim.simulator.coordinates import CoordinatesOSRM
from multimodalsim.simulator.simulation import Simulation
from multimodalsim.statistics.data_analyzer import FixedLineDataAnalyzer

unittest.TestLoader.sortTestMethodsUsing = None


class ShuttleTestCase(unittest.TestCase):
    __dispatcher = None
    __vehicles = None
    __trips = None

    @classmethod
    def setUpClass(cls):
        requests_file_path = "../../data/tests/shuttle/requests.csv"
        vehicles_file_path = "../../data/tests/shuttle/vehicles.csv"

        data_reader = ShuttleDataReader(requests_file_path, vehicles_file_path,
                                        vehicles_end_time=100000)

        cls.__vehicles, cls.__routes_by_vehicle_id = data_reader.get_vehicles()
        cls.__trips = data_reader.get_trips()

        cls.__dispatcher = ShuttleHubSimpleDispatcher()
        cls.__opt = Optimization(cls.__dispatcher)

    def test_load_optimization_config_from_file(self):

        optimization_config_file_path = \
            "../../data/tests/config/ini/optimization.ini"

        opt = Optimization(self.__dispatcher,
                           config=optimization_config_file_path)

        self.assertEqual(opt._Optimization__freeze_interval, 10)
        self.assertIsInstance(opt._Optimization__config, OptimizationConfig)

    def test_load_simulation_config_from_file(self):

        simulation_config_file_path = \
            "../../data/tests/config/ini/simulation_no_recurrent_time_sync.ini"

        self.__simulation = Simulation(self.__opt, self.__trips,
                                       self.__vehicles,
                                       self.__routes_by_vehicle_id,
                                       config=simulation_config_file_path)

        self.assertIs(self.__simulation._Simulation__max_time, None)
        self.assertIs(self.__simulation._Simulation__speed, None)
        self.assertIs(self.__simulation._Simulation__time_step, None)
        self.assertIs(self.__simulation._Simulation__update_position_time_step,
                      None)

    def test_load_simulation_config_from_file_recurrent_time_sync(self):

        simulation_config_file_path = \
            "../../data/tests/config/ini/simulation_recurrent_time_sync.ini"

        self.__simulation = Simulation(self.__opt, self.__trips,
                                       self.__vehicles,
                                       self.__routes_by_vehicle_id,
                                       config=simulation_config_file_path)

        self.assertIs(self.__simulation._Simulation__max_time, None)
        self.assertEqual(self.__simulation._Simulation__speed, 600)
        self.assertEqual(self.__simulation._Simulation__time_step, 3600)
        self.assertIs(self.__simulation._Simulation__update_position_time_step,
                      None)

    def test_load_simulation_config_from_file_max_time(self):

        simulation_config_file_path = \
            "../../data/tests/config/ini/simulation_max_time.ini"

        self.__simulation = Simulation(self.__opt, self.__trips,
                                       self.__vehicles,
                                       self.__routes_by_vehicle_id,
                                       config=simulation_config_file_path)

        self.assertEqual(self.__simulation._Simulation__max_time, 100000)
        self.assertIs(self.__simulation._Simulation__speed, None)
        self.assertIs(self.__simulation._Simulation__time_step, None)
        self.assertIs(self.__simulation._Simulation__update_position_time_step,
                      None)

    def test_load_coordinates_osrm_config_from_file(self):

        coordinates_osrm_config_file_path = \
            "../../data/tests/config/ini/coordinates_osrm.ini"

        coordinates = CoordinatesOSRM(config=coordinates_osrm_config_file_path)

        self.assertEqual(coordinates._CoordinatesOSRM__osrm_url,
                         "test")

    def test_load_gtfs_data_reader_config_from_tile(self):
        gtfs_folder_path = "../../data/tests/fixed_line_multimodal/gtfs/"
        requests_file_path = "../../data/tests/fixed_line_multimodal/requests_gtfs.csv"

        gtfs_reader_config_file_path = \
            "../../data/tests/config/ini/gtfs_data_reader.ini"

        data_reader = GTFSReader(gtfs_folder_path, requests_file_path,
                                 config=gtfs_reader_config_file_path)

        trips_columns = data_reader._GTFSReader__trips_columns
        self.assertIsInstance(trips_columns, dict)
        self.assertEqual(trips_columns["id"], 10)
        self.assertEqual(trips_columns["origin"], 11)
        self.assertEqual(trips_columns["destination"], 12)
        self.assertEqual(trips_columns["nb_passengers"], 13)
        self.assertEqual(trips_columns["release_time"], 14)
        self.assertEqual(trips_columns["ready_time"], 15)
        self.assertEqual(trips_columns["due_time"], 16)
        self.assertEqual(trips_columns["legs"], 17)

    def test_load_data_collector_config_from_tile(self):
        data_collector_config_file_path = \
            "../../data/tests/config/ini/data_collector.ini"

        data_container = DataContainer()
        StandardDataCollector(data_container,
                              config=data_collector_config_file_path)

        vehicles_columns = data_container.get_columns("vehicles")
        trips_columns = data_container.get_columns("trips")
        events_columns = data_container.get_columns("events")

        self.assertEqual(vehicles_columns["time"], "Temps")
        self.assertEqual(trips_columns["name"], "Nom")
        self.assertEqual(events_columns["priority"], "Priorite")

    def test_load_data_analyzer_config_from_tile(self):
        data_analyzer_config_file_path = \
            "../../data/tests/config/ini/data_analyzer.ini"

        data_container = DataContainer()
        data_analyzer = FixedLineDataAnalyzer(
            data_container, config=data_analyzer_config_file_path)

        ghg_e = data_analyzer._FixedLineDataAnalyzer__default_ghg_e
        self.assertEqual(ghg_e, 777)


if __name__ == '__main__':
    unittest.main()
