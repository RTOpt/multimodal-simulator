### This file analyses passenger demand and vehicle frequency for 25-Nov-2019. 
### We will evaluate the bus frequency of all routes in route_ids for the day.
### We will also evaluate the passenger demand for all routes in route_ids for the day and the total demand.
### We will also evaluate the passenger transfer demand for all routes in route_ids for the day and the total transfer demand.
import os
import csv
import json
from ast import literal_eval
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as mcolors

base_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'fixed_line', 'gtfs', 'gtfs2019-11-27')

def get_route_dictionary():
        # Define the route_ids to plot
    route_ids_dict = {}  # route_ids for each network type.
    route_ids_dict['grid'] = list(sorted([ '17N', '17S', '151S', '151N','26O', '26E', '42E','42O', '76E','76O']))  # route_ids for a quadrant style network.
    route_ids_dict['radial'] = list(sorted([ '33N', '33S', '37N', '37S', '39N', '39S','65N', '65S','70O','70E' ]))  # route_ids for a radial style network.
    route_ids_dict['low_frequency'] = list(sorted(['22E', '22O', '52E', '52O', '60E', '60O', '66E', '66O', '74E', '74O'])) # route_ids for a low frequency only network.
    # route_ids_dict['high_frequency'] = list(sorted(['24E', '24O','26E', '26O', '42E', '42O', '76E','76O', '151N','151S','65S', '65N'])) # route_ids for a high frequency only network.
    route_ids_dict['all'] = list(sorted(['144E', '144O', '20E', '20O', '222E', '222O', '22E', '22O', '24E', '24O', '252E', '252O', '26E', '26O', '42E', '42O', '52E', '52O', '56E', '56O', '60E', '60O', '66E', '66O', '70E', '70O', '74E', '74O', '76E', '76O', '942E', '942O', '151S', '151N', '17S', '17N', '27S', '27N', '33S', '33N', '37S', '37N', '41S', '41N', '43S', '43N', '45S', '45N', '46S', '46N', '55S', '55N', '61S', '61N', '63S', '63N', '65S', '65N', '901S', '901N', '902S', '902N', '903S', '903N', '925S', '925N']))
    route_ids_dict['151'] =list(sorted(['151S', '151N','40E', '40O', '55S', '55N', '56E', '56O', '61S', '61N'])) # route_ids for line 70 and it's transferring lines.
    route_ids_dict['corridor'] = list(sorted(['17S', '17N','27S', '27N', '31S', '31N', '73S', '73N'])) # route_ids for the corridor network.
    route_ids_dict['transfer_hubs'] = route_ids_dict['all'] # route_ids for the transfer hubs network.
    return route_ids_dict

def get_trips():
    """Get all trip_ids for each route in route_ids.
    
    Returns:
        dict: route_id to trip_ids mapping."""
    trips_filepath = os.path.join(base_dir, 'trips.txt')
    route_to_trips = {}
    trips_to_route = {}
    with open(trips_filepath, 'r') as trips_file:
        trips_reader = csv.reader(trips_file, delimiter=',')
        next(trips_reader, None)
        for trips_row in trips_reader:
            route_id = trips_row[0]
            trip_id = trips_row[2]
            if route_id not in route_to_trips:
                route_to_trips[route_id] = []
            route_to_trips[route_id].append(str(trip_id))
            trips_to_route[trip_id] = route_id
    return route_to_trips, trips_to_route

