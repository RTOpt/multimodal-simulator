import logging  # Required to modify the log level
from multimodalsim.__main__ import extract_simulation_output
from multimodalsim.observer.environment_observer import \
    StandardEnvironmentObserver
from multimodalsim.optimization.fixed_line.fixed_line_dispatcher import \
    FixedLineDispatcher
# from multimodalsim.optimization.fixed_line.fixed_line_synchro_dispatcher import \
#     FixedLineSynchroDispatcher
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.optimization.splitter import MultimodalSplitter
from multimodalsim.reader.data_reader import GTFSReader, os
from multimodalsim.simulator.coordinates import CoordinatesFromFile, CoordinatesOSRM
from multimodalsim.simulator.simulation import Simulation
import sys

def stl_gtfs_transfer_synchro_simulator(gtfs_folder_path=os.path.join("data","fixed_line","gtfs","gtfs-generated-small"),
                       requests_file_path=os.path.join("data","fixed_line","gtfs","gtfs-generated-small","requests.csv"),
                       coordinates_file_path=None,
                       routes_to_optimize_names = [],
                       ss = False,
                       sp = False,
                       algo = 0,
                       freeze_interval = 5,
                       output_folder_name = "gtfs-generated-small",
                       logger = logging.getLogger(__name__),
                       logging_level = logging.INFO,
                       is_from_smartcard_data = True):
    sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
    sys.path.append(r"/home/kollau/Recherche_Kolcheva/Simulator/python/examples")
    sys.path.append(os.path.abspath('../../..'))
    # To modify the log level (at INFO, by default)
    logger.setLevel(logging_level)
    logger.setlevel(logging.WARNING)
    logger.warning(" Start simulation for instance with skip_stop_is_allowed = {}, speedup_is_allowed = {}, algo = {}".format(ss, sp, algo))
    # show logging level
    logger.warning("Logging level: {}".format(logging.getLevelName(logger.getEffectiveLevel())))
    # Read input data from files with a DataReader. The DataReader returns a
    # list of Vehicle objects and a list of Trip objects.
    data_reader = GTFSReader(gtfs_folder_path, requests_file_path)

    # Set to None if coordinates of the vehicles are not available.
    if coordinates_file_path is not None:
        coordinates = CoordinatesFromFile(coordinates_file_path)
    else:
        coordinates = CoordinatesOSRM()

    vehicles, routes_by_vehicle_id = data_reader.get_vehicles()
    trips = data_reader.get_trips()

    # Get available connections saved in a .json file in the data folder
    available_connections_path = os.path.join(gtfs_folder_path, "available_connections.json")
    available_connections = data_reader.get_available_connections(available_connections_path)

    # Generate the network from GTFS files.
    g = data_reader.get_network_graph(available_connections=available_connections)

    # Initialize the optimizer.
    splitter = MultimodalSplitter(g, available_connections=available_connections,
                                  freeze_interval=freeze_interval,
                                  is_from_smartcard_data = is_from_smartcard_data)
    routes_to_optimize_names = routes_to_optimize_names if routes_to_optimize_names!=[] else list(set([vehicle.route_name for vehicle in vehicles]))
    
    # Create the output folder
    output_folder_path = os.path.join("output","fixed_line","gtfs", output_folder_name)
    output_folder_path = get_output_subfolder(output_folder_path, algo, ss, sp, routes_to_optimize_names, is_from_smartcard_data)
    print(output_folder_path)

    # Initialize the dispatcher.
    dispatcher = FixedLineDispatcher(ss = ss,
                                     sp = sp,
                                     algo = algo, 
                                     routes_to_optimize_names = routes_to_optimize_names,
                                     output_folder_path = output_folder_path)
    Data = {}
    for route_name in routes_to_optimize_names: 
        logger.info("Getting and clustering data for route %s" % route_name)
        Data[route_name] = dispatcher.get_and_cluster_data(route_name = route_name)
    dispatcher.Data = Data

    # Initialize the optimization.   
    opt = Optimization(dispatcher, splitter, freeze_interval=freeze_interval)

    # Initialize the observer.
    environment_observer = StandardEnvironmentObserver()

    # Initialize the simulation.
    simulation = Simulation(opt,
                            trips,
                            vehicles,
                            routes_by_vehicle_id,
                            environment_observer=environment_observer,
                            # coordinates=coordinates,
                            transfer_synchro = True)

    # Execute the simulation.
    simulation.simulate()

    # Extract the simulation output
    extract_simulation_output(simulation, output_folder_path)

def get_output_subfolder(output_folder_path, algo, ss, sp, routes_to_optimize_names, is_from_smartcard_data):
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)
    
    add = ''
    # Smart card usage addendum
    if is_from_smartcard_data:
        add+='SMARTCARD_' # Use historical smart card data to recreate trips for O/D pairs
    else:
        add+='SIMU_' # Simulate optimal trips for historical O/D pairs

    # Algorithm addendum
    if algo == 0:
        add += 'O' # Offline
        # Create the output folder
        output_folder_path_with_addendum = os.path.join(output_folder_path, add)
        if not os.path.exists(output_folder_path_with_addendum):
            os.makedirs(output_folder_path_with_addendum)
        return output_folder_path_with_addendum
    
    if algo == 1:
        add += 'D_' # Deterministic
    elif algo == 2:
        add += 'R_'# Regret
    elif algo == 3:
        add += 'PI_' # Perfect information

    # Tactics addendum
    if ss and sp:
        add += 'SPSS_' # Skip stop speed up, and hold
    elif ss:
        add += 'SS_' # Skip stop and hold
    elif sp:
        add += 'SP_' # Speed up and hold
    else:
        add += 'H_' # Hold

    # Routes to optimize addendum
    add += 'ROUTES_'
    if len(routes_to_optimize_names) == 1: # Optimize one route
        add +='SINGLE_'+ routes_to_optimize_names[0]
    else: # Optimize multiple routes
        add += 'MULTIPLE'
        # for route in routes_to_optimize_names:
        #     add += '_'+ route
    
    # Create the output folder
    output_folder_path_with_addendum = os.path.join(output_folder_path, add)
    if not os.path.exists(output_folder_path_with_addendum):
        print(len(output_folder_path_with_addendum))
        print(output_folder_path_with_addendum) 
        os.makedirs(output_folder_path_with_addendum)
    return output_folder_path_with_addendum