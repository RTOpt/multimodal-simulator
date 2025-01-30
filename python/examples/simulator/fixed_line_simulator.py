import threading
import logging
import time

from multimodalsim.simulator.simulator import Simulator

logger = logging.getLogger(__name__)


if __name__ == '__main__':

    simulation_directory = "../../../data/stl/instance_10/"

    simulator = Simulator(simulation_directory)

    simulation_thread = threading.Thread(target=simulator.simulate,
                                         name="simulation_thread")

    simulation_thread.start()

    time.sleep(2)

    simulator.pause()

    time.sleep(5)

    simulator.resume()

    time.sleep(2)

    simulator.pause()

    time.sleep(5)

    simulator.resume()

    time.sleep(5)

    simulator.stop()