def get_route_frequency(route_to_trips, tripid_to_departure_times, route_ids):
    """Get frequency for each route in route_to_trips.
    Inputs:
        route_to_trips (dict): route_id to trip_ids mapping.
        tripid_to_departure_times (dict): trip_id to departure_times mapping.
    Outputs:
        dict: route_id to frequency mapping.
    """
    start_time = 0 
    end_time = max(tripid_to_departure_times.values())  # in seconds from midnight.
    nbr_hours = (end_time - start_time) // 3600 +1 # in hours.
    route_to_frequency = {}  # route_id to frequency mapping.
    total_trips = 0  # total number of trips.
    problem_trips = 0  # number of trips with no departure time.
    total_frequency = []  # total frequency.
    total_frequency.extend([0] * nbr_hours)  # initialize total frequency.
    for route_id in route_to_trips:  # for each route.
        if route_id not in route_ids:  # if route_id not in route_ids.
            continue  # skip route.
        route_to_frequency[route_id] = []  # initialize frequency list.
        route_to_frequency[route_id].extend([0] * nbr_hours)
        for trip_id in route_to_trips[route_id]:  # for each trip in route.
            total_trips += 1  # increment total number of trips.
            if trip_id in tripid_to_departure_times:  # if trip_id in departure_times mapping.
                hour = tripid_to_departure_times[trip_id] // 3600  # get hour.
                route_to_frequency[route_id][hour] += 1  # increment frequency.
            else:  # if trip_id not in departure_times mapping.
                problem_trips += 1  # increment number of problem trips.
    print('All trips: ', total_trips)  # print total number of trips.
    print('Problem trips: ', problem_trips)  # print number of problem trips.
    return route_to_frequency, nbr_hours

def frequency_to_headway(frequency):
    """Convert frequency (buses per hour) to headway (minutes between buses)."""
    if frequency <= 0:
        return None  # Handle invalid input
    return 60 / frequency

def plot_route_frequency(route_to_frequency, nbr_hours, color_dict, network_style):
    """Plot frequency for each route in route_to_frequency."""
    #set plot size
    plt.figure(figsize=(12, 8))  # set plot size.
    route_ids_to_remove = []  # route_ids to remove.
    sorted_route_ids = list(sorted(route_to_frequency.keys()))  # get route_ids.
    for route_id in sorted_route_ids:
        # if network_style == 'low_frequency' and max(route_to_frequency[route_id]) > 2:  # if low frequency network and maximum frequency > 4.
        #     route_ids_to_remove.append(route_id)  # add route_id to remove.
        #     continue # skip route.
        # if network_style == 'high_frequency' and max(route_to_frequency[route_id]) < 7:  # if high frequency network and maximum frequency < 4.
        #     route_ids_to_remove.append(route_id)  # add route_id to remove.
        #     continue # skip route.
        route_name = route_id[:-1]  # get route name.
        route_dir = route_id[-1]  # get route direction.
        if route_dir in ['E', 'S']:
            marker = 'o'  # circle
        else:  # if route_dir in ['O', 'N'].
            marker = 's'  # square
        color = color_dict[route_name]  # get color.
        plt.plot(np.arange(0, nbr_hours, 1), route_to_frequency[route_id], label=route_id, marker=marker, color= color)  # plot frequency.
        plt.xticks(np.arange(0, nbr_hours, 1))
    plt.xlim(3, 23)
    maximum_frequency = max(f for route_id in route_to_frequency if route_id not in route_ids_to_remove for f in route_to_frequency[route_id])  # maximum frequency.
    # Add vertical lines at x = 14 and x = 19, and color the graph between these lines.
    plt.axvspan(14, 19, color='gray', alpha=0.2)  # color graph between 14 and 19.
    plt.axvline(x=14, color='gray', linestyle='--')  # add vertical line at x = 14.
    plt.axvline(x=19, color='gray', linestyle='--')  # add vertical line at x = 19.
    plt.text(14.5, maximum_frequency+1, 'OPTIMIZATION HORIZON',fontsize=10)  # add text at x = 14.5, y = 100.
    plt.xlabel('Time (hours)')
    plt.ylabel('Frequency (buses/hour)')
    plt.title('Headways for each route')
    if network_style != 'all':
        plt.legend()
    else: 
        plt.legend(ncol=4)  # show legend.

    # Save the figure as a PNG file with a high resolution (300 DPI) and close the plot to free up memory
    name = 'stl_'+network_style+'_instance_frequency.png'
    folder_name = 'figures_'+network_style
    folder = os.path.join(os.path.dirname(__file__), 'figures', folder_name)
    if not os.path.exists(folder):  # Check if the folder exists
        os.makedirs(folder)  # Create the folder if it doesn't exist
    completename = os.path.join(os.path.dirname(__file__), 'figures', folder_name, name)
    plt.savefig(completename, dpi=300)
    plt.close()  # Close the plot to free up memory
    return route_ids_to_remove  # return route_ids to remove.

