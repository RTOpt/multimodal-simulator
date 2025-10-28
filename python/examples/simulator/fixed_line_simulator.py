import logging

from multimodalsim.simulator.simulator import Simulator

logger = logging.getLogger(__name__)


if __name__ == '__main__':
    # To modify the log level (at INFO, by default)
    logging.getLogger().setLevel(logging.INFO)

    simulation_directory = "../../../data/stl/instance_07/"

    simulator = Simulator(simulation_directory)

    simulator.simulate()
