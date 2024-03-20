import unittest

from multimodalsim.optimization.fixed_line.fixed_line_dispatcher import \
    FixedLineDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.splitter import MultimodalSplitter
from multimodalsim.reader.data_reader import GTFSReader
from multimodalsim.reader.travel_times_reader import MatrixTravelTimesReader
from multimodalsim.simulator.simulation import Simulation
from multimodalsim.state_machine.status import PassengerStatus, VehicleStatus

unittest.TestLoader.sortTestMethodsUsing = None


class FixedLineMultimodalTestCase(unittest.TestCase):
    __vehicles = None
    __trips = None

    @classmethod
    def setUpClass(cls):
        gtfs_folder_path = "../../data/tests/fixed_line_travel_times/gtfs/"
        requests_file_path = "../../data/tests/fixed_line_travel_times/requests_gtfs.csv"
        data_reader = GTFSReader(gtfs_folder_path, requests_file_path)

        cls.__vehicles, routes_by_vehicle_id = data_reader.get_vehicles(
            min_departure_time_interval=60)
        cls.__trips = data_reader.get_trips()

        g = data_reader.get_network_graph()

        freeze_interval = 5
        splitter = MultimodalSplitter(g, freeze_interval=freeze_interval)
        dispatcher = FixedLineDispatcher()
        opt = Optimization(dispatcher, splitter,
                           freeze_interval=freeze_interval)

        cls.__simulation = Simulation(opt, cls.__trips, cls.__vehicles,
                                      routes_by_vehicle_id)

        travel_times_file_path = \
            "../../data/tests/fixed_line_travel_times/actual_travel_times_late.csv"
        matrix_travel_times_reader = \
            MatrixTravelTimesReader(travel_times_file_path)
        matrix_travel_times = \
            matrix_travel_times_reader.get_matrix_travel_times()

        splitter = MultimodalSplitter(g)
        dispatcher = FixedLineDispatcher()
        opt = Optimization(dispatcher, splitter)

        cls.__simulation = Simulation(opt, cls.__trips, cls.__vehicles,
                                      routes_by_vehicle_id,
                                      travel_times=matrix_travel_times)

    def test_simulate(self):
        self.__simulation.simulate()

    def test_vehicle_complete_status(self):

        for vehicle in self.__vehicles:
            self.assertEqual(vehicle.status, VehicleStatus.COMPLETE)

    def test_trip_complete_status(self):

        for trip in self.__trips:
            self.assertEqual(trip.status, PassengerStatus.COMPLETE)




if __name__ == '__main__':
    unittest.main()