def get_trips_departure_times():
    
    """Get departure time for each trip in route_to_trips.
    Inputs:
        route_to_trips (dict): route_id to trip_ids mapping.
    Outputs:
        dict: route_id to departure_times mapping."""

    stop_times_filepath = os.path.join(base_dir, 'stop_times_upgrade.txt')
    tripid_to_departure_times = {}
    tripid_to_stop_times = {}
    with open(stop_times_filepath, 'r') as stop_times_file:
        stop_times_reader = csv.reader(stop_times_file, delimiter=',')
        next(stop_times_reader, None)
        for stop_times_row in stop_times_reader:
            trip_id = stop_times_row[0]
            if trip_id not in tripid_to_stop_times:
                tripid_to_stop_times[trip_id] = {}
            arrival_time = stop_times_row[1]
            stop_id = stop_times_row[3]
            tripid_to_stop_times[trip_id][stop_id] = arrival_time
            planned_departure_time_from_origin = stop_times_row[9]
            if trip_id not in tripid_to_departure_times:
                tripid_to_departure_times[str(trip_id)] = int(planned_departure_time_from_origin)
    return tripid_to_departure_times, tripid_to_stop_times

def get_passenger_and_transfer_demand(trips_to_route, tripid_to_stop_times, route_ids):
    """Get passenger and transfer demand for all routes."""
    request_filepath = os.path.join(base_dir, 'requests.csv')
    route_to_passenger_demand = {}
    total_demand =[]
    stop_to_time_transfers = {}

    with open(request_filepath, 'r') as request_file:
        request_reader = csv.reader(request_file, delimiter=';')
        next(request_reader, None)
        for request_row in request_reader:
            add_total_demand = False
            legs_stops_pairs_list = None
            if len(request_row) - 1 == 7:
                legs_stops_pairs_list = literal_eval(request_row[7])
            if legs_stops_pairs_list is not None:
                i = 1
                all = len(legs_stops_pairs_list)
                ready_time = None
                for stops_pair in legs_stops_pairs_list:
                    first_stop_id = str(stops_pair[0])
                    second_stop_id = str(stops_pair[1])
                    trip_id = str(stops_pair[2])
                    boarding_time_first = tripid_to_stop_times[trip_id][first_stop_id]
                    boarding_time_second = tripid_to_stop_times[trip_id][second_stop_id]
                    route_id = trips_to_route[trip_id]
                    if route_id not in route_ids:
                        continue  # skip route.
                    add_total_demand = True
                    if ready_time is None:  # if first leg.
                        ready_time = int(boarding_time_first)  # if first leg, ready time is boarding time.
                    if route_id not in route_to_passenger_demand:
                        route_to_passenger_demand[route_id] = {}
                        route_to_passenger_demand[route_id]['regular'] = []
                        route_to_passenger_demand[route_id]['transfer'] = {}
                        route_to_passenger_demand[route_id]['transfer']['boarding'] = []
                        route_to_passenger_demand[route_id]['transfer']['alighting'] = []
                    route_to_passenger_demand[route_id]['regular'].append(boarding_time_first)
                    if i == 1 and i!=all: #alighting transfer
                        route_to_passenger_demand[route_id]['transfer']['alighting'].append(boarding_time_second)
                        if second_stop_id not in stop_to_time_transfers:
                            stop_to_time_transfers[second_stop_id] = {}
                            stop_to_time_transfers[second_stop_id]['boarding']=[]
                            stop_to_time_transfers[second_stop_id]['alighting']=[]
                        stop_to_time_transfers[second_stop_id]['alighting'].append(boarding_time_second)
                    elif i == all and i!=1: #boarding transfer
                        if first_stop_id not in stop_to_time_transfers:
                            stop_to_time_transfers[first_stop_id] = {}
                            stop_to_time_transfers[first_stop_id]['boarding']=[]
                            stop_to_time_transfers[first_stop_id]['alighting']=[]
                        stop_to_time_transfers[first_stop_id]['boarding'].append(boarding_time_first)
                        route_to_passenger_demand[route_id]['transfer']['boarding'].append(boarding_time_first)
                    elif i!=1 and i!=all: #both transfer
                        if first_stop_id not in stop_to_time_transfers:
                            stop_to_time_transfers[first_stop_id] = {}
                            stop_to_time_transfers[first_stop_id]['boarding']=[]
                            stop_to_time_transfers[first_stop_id]['alighting']=[]
                        stop_to_time_transfers[first_stop_id]['boarding'].append(boarding_time_first)
                        if second_stop_id not in stop_to_time_transfers:
                            stop_to_time_transfers[second_stop_id] = {}
                            stop_to_time_transfers[second_stop_id]['boarding']=[]
                            stop_to_time_transfers[second_stop_id]['alighting']=[]
                        stop_to_time_transfers[second_stop_id]['alighting'].append(boarding_time_second)
                        route_to_passenger_demand[route_id]['transfer']['boarding'].append(boarding_time_first)
                        route_to_passenger_demand[route_id]['transfer']['alighting'].append(boarding_time_second)
                    i+=1
            if add_total_demand:
                total_demand.append(ready_time)
    return route_to_passenger_demand, total_demand, stop_to_time_transfers

