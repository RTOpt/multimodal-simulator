"""
constants are found here
"""

import os
from dateutil.parser import parse

##################################################################################
# Data File Path
##################################################################################
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
print(ROOT_PATH)


##################################################################################
# TAD System Config
##################################################################################

# fleet config
FLEET_SIZE = [30]
VEHICLE_CAPACITY = [3,5]

# request_config
MAXIMUM_REQUEST_PASSENGER = 5


##################################################################################
# Simulation Config
##################################################################################
SIMULATION_START_TIME = "2021-03-01 8:30:00"  # peak hour: 8:00:00 - 10:00:00
SIMULATION_DURATION_MIN = 30

