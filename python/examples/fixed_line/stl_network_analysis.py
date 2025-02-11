### This file analyses passenger demand and vehicle frequency for 25-Nov-2019. 
### We will evaluate the bus frequency of all routes in route_ids for the day.
### We will also evaluate the passenger demand for all routes in route_ids for the day and the total demand.
### We will also evaluate the passenger transfer demand for all routes in route_ids for the day and the total transfer demand.
import os
import csv
from ast import literal_eval
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as mcolors

base_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'fixed_line', 'gtfs', 'gtfs2019-11-25')

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
    return route_to_frequency, end_time, nbr_hours

def plot_route_frequency(route_to_frequency, nbr_hours, color_dict, network_style):
    """Plot frequency for each route in route_to_frequency."""
    #set plot size
    plt.figure(figsize=(12, 8))  # set plot size.
    maximum_frequency = max(max(route_to_frequency.values()))  # maximum frequency.
    for route_id in route_to_frequency:
        color = color_dict[route_id]  # get color.
        plt.plot(np.arange(0, nbr_hours, 1), route_to_frequency[route_id], label=route_id, marker='o', color= color)
        plt.xticks(np.arange(0, nbr_hours, 1))
    plt.xlim(3, 23)
    # Add vertical lines at x = 14 and x = 19, and color the graph between these lines.
    plt.axvspan(14, 19, color='gray', alpha=0.2)  # color graph between 14 and 19.
    plt.axvline(x=14, color='gray', linestyle='--')  # add vertical line at x = 14.
    plt.axvline(x=19, color='gray', linestyle='--')  # add vertical line at x = 19.
    plt.text(14.5, maximum_frequency+1, 'OPTIMIZATION HORIZON',fontsize=10)  # add text at x = 14.5, y = 100.
    plt.xlabel('Time (hours)')
    plt.ylabel('Frequency (buses/hour)')
    plt.title('Frequency for each route')
    if network_style != 'all':
        plt.legend()
    else: 
        plt.legend(ncol=3)  # show legend.

    # Save the figure as a PNG file with a high resolution (300 DPI) and close the plot to free up memory
    name = 'stl_'+network_style+'_instance_frequency.png'
    folder_name = 'figures_'+network_style
    folder = os.path.join(os.path.dirname(__file__), 'figures', folder_name)
    if not os.path.exists(folder):  # Check if the folder exists
        os.makedirs(folder)  # Create the folder if it doesn't exist
    completename = os.path.join(os.path.dirname(__file__), 'figures', folder_name, name)
    plt.savefig(completename, dpi=300)
    plt.close()  # Close the plot to free up memory
    return

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
                    if route_id not in route_ids:  # if route_id not in route_ids.
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
                    elif i == all and i!=1: #boarding transfer
                        route_to_passenger_demand[route_id]['transfer']['boarding'].append(boarding_time_first)
                    elif i!=1 and i!=all: #both transfer
                        route_to_passenger_demand[route_id]['transfer']['boarding'].append(boarding_time_first)
                        route_to_passenger_demand[route_id]['transfer']['alighting'].append(boarding_time_second)
                    i+=1
            if add_total_demand:
                total_demand.append(ready_time)
    return route_to_passenger_demand, total_demand

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

def plot_route_passenger_demand(route_to_hourly_passenger_demand, nbr_hours, color_dict, network_style):
    """Plot passenger demand for each route in route_to_hourly_passenger_demand."""
    plt.figure(figsize=(12, 8))  # set plot size.
    maximum_passenger_demand = 0  # maximum passenger demand.
    if network_style == 'all':
        minmax_hourly_passenger_demand = 0  # minimum maximum hourly passenger demand.
    else:
        minmax_hourly_passenger_demand = 0  # minimum maximum hourly passenger demand.
    for type in ['regular', 'transfer']:  # for each type.
        add_to_label = ""  # add to label.
        if type == 'regular':  # if regular demand.
            linestyle = '-'  # solid line.
        else:  # if transfer demand.
            linestyle = '--'  # dashed line.
            add_to_label += " (transfer)"  # add to label.
        for route_id in route_to_hourly_passenger_demand:  # for each route.
            label = route_id +add_to_label  # label.
            color = color_dict[route_id]  # get color.
            if max(route_to_hourly_passenger_demand[route_id]['regular']) < minmax_hourly_passenger_demand:
                continue
            maximum_passenger_demand = max(max(route_to_hourly_passenger_demand[route_id][type]), maximum_passenger_demand)  # maximum passenger demand.
            plt.plot(np.arange(0, nbr_hours, 1), route_to_hourly_passenger_demand[route_id][type], label=label, marker='o', color= color, linestyle = linestyle)  # plot passenger demand.
    plt.xticks(np.arange(0, nbr_hours, 1))  # x ticks at every hour.
    plt.xlim(3, 23)  # Cut plots before 4am and after 11pm.
    # Add vertical lines at x = 14 and x = 19, and color the graph between these lines.
    plt.axvspan(14, 19, color='gray', alpha=0.2)  # color graph between 14 and 19.
    plt.axvline(x=14, color='gray', linestyle='--')  # add vertical line at x = 14.
    plt.axvline(x=19, color='gray', linestyle='--')  # add vertical line at x = 19.
    plt.text(14.5, maximum_passenger_demand+5, 'OPTIMIZATION HORIZON',fontsize=10)  # add text at x = 14.5, y = 100.
    plt.xlabel('Time (hours)')  # x-axis label.
    plt.ylabel('Passenger demand (nbr boarding passengers/hour)\nand transfer demand (nbr boarding/alighting transfers/hour)')  # y-axis label.
    plt.title('Passenger demand for each route')  # plot title.
    if network_style != 'all':
        plt.legend(ncol=2,title="Regular vs Transfer Demand")  # show legend.
    else:
        plt.legend(ncol=4,title="Regular vs Transfer Demand")

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
    color_dict = {}  # color dict.
    cmap = plt.get_cmap("Set1")  # Set1 has strong, well-separated colors
    for i, route_id in enumerate(route_ids):  # for each route_id.
        color_dict[route_id] = cmap(i % cmap.N)  # get color.
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
    ax1.plot(np.arange(0, nbr_hours, 1), total_passenger_demand, label='Total passenger demand', marker='o', color='b')  # plot total passenger demand.
    ax2 = ax1.twinx()  # create second y-axis.
    ax2.set_ylabel('Transfer demand (transfers/hour)')  # y-axis label.
    ax2.tick_params(axis='y')  # y-axis ticks.
    ax2.plot(np.arange(0, nbr_hours, 1), total_transfer_demand, label='Total transfer demand', marker='o', color='r')  # plot total transfer demand.
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
    route_to_frequency, end_time, nbr_hours = get_route_frequency(route_to_trips, tripid_to_departure_times, route_ids)
    plot_route_frequency(route_to_frequency, nbr_hours, color_dict, network_style)

    route_to_passenger_demand, total_demand = get_passenger_and_transfer_demand(trips_to_route, tripid_to_stop_times, route_ids)
    route_to_hourly_passenger_demand, total_passenger_demand, total_transfer_demand = get_hourly_passenger_demand(route_to_passenger_demand, total_demand, nbr_hours)
    plot_route_passenger_demand(route_to_hourly_passenger_demand, nbr_hours, color_dict, network_style)
    plot_total_passenger_demand(total_passenger_demand, total_transfer_demand, nbr_hours, network_style)