def get_hourly_passenger_demand(route_to_passenger_demand, total_demand, nbr_hours):
    """Get hourly passenger demand for all routes."""
    route_to_hourly_passenger_demand = {}  # route_id to hourly passenger demand mapping.
    total_transfer_demand = []  # total transfer demand.
    total_transfer_demand.extend([0] * nbr_hours)  # initialize total transfer demand.
    for route_id in route_to_passenger_demand:  # for each route.
        route_to_hourly_passenger_demand[route_id] = {}
        route_to_hourly_passenger_demand[route_id]['regular'] = []
        route_to_hourly_passenger_demand[route_id]['transfer'] = {}
        route_to_hourly_passenger_demand[route_id]['transfer'] = []
        for i in range(nbr_hours):
            route_to_hourly_passenger_demand[route_id]['regular'].append(0)
            route_to_hourly_passenger_demand[route_id]['transfer'].append(0)
        for boarding_time in route_to_passenger_demand[route_id]['regular']:
            hour = int(boarding_time) // 3600  # get hour.
            route_to_hourly_passenger_demand[route_id]['regular'][hour] += 1  # increment passenger demand.
        for boarding_time in route_to_passenger_demand[route_id]['transfer']['boarding']:
            hour = int(boarding_time) // 3600
            route_to_hourly_passenger_demand[route_id]['transfer'][hour] += 1
            total_transfer_demand[hour] += 1  # increment total transfer demand.
        for alighting_time in route_to_passenger_demand[route_id]['transfer']['alighting']:
            hour = int(alighting_time) // 3600
            route_to_hourly_passenger_demand[route_id]['transfer'][hour] += 1
    total_passenger_demand = []  # total passenger demand.
    total_passenger_demand.extend([0] * nbr_hours)  # initialize total passenger demand.
    total_demand = [x//3600 for x in total_demand]  # convert total demand to hours.
    for hour in total_demand:  # for each hour in total demand.
        total_passenger_demand[hour] += 1  # increment total passenger demand.
    return route_to_hourly_passenger_demand, total_passenger_demand, total_transfer_demand

def load_connections():
    """
    Load available connections from a JSON file and create a dictionary mapping each stop to its connected stops.
    """
    base_dir_connections = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'fixed_line')
    gtfs_2019_dir = os.path.join(base_dir_connections, 'gtfs', 'gtfs2019-11-01')
    connections_file = os.path.join(gtfs_2019_dir, 'available_connections.json')
    with open(connections_file, 'r') as file:
        connection_groups = json.load(file)
    
    stop_connections = {}
    for group in connection_groups:
        for stop_id in group:
            if stop_id not in stop_connections:
                stop_connections[stop_id] = set()
            stop_connections[stop_id].update(group)
    
    for stop_id in stop_connections:
        stop_connections[stop_id].discard(stop_id)
        stop_connections[stop_id] = list(stop_connections[stop_id])
    
    return stop_connections

