import unittest

from multimodalsim.optimization.fixed_line.fixed_line_dispatcher import \
    FixedLineDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.shuttle.shuttle_hub_simple_dispatcher import \
    ShuttleHubSimpleDispatcher
from multimodalsim.optimization.splitter import OneLegSplitter
from multimodalsim.reader.data_reader import GTFSReader, ShuttleDataReader
from multimodalsim.simulator.simulation import Simulation
from multimodalsim.state_machine.status import PassengerStatus, VehicleStatus

unittest.TestLoader.sortTestMethodsUsing = None


class ShuttleTestCase(unittest.TestCase):
    __vehicles = None
    __trips = None

    @classmethod
    def setUpClass(cls):
        requests_file_path = "../../data/tests/shuttle/requests.csv"
        vehicles_file_path = "../../data/tests/shuttle/vehicles.csv"

        data_reader = ShuttleDataReader(requests_file_path, vehicles_file_path,
                                        vehicles_end_time=100000)

        cls.__vehicles, routes_by_vehicle_id = data_reader.get_vehicles()
        cls.__trips = data_reader.get_trips()

        dispatcher = ShuttleHubSimpleDispatcher()
        opt = Optimization(dispatcher)

        cls.__simulation = Simulation(opt, cls.__trips, cls.__vehicles,
                                      routes_by_vehicle_id)

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