def get_hourly_stop_transfer_demand(stop_to_time_transfers, nbr_hours):
    """This functions helps to get hourly transfer demand for each stop.
    We use this output for the transfer hub network style."""
    stop_to_hourly_transfer_demand = {}  # stop_id to hourly transfer demand mapping.
    for stop_id_str in stop_to_time_transfers:  # for each stop.
        stop_id = int(stop_id_str)
        stop_to_hourly_transfer_demand[stop_id] = {}
        stop_to_hourly_transfer_demand[stop_id]['boarding'] = []
        stop_to_hourly_transfer_demand[stop_id]['alighting'] = []
        for i in range(nbr_hours):
            stop_to_hourly_transfer_demand[stop_id]['boarding'].append(0)
            stop_to_hourly_transfer_demand[stop_id]['alighting'].append(0)
        for boarding_time in stop_to_time_transfers[stop_id_str]['boarding']:
            hour = int(boarding_time) // 3600  # get hour.
            stop_to_hourly_transfer_demand[stop_id]['boarding'][hour] += 1  # increment boarding transfer demand.
        for alighting_time in stop_to_time_transfers[stop_id_str]['alighting']:
            hour = int(alighting_time) // 3600  # get hour.
            stop_to_hourly_transfer_demand[stop_id]['alighting'][hour] += 1  # increment alighting transfer demand.
    
    # Merge dict entries which are connected stops. 
    stop_connections = load_connections()
    merged_stops = set()
    for stop_id in stop_to_hourly_transfer_demand:
        if stop_id in merged_stops:
            continue
        connected_stops = stop_connections.get(stop_id, [])
        for connected_stop in connected_stops:
            if connected_stop in stop_to_hourly_transfer_demand and connected_stop not in merged_stops:
                merged_stops.add(int(connected_stop))
                for i in range(nbr_hours):
                    stop_to_hourly_transfer_demand[stop_id]['boarding'][i] += stop_to_hourly_transfer_demand[connected_stop]['boarding'][i]
                    stop_to_hourly_transfer_demand[stop_id]['alighting'][i] += stop_to_hourly_transfer_demand[connected_stop]['alighting'][i]

    return stop_to_hourly_transfer_demand  # return stop to hourly transfer demand mapping.

def plot_stop_transfer_demand(stop_to_hourly_transfer_demand, nbr_hours):
    """Plot transfer demand for each stop in stop_to_hourly_transfer_demand."""
    # Create figure and subplots
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Define line styles for each demand type
    demand_types = {'boarding': ('-', axes[0], 'Boarding transfer demand\n(nbr boarding transfers/hour)', 'o'),
                    'alighting': ('-', axes[1], 'Alighting transfer demand\n(nbr alighting transfers/hour)', 's')}
    colors = ['red',  'green','blue', 'magenta', 'purple', 'darkcyan','gray', 'olive', 'cyan', 'black', 'pink', 'orange', 'yellow',  'lime', 'teal', 'indigo', 'maroon', 'navy', 'peru', 'plum', 'salmon', 'sienna', 'tan', 'thistle', 'tomato', 'turquoise', 'violet', 'wheat', 'yellowgreen', 'aquamarine', 'bisque', 'blueviolet', 'burlywood', 'cadetblue', 'chartreuse', 'chocolate', 'coral', 'cornflowerblue', 'cornsilk', 'crimson']
    color_dict = {}
    # Loop over demand types and plot in respective subplot
    for type, (linestyle, ax, ylabel, marker) in demand_types.items():

        legend_handles = []  # Initialize legend handles
        for stop_id in stop_to_hourly_transfer_demand:  # Iterate over stops
            max_transfer_demand = max(stop_to_hourly_transfer_demand[stop_id]['boarding'])  # Maximum transfer demand for stop
            if max_transfer_demand < 20:  # Skip stops with low transfer demand
                continue
            label = stop_id  # Label for legend
            if not color_dict.get(stop_id):
                color_dict[stop_id] = colors.pop(0)  # Get color
                color=color_dict[stop_id]
            else:
                color = color_dict[stop_id]
            line, = ax.plot(np.arange(0, nbr_hours, 1), 
                    stop_to_hourly_transfer_demand[stop_id][type], 
                    label=label, 
                    marker=marker, 
                    color=color, 
                    linestyle=linestyle)
            legend_handles.append(line)  # Add line to legend
        
        # Set individual legends
        ax.legend(handles=legend_handles, ncol=4, title = type + " demand")

        # Add vertical lines and shaded optimization horizon
        ax.axvspan(14, 19, color='gray', alpha=0.2)  
        ax.axvline(x=14, color='gray', linestyle='--')  
        ax.axvline(x=19, color='gray', linestyle='--') 
        ax.set_ylabel(ylabel)
        ax.set_xticks(np.arange(0, nbr_hours, 1))
        ax.set_xlim(3, 23)
        ax.set_xlabel('Time (hours)')
    axes[0].text(14, 10, 'OPTIMIZATION HORIZON', fontsize=10)

    # Set common x-axis properties
    axes[0].set_title('Transfer demand for each stop')  # plot title.
    # Save the figure as a PNG file with a high resolution (300 DPI) and close the plot to free up memory
    name = 'stl_instance_stop_transfer_demand.png'
    folder = os.path.join(os.path.dirname(__file__), 'figures')
    if not os.path.exists(folder):  # Check if the folder exists
        os.makedirs(folder)  # Create the folder if it doesn't exist
    completename = os.path.join(os.path.dirname(__file__),'figures', name)
    plt.savefig(completename, dpi=300)
    plt.close()  # Close the plot to free up memory

def plot_route_passenger_demand(route_to_hourly_passenger_demand, nbr_hours, color_dict, network_style):
    """Plot passenger demand for each route in route_to_hourly_passenger_demand."""
    # Sum demand for route_id with same route_name
    route_name_to_hourly_passenger_demand = {}
    sorted_route_ids = list(sorted(route_to_hourly_passenger_demand.keys()))
    for route_id in sorted_route_ids:
        route_name = route_id[:-1]
        if route_name not in route_name_to_hourly_passenger_demand:
            route_name_to_hourly_passenger_demand[route_name] = {}
            route_name_to_hourly_passenger_demand[route_name]['regular'] = [0]*nbr_hours
            route_name_to_hourly_passenger_demand[route_name]['transfer'] = [0]*nbr_hours
        for i in range(nbr_hours):
            route_name_to_hourly_passenger_demand[route_name]['regular'][i] += route_to_hourly_passenger_demand[route_id]['regular'][i]
            route_name_to_hourly_passenger_demand[route_name]['transfer'][i] += route_to_hourly_passenger_demand[route_id]['transfer'][i]
    maximum_passenger_demand = 0  # maximum passenger demand.
    if network_style == 'all':
        minmax_hourly_passenger_demand = 0  # minimum maximum hourly passenger demand.
    else:
        minmax_hourly_passenger_demand = 0  # minimum maximum hourly passenger demand.


    # Create figure and subplots
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Define line styles for each demand type
    demand_types = {'regular': ('-', axes[0], 'Passenger demand\n(nbr boarding passengers/hour)', 'o'),
                    'transfer': ('-', axes[1], 'Transfer demand\n(nbr boarding/alighting transfers/hour)', 's')}

    sorted_route_names = list(sorted(route_name_to_hourly_passenger_demand.keys()))  # Get route names

    # Loop over demand types and plot in respective subplot
    for type, (linestyle, ax, ylabel, marker) in demand_types.items():
        legend_handles = []  # Initialize legend handles
        for route_name in sorted_route_names:  # Iterate over routes
            label = route_name # Label for legend
            color = color_dict[route_name]  
            if max(route_name_to_hourly_passenger_demand[route_name]['regular']) < minmax_hourly_passenger_demand:
                continue
            maximum_passenger_demand = max(max(route_name_to_hourly_passenger_demand[route_name][type]), maximum_passenger_demand)  
            line, = ax.plot(np.arange(0, nbr_hours, 1), 
                    route_name_to_hourly_passenger_demand[route_name][type], 
                    label=label, 
                    marker=marker, 
                    color=color, 
                    linestyle=linestyle)
            legend_handles.append(line)  # Add line to legend
        
        # Set individual legends
        legend_columns = 2 if network_style != 'all' else 4
        ax.legend(handles=legend_handles, ncol=legend_columns, title = type + " demand")

        # Add vertical lines and shaded optimization horizon
        ax.axvspan(14, 19, color='gray', alpha=0.2)  
        ax.axvline(x=14, color='gray', linestyle='--')  
        ax.axvline(x=19, color='gray', linestyle='--') 
        ax.set_ylabel(ylabel)
        ax.set_xticks(np.arange(0, nbr_hours, 1))
        ax.set_xlim(3, 23)
        ax.set_xlabel('Time (hours)')
    axes[0].text(14, maximum_passenger_demand-10, 'OPTIMIZATION HORIZON', fontsize=10)

    # Set common x-axis properties
    #set title for axes[0] and axes[1]
    axes[0].set_title('Passenger demand for each route')  # plot title.
    axes[1].set_title('Transfer demand for each route')  # plot title.

    # Save the figure as a PNG file with a high resolution (300 DPI) and close the plot to free up memory
    name = 'stl_'+network_style+'_instance_route_demand.png'
    folder_name = 'figures_'+network_style
    folder = os.path.join(os.path.dirname(__file__), 'figures', folder_name)
    if not os.path.exists(folder):  # Check if the folder exists
        os.makedirs(folder)  # Create the folder if it doesn't exist
    completename = os.path.join(os.path.dirname(__file__),'figures', folder_name, name)
    plt.savefig(completename, dpi=300)
    plt.close()  # Close the plot to free up memory
    return

def get_color_dict(route_ids):  # get color dict.
    """Get color dict for each route in route_ids."""
    # Generate 40 colors by combining tab20, tab20b, and tab20c
    colors = [plt.get_cmap('tab20')(i/20) for i in range(20)] + \
             [plt.get_cmap('tab20b')(i/20) for i in range(20)] + \
             [plt.get_cmap('tab20c')(i/20) for i in range(20)]
    colors = ['red',  'green','blue', 'magenta', 'purple', 'darkcyan','gray', 'olive', 'cyan', 'black', 'pink', 'orange', 'yellow',  'lime', 'teal', 'indigo', 'maroon', 'navy', 'peru', 'plum', 'salmon', 'sienna', 'tan', 'thistle', 'tomato', 'turquoise', 'violet', 'wheat', 'yellowgreen', 'aquamarine', 'bisque', 'blueviolet', 'burlywood', 'cadetblue', 'chartreuse', 'chocolate', 'coral', 'cornflowerblue', 'cornsilk', 'crimson']
    # colors = [c for c in colors if (0.299*c[0] + 0.587*c[1] + 0.114*c[2]) < 0.75] # remove liht/pale colors
    color_dict = {}  # color dict.
    # cmap = plt.get_cmap("Set1")  # Set1 has strong, well-separated colors
    route_names = [route_id[:-1] for route_id in route_ids]  # get route names.
    route_names = sorted(list(set(route_names)))  # get unique route names.
    for i, route_name in enumerate(route_names):
        color_dict[route_name] = colors[i % len(colors)]  # Assign colors cyclically if more than 40 routes
    return color_dict  # return color dict.

def plot_total_passenger_demand(total_passenger_demand, total_transfer_demand, nbr_hours, network_style):
    """Plot total passenger demand."""
    # plot total passenger demand on left y-axis and total transfer demand on right y-axis.
    fig, ax1 = plt.subplots(figsize=(12, 8))  # create figure and axis.
    ax1.set_xlabel('Time (hours)')  # x-axis label.
    ax1.set_ylabel('Passenger demand (passengers/hour)')  # y-axis label.
    ax1.set_title('Total passenger demand')  # plot title.
    ax1.tick_params(axis='y')  # y-axis ticks.
    ax1.set_xticks(np.arange(0, nbr_hours, 1))  # x ticks at every hour.
    ax1.set_xlim(3, 24)  # Cut plots before 4am and after 11pm.
    ax1.plot(np.arange(0, nbr_hours, 1), total_passenger_demand, label='Total number of passengers', marker='o', color='b')  # plot total passenger demand.
    ax2 = ax1.twinx()  # create second y-axis.
    ax2.set_ylabel('Transfer demand (transfers/hour)')  # y-axis label.
    ax2.tick_params(axis='y')  # y-axis ticks.
    ax2.plot(np.arange(0, nbr_hours, 1), total_transfer_demand, label='Total number of transfers', marker='o', color='b', linestyle ='--')  # plot total transfer demand.
    fig.tight_layout()  # adjust layout.
    # Add vertical lines at x = 14 and x = 19, and color the graph between these lines.
    maximum_passenger_demand = max(total_passenger_demand)  # maximum passenger demand.
    ax1.axvspan(14, 19, color='gray', alpha=0.2)  # color graph between 14 and 19.
    ax1.axvline(x=14, color='gray', linestyle='--')  # add vertical line at x = 14.
    ax1.axvline(x=19, color='gray', linestyle='--')  # add vertical line at x = 19.
    ax1.text(14.5, maximum_passenger_demand+5, 'OPTIMIZATION HORIZON',fontsize=10)  # add text at x = 14.5, y = 100.
    # add legend for both y-axes.
    lines1, labels1 = ax1.get_legend_handles_labels()  # get legend handles and labels for first y-axis.
    lines2, labels2 = ax2.get_legend_handles_labels()  # get legend handles and labels for second y-axis.
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')  # add legend.
    
    # Save the figure as a PNG file with a high resolution (300 DPI) and close the plot to free up memory
    name = 'stl_'+network_style+'_instance_total_demand.png'
    folder_name = 'figures_'+network_style
    folder = os.path.join(os.path.dirname(__file__), 'figures', folder_name)
    if not os.path.exists(folder):  # Check if the folder exists
        os.makedirs(folder)  # Create the folder if it doesn't exist
    completename = os.path.join(os.path.dirname(__file__),'figures', folder_name, name)
    plt.savefig(completename, dpi=300)
    plt.close()  # Close the plot to free up memory
    return

### Get all trip_ids for each route in route_ids.
def analyze_network(network_style, route_ids):  # analyze network.
    color_dict = get_color_dict(route_ids)  # get color dict.
    route_to_trips, trips_to_route = get_trips()
    tripid_to_departure_times, tripid_to_stop_times = get_trips_departure_times()
    route_to_frequency, nbr_hours = get_route_frequency(route_to_trips, tripid_to_departure_times, route_ids)
    route_ids_to_remove = plot_route_frequency(route_to_frequency, nbr_hours, color_dict, network_style)
    for route_id in route_ids_to_remove:  # for each route_id to remove.
        route_ids.remove(route_id)  # remove route_id.
    print('network_style: ', network_style)  # print network style.
    print('route_ids: ', route_ids)  # print route_ids.

    route_to_passenger_demand, total_demand, stop_to_time_transfers = get_passenger_and_transfer_demand(trips_to_route, tripid_to_stop_times, route_ids)
    route_to_hourly_passenger_demand, total_passenger_demand, total_transfer_demand = get_hourly_passenger_demand(route_to_passenger_demand, total_demand, nbr_hours)
    stop_to_hourly_transfer_demand = get_hourly_stop_transfer_demand(stop_to_time_transfers, nbr_hours)
    plot_stop_transfer_demand(stop_to_hourly_transfer_demand, nbr_hours)
    plot_route_passenger_demand(route_to_hourly_passenger_demand, nbr_hours, color_dict, network_style)
    plot_total_passenger_demand(total_passenger_demand, total_transfer_demand, nbr_hours, network_style)