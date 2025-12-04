import pandas as pd
import csv
import os
import matplotlib.pyplot as plt
from stl_gtfs_transfer_synchro import get_output_subfolder
import matplotlib.lines as mlines
from ast import literal_eval
import sys
import numpy as np
from fixed_line.stl_network_analysis import get_route_dictionary, get_color_dict, lighten_color
import traceback
from scipy.stats import ttest_rel, wilcoxon

sys.path.append(os.path.abspath('../..'))
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
sys.path.append(r"/home/kollau/Recherche_Kolcheva/Simulator/python/examples")

figsize = (12, 6)
mean_color = "black"
median_color = "black"
percentile_color = median_color
transfers_color = 'blue'#"#377eb8"#'dodgerblue'#'black'##
transfers_marker = "o-"
transfers_marker_size = 8
fontsize = 16

def analyze_simulations(simulation1_path, simulation2_path, total_transfers, transfers, relative_increase_threshold=1.5):
    # Load the two simulation data files
    sim1_df = pd.read_csv(simulation1_path)
    sim2_df = pd.read_csv(simulation2_path)
    
    # Identify total travel time for each passenger in each simulation
    sim1_df["total_travel_time"] = sim1_df["wait_before_boarding"] + sim1_df["onboard_time"] + sim1_df["transfer_time"]
    sim2_df["total_travel_time"] = sim2_df["wait_before_boarding"] + sim2_df["onboard_time"] + sim2_df["transfer_time"]

    # Filter out passengers with no transfers for transfer percentage calculation
    all_transfer_passangers_id = transfers.keys()
    positive_transfer_time_sim1 = sim1_df[sim1_df["id"].isin(all_transfer_passangers_id)]['transfer_time']
    positive_transfer_time_sim2 = sim2_df[sim2_df["id"].isin(all_transfer_passangers_id)]['transfer_time']

    # Merge DataFrames on 'id' column to align passenger data from both simulations
    comparison_df = pd.merge(sim1_df, sim2_df, on="id", suffixes=('_sim1', '_sim2'))

    # Identify missed transfers based on a relative increase in transfer time
    comparison_df["relative_transfer_increase"] = (
        comparison_df["transfer_time_sim2"] / comparison_df["transfer_time_sim1"]
    )
    comparison_df["missed_transfer_sim2"] = comparison_df["relative_transfer_increase"] > relative_increase_threshold
    comparison_df["missed_transfer_sim1"] = comparison_df["relative_transfer_increase"] < (1 / relative_increase_threshold)
    
    # Count the total number of transfers (all individual transfers) in each simulation
    total_transfers_sim1 = positive_transfer_time_sim1.shape[0]
    total_transfers_sim2 = positive_transfer_time_sim2.shape[0]

    # Count missed transfers (where relative increase indicates a missed transfer) in each simulation
    missed_transfers_sim1 = comparison_df["missed_transfer_sim1"].sum()
    missed_transfers_sim2 = comparison_df["missed_transfer_sim2"].sum()
    if total_transfers_sim1 < total_transfers:
        missed_transfers_sim1 += (total_transfers - total_transfers_sim1)
        total_transfers_sim1 = total_transfers
    if total_transfers_sim2 < total_transfers:
        missed_transfers_sim2 += (total_transfers - total_transfers_sim2)
        total_transfers_sim2 = total_transfers

    # Calculate percentage of missed transfers in each simulation
    missed_transfer_percentage_sim1 = (missed_transfers_sim1 / total_transfers) * 100 if total_transfers > 0 else 0
    missed_transfer_percentage_sim2 = (missed_transfers_sim2 / total_transfers) * 100 if total_transfers > 0 else 0

    # Output data for plotting
    output_data = {
        "travel_times_sim1": sim1_df["total_travel_time"],
        "travel_times_sim2": sim2_df["total_travel_time"],
        "transfer_times_sim1": positive_transfer_time_sim1,
        "transfer_times_sim2": positive_transfer_time_sim2,
        "missed_transfer_percentage_sim1": missed_transfer_percentage_sim1,
        "missed_transfer_percentage_sim2": missed_transfer_percentage_sim2,
        "total_transfers_sim1": total_transfers_sim1,
        "total_transfers_sim2": total_transfers_sim2,
        "missed_transfers_sim1": missed_transfers_sim1,
        "missed_transfers_sim2": missed_transfers_sim2,
        "positive_transfer_time_sim1": positive_transfer_time_sim1,
        "positive_transfer_time_sim2": positive_transfer_time_sim2,
    }

    return output_data

def get_request_transfer_data(requests_file_path, bus_trip_ids = None):
    request_file = os.path.join(requests_file_path, 'requests.csv')
    transfers = {}
    request_legs = {}
    with open(request_file, 'r') as requests_file:
        requests_reader = csv.reader(requests_file, delimiter=';')
        next(requests_reader, None)
        total_transfers = 0
        for row in requests_reader:
            request_id = row[0] 
            legs_stops_pairs_list = None
            if len(row) - 1 == 7:
                legs_stops_pairs_list = literal_eval(row[7])
            if legs_stops_pairs_list is not None:
                if bus_trip_ids is not None:
                    if len([leg for leg in legs_stops_pairs_list if str(leg[2]) in bus_trip_ids]) == 0:
                        continue
                request_legs[request_id] = []
                for leg in legs_stops_pairs_list:
                    request_legs[request_id].append( (int(leg[0]), int(leg[1]), str(leg[2])) )
                current_number_transfers = len(legs_stops_pairs_list) - 1
                total_transfers += current_number_transfers if current_number_transfers >= 0 else 0
                if current_number_transfers > 0:
                    transfers[request_id] = current_number_transfers
    return(transfers, total_transfers, request_legs)

def get_observations_df(output_folder_path, transfers):
    # We only need the status.ONBOARD for passengers with transfers
    trips_observations_df = pd.read_csv(os.path.join(output_folder_path, 'trips_observations_df.csv'))
    request_ids = list(sorted([request_id for request_id in transfers.keys()]))
    print('total number of transfers:', len(request_ids))
    trips_observations_df = trips_observations_df[
                        (trips_observations_df['Status'].isin(['PassengersStatus.ONBOARD'])) &
                        (trips_observations_df['ID'].isin(request_ids))]
    #Remove rows if Assigned vehicle contains 'walking' (these are added legs for walking time due to skip-stop tactic)
    trips_observations_df = trips_observations_df[
                     ~trips_observations_df['Assigned vehicle'].astype(str).str.contains('walking', na=False)]
    #Sort by ID and time
    trips_observations_df = trips_observations_df.sort_values(by=['ID', 'Time'])
    return trips_observations_df

def get_no_tactics_boarding_times(trips_observations_df, transfers):
    request_ids = list(sorted([request_id for request_id in transfers.keys()]))
    boarding_times = {}
    for request_id in request_ids:
        boarding_times[request_id] = []
    for index, row in trips_observations_df.iterrows():
        request_id = row['ID']
        boarding_times[request_id].append((str(row['Assigned vehicle']), int(row['Time'])))
    return boarding_times

def get_transfer_stats(output_folder_path, transfers, total_transfers, request_legs):
    """This function retrieves data on the number of completed and missed transfers, as well as the percentage of missed transfers
    from the results of a simulation run.
    In order to retrieve missed transfers we compare the vehicles used in the simulation for each leg of each request with the vehicles
    that were used in the optimal solution for the same leg. If the vehicles are different, we consider the transfer as missed.
    This is true because the original assigned vehicle is the best possible option for the passenger to make the transfer. If a passenger misses that vehicle, 
    they are re-assigned to the next vehicle on the same line"""
    number_of_completed_transfers = 0
    number_of_missed_transfers = 0
    
    # We only need the status.ONBOARD for passengers with transfers
    trips_observations_df = get_observations_df(output_folder_path, transfers)
    request_ids = list(sorted([request_id for request_id in transfers.keys()]))

    #There are multiple rows for each request_id, each one corresponding to a leg of the trip
    #We need to check if the vehicle is the same for each leg of the trip
    completed_requests = 0
    not_completed_requests = []
    not_completed_transfer_requests = []
    i = 0
    row_index = 0
    while i < len(request_ids):
        request_id = request_ids[i]
        request_legs_list = request_legs[request_id]
        if row_index >= len(trips_observations_df):
            i+=1
            not_completed_requests.append(request_id)
            if len(request_legs_list) > 0:
                not_completed_transfer_requests.append(request_id)
            continue
        row = trips_observations_df.iloc[row_index]
        row_request_id = row['ID']
        while row_request_id != request_id and i < len(request_ids):
            not_completed_requests.append(request_id)
            if len(request_legs_list) > 0:
                not_completed_transfer_requests.append(request_id)
            i+=1
            request_id = request_ids[i]
            request_legs_list = request_legs[request_id]
        if i >= len(request_ids):
            break
        first_leg = True
        completed_requests += 1
        leg_index = -1
        for leg in request_legs_list:
            leg_index += 1
            if row_request_id == request_id:
                if first_leg:
                    first_leg = False
                    row_index += 1
                    if row_index < len(trips_observations_df):
                        row = trips_observations_df.iloc[row_index]
                    else:
                        break
                    row_request_id = row['ID']
                    continue
                number_of_completed_transfers += 1
                row_index += 1
                if row_index < len(trips_observations_df):
                    row = trips_observations_df.iloc[row_index]
                else:
                    break
                row_request_id = row['ID']
            else:
                # This means the passenger did not manage to finish his trip (no more buses)
                if first_leg == False: 
                    number_of_missed_transfers += 1
        i+=1
    for request in not_completed_requests:
        number_of_missed_transfers += transfers[request]
    # Calculate the number of missed transfers and the percentage of missed transfers
    print('Total transfer requests:', len(request_ids))
    print('Counter missed transfers', number_of_missed_transfers)
    print('Counter completed transfers', number_of_completed_transfers)
    print('Total counted transfers', number_of_missed_transfers + number_of_completed_transfers)
    print('Total transfers in requests.csv file', total_transfers)
    if total_transfers != number_of_missed_transfers + number_of_completed_transfers:
        print('Error in counting transfers')
    percentage_missed_transfers = (number_of_missed_transfers/total_transfers)*100 if total_transfers > 0 else 0
    return(number_of_completed_transfers, percentage_missed_transfers, not_completed_transfer_requests)

def old_get_transfer_stats(output_folder_path, transfers, total_transfers, request_legs):
    """This function retrieves data on the number of completed and missed transfers, as well as the percentage of missed transfers
    from the results of a simulation run."""
    trips_observations_df = pd.read_csv(os.path.join(output_folder_path, 'trips_observations_df.csv'))
    number_of_completed_transfers = 0

    ### Filter out passengers that did not finish their trip
    trips_observations_df = trips_observations_df[trips_observations_df['Status'] == 'PassengersStatus.COMPLETE']
    number_of_completed_transfers = 0

    # filter trips_observations_df for request_id and next_legs = []
    trips_observations_df = trips_observations_df[trips_observations_df['Next legs'].astype(str) == '[]']
    trips_observations_df['ID'] = trips_observations_df['ID'].astype(str)

    # Only keep rows where trips_observations_df['ID'].astype(str) is in transfers.keys()
    trips_observations_df = trips_observations_df[trips_observations_df['ID'].astype(str).isin(transfers.keys())]
    for index, row in trips_observations_df.iterrows():
        request_id = row['ID']
        num_transfers = transfers[request_id]
        number_of_completed_transfers += num_transfers
  

    # Calculate the number of missed transfers and the percentage of missed transfers
    number_missed_transfers = total_transfers - number_of_completed_transfers
    percentage_missed_transfers = (number_missed_transfers/total_transfers)*100 if total_transfers > 0 else 0
    return(number_of_completed_transfers, number_missed_transfers, percentage_missed_transfers)

def get_travel_time_stats(output_folder_path, transfers, not_completed_transfer_requests):
    total_times = []
    transfer_times = []
    # Get total travel time for all passengers (not only transfer passengers)
    create_trip_details_df(output_folder_path=output_folder_path, not_completed_transfer_requests = not_completed_transfer_requests, transfers = transfers)
    trips_details_observations_df = pd.read_csv(os.path.join(output_folder_path, 'trips_details_observations_df_new.csv'))
    treated_not_completed_transfer_requests = []
    for index, row in trips_details_observations_df.iterrows():
        request_id = row['id']
        if request_id in not_completed_transfer_requests and request_id not in treated_not_completed_transfer_requests:
            treated_not_completed_transfer_requests.append(request_id)
        total_time = row['wait_before_boarding'] + row['onboard_time'] + row['transfer_time']
        total_times.append(total_time)
        if row['id'] in transfers.keys():
            transfer_times.append(row['transfer_time'])
    # What about passengers that did not get a bus?
    not_completed_transfer_requests = list(set(not_completed_transfer_requests) - set(treated_not_completed_transfer_requests))
    print('Number of not treated request ids:', len(not_completed_transfer_requests))
    return(total_times, transfer_times)

def create_trip_details_df(output_folder_path, not_completed_transfer_requests, transfers):
    nbr_passengers_no_bus = 0
    observations_df = pd.read_csv(os.path.join(output_folder_path, 'trips_observations_df.csv'))
    observations_details = []
    id_col = "ID"
    status_col = 'Status'
    time_col = 'Time'
    reg_penalty_factor = 900
    transfer_penalty_factor = 900
    ## first clean data of all rows for which 'status' is 'PassengersStatus.ASSIGNED'
    observations_sorted = observations_df[observations_df['Status'].isin(['PassengersStatus.ONBOARD', 'PassengersStatus.READY', 'PassengersStatus.COMPLETE', 'PassengersStatus.RELEASE'])]
    observations_sorted = observations_sorted.sort_values(by=[id_col, time_col], ascending =[True, True], inplace=False)
    observations_sorted["duration"] = observations_sorted[time_col]. \
        transform(lambda s: s.shift(-1) - s)
    ### if status is 'PassengersStatus.COMPLETE' the 'duration' should be equal to 0
    observations_sorted.loc[observations_sorted[status_col] == 'PassengersStatus.COMPLETE', 'duration'] = 0
    ### For each group, wait before boarding is the duration of the first row with status 'PassengersStatus.Ready' before the first row with status 'PassengersStatus.ONBOARD'
    all_id_values = observations_sorted[id_col].unique()
    for id in all_id_values:
        group = observations_sorted[observations_sorted[id_col] == id]
        nbr_transfers = len(literal_eval(group['Next legs'].iat[0]))
        ready_row = group[group[status_col] == 'PassengersStatus.READY'].head(1)
        if ready_row.empty:
            next_legs = group['Next legs'].iat[0]
            time_penalty = (1+len(literal_eval(next_legs)))*reg_penalty_factor
            transfer_penalty = len(literal_eval(next_legs))*transfer_penalty_factor
            wait_before_boarding = 0
            onboard_time = time_penalty
            transfer_time = transfer_penalty
            nbr_passengers_no_bus += 1
        else:
            wait_before_boarding = 0
            onboard_time = 0
            transfer_time = 0
            #check if passenger completer the journey
            if group[group[status_col] == 'PassengersStatus.COMPLETE'].empty:
                nbr_passengers_no_bus += 1
                #Set last row duration to 0 
                group.loc[group.tail(1).index, 'duration'] = 0
                #get last row
                last_row = group.tail(1)
                # print('Passenger did not complete the journey')
                # print('Passenger id:', id)
                # print('Last row:', last_row)
                #check if ready_row and last row are the same
                if ready_row.equals(last_row): #passenger never boarded any bus
                    next_legs = group['Next legs'].iat[0]
                    time_penalty = (1+len(literal_eval(next_legs)))*reg_penalty_factor # penalty for each leg (including current leg)
                    transfer_penalty = len(literal_eval(next_legs))*transfer_penalty_factor # 30 minutes penalty per transfer
                    wait_before_boarding += 0
                    onboard_time += time_penalty
                    transfer_time += transfer_penalty
                else:
                    #get remaining legs
                    next_legs = last_row['Next legs'].iat[0]
                    time_penalty = (len(literal_eval(next_legs)))*reg_penalty_factor # penalty for each leg (including current leg)
                    transfer_penalty =  (len(literal_eval(next_legs)))*transfer_penalty_factor # 30 minutes penalty per transfer
                    # get last row status
                    last_row_status = last_row[status_col].iat[0]
                    if last_row_status == 'PassengersStatus.ONBOARD':# current leg has started but we don't know how long it was (this could be improved if we know when the bus trip arrived at the stop.)
                        time_penalty += reg_penalty_factor
                    elif last_row_status in ['PassengersStatus.READY', 'PassengersStatus.RELEASE']: # current leg has not started AND it is a transfer (not the fist leg)
                        transfer_penalty += transfer_penalty_factor
                        time_penalty += reg_penalty_factor
                    wait_before_boarding += 0
                    onboard_time += time_penalty
                    transfer_time += transfer_penalty
            wait_before_boarding += ready_row['duration'].iat[0]
            onboard_time += sum(group[group[status_col] == 'PassengersStatus.ONBOARD']['duration'])
            transfer_time += sum(group[group[status_col] == 'PassengersStatus.READY']['duration']) - wait_before_boarding
        observation = {
            "id" : id,
            "wait_before_boarding" : wait_before_boarding,
            "onboard_time" : onboard_time,
            "transfer_time" : transfer_time,
            "nbr_transfers" : nbr_transfers
        }
        observations_details.append(observation)
    # Get all observation_details ids
    all_ids = list(sorted([observation['id'] for observation in observations_details]))
    # check if not_completed_transfer_requests are in all_ids
    for request_id in not_completed_transfer_requests:
        if request_id not in all_ids:
            transfer_time = 0
            wait_before_boarding = 0
            onboard_time = reg_penalty_factor
            if request_id in transfers.keys():
                transfer_time += transfers[request_id]*transfer_penalty_factor
                onboard_time += (transfers[request_id]-1)*reg_penalty_factor
            observation = {
                "id" : request_id,
                "wait_before_boarding" : wait_before_boarding,
                "onboard_time" : onboard_time,
                "transfer_time" : transfer_time,
                "nbr_transfers" : transfers[request_id]
            }
            observations_details.append(observation)
    observations_details_df = pd.DataFrame(observations_details)
    observations_details_df_path = os.path.join(output_folder_path, 'trips_details_observations_df_new.csv')
    print('Saving trips_details_observations_df_new.csv to ', observations_details_df_path)
    observations_details_df.to_csv(observations_details_df_path, index=False)
    print('Number of passengers that did not get a bus:', nbr_passengers_no_bus)
    return()

def get_transfer_and_travel_time_stats(output_folder_path, transfers, total_transfers, request_legs):
    number_of_completed_transfers, percentage_missed_transfers, not_completed_transfer_requests = get_transfer_stats(output_folder_path, transfers, total_transfers, request_legs)
    total_times, transfer_times = get_travel_time_stats(output_folder_path, transfers, not_completed_transfer_requests)
    return(number_of_completed_transfers, percentage_missed_transfers, transfer_times, total_times)

def get_ylabel(transfer_type):
    """Return the ylabel based on the transfer type."""
    if transfer_type == 0:
        return("Missed Transfers (%)")
    elif transfer_type == 1:
        return("Number of transfers")
    else:
        return("Mean transfer time\n(in minutes)")

def plot_boxplots(data : list,
                  missed_transfer_percentages : list,
                  positions : list,
                  group_ticks : list,  # One tick per main group
                  group_tick_labels: list,  # Track labels for main groups
                  color_map : list,  # Track colors to apply to each box
                  transfer_type: int,
                  title : str,
                  complete_figure_name : str,
                  legend_patches : list = [],
                  xlabel : str = None):
    """ Function to plot boxplots with custom colors, mean line, and labels. Centralized here to ensure consistent
     formatting across different plots, as well as consistent colors.
     Parameters:
     
      - data: List of lists containing the data for each boxplot
      - positions: List of positions for each boxplot
      - group_ticks: List of positions for the x-tick labels
      - group_tick_labels: List of labels for the x-tick labels
      - color_map: List of colors for each boxplot 
      - transfer_type: Type of transfer data (0 for percentage, 1 for number, 2 for mean time)
      """
    # Boxplot with custom colors, mean line, and labels
    fig, ax = plt.subplots(figsize=figsize)
    ax2 = ax.twinx()  # Create secondary y-axis for missed transfer percentages
    bp = ax.boxplot(data, positions=positions, patch_artist=True, showmeans=True,
                    meanline=True, meanprops=dict(color=mean_color, linestyle='--', linewidth=2),
                    medianprops=dict(color=median_color, linewidth=2), showfliers=False)
    
    for patch, color in zip(bp['boxes'], color_map):  # Apply consistent colors
        patch.set_facecolor(color)

    for i, pos in enumerate(positions):
        # Get the y-values for median and mean
        median = bp['medians'][i]
        mean = bp['means'][i]
        median_value = median.get_ydata()[0]
        mean_value = mean.get_ydata()[0]

        # Annotate the median value above the median line
        ax.text(pos, median_value-0.5, f'{median_value:.1f}', ha='center', va='top', fontsize=fontsize-2, color=median_color)
        # Annotate the mean value below the mean line
        ax.text(pos, mean_value, f'{mean_value:.1f}', ha='center', va='bottom', fontsize=fontsize-2, color=mean_color)
    
    # Set primary y-axis parameters 
    ax.set_ylim(0, max([max(group) for group in data]) * 0.7)  # Set y-limit for better visibility
    ax.set_ylim(0, 110)  # Set y-limit for better visibility
    ax.tick_params(axis='y', which='major', labelsize=fontsize-2, labelleft=True, labelright=False, left=True, right=False)
    ax.set_ylabel("Travel Time (minutes)", fontsize=fontsize)
    # Set x-axis ticks and labels
    ax.set_xticks(group_ticks)
    ax.set_xticklabels(group_tick_labels, fontsize= fontsize)
    if xlabel is not None:
        ax.set_xlabel(xlabel, fontsize=fontsize)

    # Plot missed transfer percentages as points on the secondary y-axis
    ylabel = get_ylabel(transfer_type)
    # Round percentages to one decimal place
    missed_transfer_percentages = [round(value, 1) for value in missed_transfer_percentages]
    ax2.plot(positions, missed_transfer_percentages, transfers_marker, color=transfers_color, label = ylabel, markersize=transfers_marker_size, zorder = 10 )
    # Add values as text annotations above the points
    for i, value in enumerate(missed_transfer_percentages):
        ax2.text(positions[i]-0.05, value+0.1, f'{value:.1f}', ha='center', va='bottom', fontsize=fontsize-2, color=transfers_color, zorder = 10)
    
    # Set secondary y-axis parameters
    ax2.tick_params(axis='y', which='major', labelsize=fontsize-2, labelleft=False, labelright=True, left=False, right=True, color=transfers_color, labelcolor=transfers_color)
    ax2.set_ylim(min(missed_transfer_percentages)*0.7, max(missed_transfer_percentages) * 1.2)  # Set y-limit for better visibility
    ax2.set_ylim(2, max(missed_transfer_percentages) * 1.2)  # Set y-limit for better visibility
    ax2.set_ylim(-5, 22)  # Set y-limit for better visibility
    ax2.set_ylabel(ylabel, fontsize=fontsize, color=transfers_color)

    # Add mean, median, and missed transfer line entries to the legend
    mean_line = mlines.Line2D([0], [0], color = mean_color, linestyle = '--', linewidth = 2, label = 'Mean')
    median_line = mlines.Line2D([0], [0], color = median_color, linestyle = '-', linewidth = 2, label = 'Median')
    missed_transfers_line = mlines.Line2D([0], [0], color = transfers_color, lw=2, label = ylabel)
    legend_patches.extend([mean_line, median_line, missed_transfers_line])

    # Set figure title
    ax.set_title(title, fontsize=fontsize + 2)

    # Optimize legend position and style
    legend = ax.legend(handles=legend_patches, loc='upper left', fontsize=fontsize-2, title_fontsize=fontsize,
             framealpha=0.9, shadow=True, ncol = 4)
    legend.set_zorder(100)

    plt.tight_layout()
    plt.savefig(complete_figure_name, dpi = 300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    return()

def get_tactic_stats(baseline_folder, line_name):
    tactics_filename = os.path.join(baseline_folder, 'tactics.txt')
    if not os.path.exists(tactics_filename):
        return()
    
    tactic_stats = {}
    for route_name in line_name:
        tactic_stats[route_name] = {}
        tactic_stats[route_name]['h_hp'] = 0
        tactic_stats[route_name]['none'] = 0
        tactic_stats[route_name]['h_t'] = 0
        tactic_stats[route_name]['ss'] = 0
        tactic_stats[route_name]['sp'] = 0
        tactic_stats[route_name]['sp_hp'] = 0
        tactic_stats[route_name]['sp_t'] = 0

    with open(tactics_filename, 'r') as file:
        lines = file.readlines()
        lines = lines[2:]
        for line in lines:
            line = line.strip()
            # split line by comma
            # 4 is speedup
            # 5 is skip-stop
            # 6 is hold
            line_split = line.split(',')
            route_name = line_split[0].strip()
            ss = literal_eval(line_split[5].strip())
            sp = literal_eval(line_split[4].strip())
            hold = line_split[6].strip()
            if len(hold) > 2:
                continue
            hold = literal_eval(hold)
            if route_name not in tactic_stats:
                continue
            if ss == True:
                tactic_stats[route_name]['ss'] += 1
            elif sp == True: # sp
                if hold == -1:
                    tactic_stats[route_name]['sp'] += 1
                elif hold == 0:
                    tactic_stats[route_name]['sp_hp'] += 1
                elif hold == 1:
                    tactic_stats[route_name]['sp_t'] += 1
            elif hold == 0: # hold
                tactic_stats[route_name]['h_hp'] += 1
            elif hold == 1:
                tactic_stats[route_name]['h_t'] += 1
            else:
                tactic_stats[route_name]['none'] += 1
    for route_name in tactic_stats:
        # Print stats
        print('*************')
        print('Route name:', route_name)
        print('Hold for planned time:', tactic_stats[route_name]['h_hp'])
        print('Hold for transfer time:', tactic_stats[route_name]['h_t'])
        print('Spedup:', tactic_stats[route_name]['sp'])
        print('Speedup and hold for planned time:', tactic_stats[route_name]['sp_hp'])
        print('Speedup and hold for transfer time:', tactic_stats[route_name]['sp_t'])
        print('Skip-stop:', tactic_stats[route_name]['ss'])
        print('******************')

def plot_network_comparisons(instance_name,
                            requests_file_path,
                            line_name="70E",
                            base_folder="output/fixed_line/gtfs",
                            transfer_type = 0,
                            network_style = '',
                            greyscale = False):
    """ 
    Compare the passenger travel times for across different algorithms and settings.

    Parameters:
    - instance_name: Name of the test instance folder
    - line_name: Name of the bus line(s) to compare
    - base_folder: Base folder for the output data
    - transfer_type: 0 for percentage of missed transfers
                     1 for number of missed transfers
                     2 for mean transfer time

    """
    base_params, algo_params = get_params(line_name)

    # Prepare to collect output data for each comparison
    output_folder_path = os.path.join(base_folder, instance_name)
    group_data = {}
    missed_transfer_data = {}

    ### Get the total number of transfers
    transfers, total_transfers, request_legs = get_request_transfer_data(requests_file_path=requests_file_path)

    # Define the labels for main groups
    group_labels = ["Baseline", "Hold", "Hold&\nSpeedup", "Hold&\nSkip-Stop", "Hold, Speedup&\nSkip-Stop"]
    sub_labels = ["Deterministic", "Regret", "Perfect Info"]

    # Initialize group_data with Baseline baseline
    baseline_folder = get_output_subfolder(output_folder_path, *base_params)
    if os.path.exists(os.path.join(baseline_folder, 'trips_observations_df.csv')):
        number_of_completed_transfers_notactics, percentage_missed_transfers_notactics, transfer_times_notactics, total_times_notactics = get_transfer_and_travel_time_stats(baseline_folder, transfers, total_transfers, request_legs)
        get_tactic_stats(baseline_folder, line_name)
     # Ensure the baseline file exists
    baseline_file = os.path.join(baseline_folder, "trips_details_observations_df_new.csv")
    if not os.path.exists(baseline_file):
        raise FileNotFoundError(f"Baseline file not found: {baseline_file}")
    group_data["Baseline"] = [time / 60 for time in total_times_notactics]
    if transfer_type == 0:
        missed_transfer_data["Baseline"] = percentage_missed_transfers_notactics #output_data_baseline["missed_transfer_percentage_sim1"] 
    elif transfer_type == 1:
        missed_transfer_data["Baseline"] = number_of_completed_transfers_notactics #output_data_baseline["total_transfers_sim1"]
    else:
        missed_transfer_data["Baseline"] = np.mean(transfer_times_notactics)/60

    # Generate comparisons for algo_params
    for i, params in enumerate(algo_params):
        sim_folder = get_output_subfolder(output_folder_path, *params)
        if os.path.exists(os.path.join(sim_folder, 'trips_observations_df.csv')):
            number_of_completed_transfers_key, percentage_missed_transfers_key, transfer_times_key, total_times_key = get_transfer_and_travel_time_stats(sim_folder, transfers, total_transfers, request_legs)
            get_tactic_stats(sim_folder, line_name)
        else:
            print('*** PROBLEM ***')
            print('ALGO PARAMS', params)
            print('SIM FOLDER', sim_folder)
            print('NO DATA')
            continue
        group_index = 1 + i // 3  # Group index based on the 6 groups specified
        key = f"{group_labels[group_index]} {sub_labels[i % 3]}"
        group_data[key] = [time / 60 for time in total_times_key]
        if transfer_type == 0:
            missed_transfer_data[key] = percentage_missed_transfers_key#output_data["missed_transfer_percentage_sim2"] 
        elif transfer_type == 1:
            missed_transfer_data[key] = int(number_of_completed_transfers_key)#output_data["total_transfers_sim2"]
        else:
            missed_transfer_data[key] = np.mean(transfer_times_key)/60

    # Define consistent colors for each algorithm across groups
    algorithm_colors = get_algorithm_colors(greyscale=greyscale)
    algorithm_colors["Baseline"] = algorithm_colors['No tactics']  # Use the same color for Baseline as No tactics

    # Prepare data for plotting : prepare data for boxplot with spacing between groups
    positions = []
    data = []
    group_ticks = []  # One tick per main group
    color_map = []  # Track colors to apply to each box
    group_tick_labels = []  # Track labels for main groups
    pos = 1
    missed_transfer_percentages = []  # Track missed transfer percentage for each boxplot
    for i, group in enumerate(group_labels):
        if group in group_data:
            data.append(group_data[group])
            color_map.append(algorithm_colors.get(group, "#AEC6CF"))  # Default color if missing
            positions.append(pos)
            group_ticks.append(pos)  # Position for the x-tick label
            group_tick_labels.append(group)
            missed_transfer_percentages.append(missed_transfer_data.get(group, 0))
            pos += 0.7
        else:  # For groups with multiple sub-groups
            group_ticks.append(pos + 1)
            group_tick_labels.append(group)

        # Sub-groups for algorithms
        for j, sub_label in enumerate(sub_labels):
            key = f"{group} {sub_label}"
            if key in group_data:
                data.append(group_data[key])
                color_map.append(algorithm_colors[sub_label])  # Consistent color per algorithm
                positions.append(pos)
                missed_transfer_percentages.append(missed_transfer_data.get(key, 0))
                pos += 0.7
        pos += 0.7  # Add space between main groups

    # Get legend for algorithm colors with bold font
    legend_patches = [mlines.Line2D([0], [0], color=color, lw=7, label=label)
                      for label, color in algorithm_colors.items() if label in ["Baseline"] + sub_labels ]
    
    # Get title:
    all_lines_string = get_line_str(network_style, line_name)
    title = "Comparison of passenger travel and transfer times\nfor " + all_lines_string
    
    # Get image name
    if transfer_type == 0:
        addendum = 'pecentage_missed_transfers'
    elif transfer_type == 1:
        addendum = 'number_transfers'
    else:
        addendum = 'mean_transfer_time'
    figure_name = get_image_name(network_style, line_name)
    figure_name = f"{figure_name}_travel_time_and_"+addendum+"_comparison.png"
    complete_figure_name = os.path.join(base_folder, instance_name, figure_name)
    
    # Plot figure
    plot_boxplots(data = data,
                  missed_transfer_percentages = missed_transfer_percentages,
                  positions = positions,
                  group_ticks = group_ticks,  # One tick per main group
                  group_tick_labels = group_tick_labels,  # Track labels for main groups
                  color_map = color_map,  # Track colors to apply to each box
                  transfer_type = transfer_type, 
                  title = title,
                  complete_figure_name = complete_figure_name,
                  legend_patches = legend_patches)
    print('Figure saved to', complete_figure_name)
    return()

def get_algorithm_colors(greyscale=False):
    algorithm_colors = {
        "No tactics": "grey",
        "Optimal\ntravel paths": "#f781bf",
        "Deterministic": '#4daf4a',
        "Regret": "#ff7f00",
        "Perfect Info": '#f781bf'
    }
    if greyscale:
        algorithm_colors = {
            "No tactics": 'darkgray',
            "Optimal\ntravel paths": "gray",
            "Deterministic": "dimgray",
            "Regret": "slategray",
            "Perfect Info": 'lightgray'
        }
    return algorithm_colors

def get_params(line_name, algo = None, ss = None, sp = None):
    # Define base parameters for comparisons
    base_params = (0, False, False, line_name, True)  # No tactics, smartcard data (baseline)
    # optimal_travel_paths_params = (0, False, False, [line_name], False)  # Optimal travel paths

    # Define parameter sets for groups 3 to 6
    algo_params = [
        # Group 3: Algorithms with smartcard data, Hold only
        (1, False, False, line_name, True),  # Deterministic
        (2, False, False, line_name, True),  # Regret
        (3, False, False, line_name, True),  # Perfect Information

        # Group 4: Algorithms with smartcard data, Hold and Speedup allowed
        (1, False, True, line_name, True),   # Deterministic
        (2, False, True, line_name, True),   # Regret
        (3, False, True, line_name, True),   # Perfect Information

        # Group 5: Algorithms with smartcard data, Hold and Skip-Stop allowed
        (1, True, False, line_name, True),   # Deterministic
        (2, True, False, line_name, True),   # Regret
        (3, True, False, line_name, True),   # Perfect Information

        # Group 6: Algorithms with smartcard data, Hold, Speedup and Skip-Stop allowed
        (1, True, True, line_name, True),    # Deterministic
        (2, True, True, line_name, True),    # Regret
        (3, True, True, line_name, True)     # Perfect Information
    ]
    if algo is not None:
        # remove all params that are not equal to algo
        algo_params = [param for param in algo_params if param[0] == algo]
    if ss is not None:
        # remove all params that are not equal to ss
        algo_params = [param for param in algo_params if param[1] == ss]
    if sp is not None:
        # remove all params that are not equal to speedup
        algo_params = [param for param in algo_params if param[2] == sp]
    return(base_params, algo_params)

def get_line_str(network_style, line_name):
    lines_str_dict = {}
    if len(line_name)>10:
        all_lines_string = 'All lines'
    else:
        all_lines_string = ', '.join([str(line_name_single)[:-1] for line_name_single in line_name])
    lines_str_dict[''] = all_lines_string
    lines_str_dict['all'] = 'all lines.'
    lines_str_dict['grid']= 'lines in grid sub-network.'
    lines_str_dict['low_frequency'] = 'lines in low frequency sub-network.'
    lines_str_dict['high_frequency'] = 'lines in high frequency sub-network.'
    lines_str_dict['radial'] = 'lines in radial sub-network.'
    lines_str_dict['corridor'] = 'lines in corridor sub-network.'
    lines_str_dict['151'] = "line 151 and it's connecting lines."
    lines_str_dict['transfer_hubs'] = 'optimization around transfer hubs.'
    lines_str_dict['to_low_frequency'] = 'low frequency PM demand lines.'
    print('new network style:', network_style)
    all_lines_string = lines_str_dict[network_style]
    return(all_lines_string)

def get_image_name(network_style, line_name):
    lines_str_dict = {}
    if len(line_name)>10:
        all_lines_string = 'All_lines'
    else:
        all_lines_string = ', '.join([str(line_name_single)[:-1] for line_name_single in line_name])
    lines_str_dict[''] = all_lines_string
    lines_str_dict['all'] = 'all'
    lines_str_dict['grid']= 'grid'
    lines_str_dict['low_frequency'] = 'low_frequency'
    lines_str_dict['high_frequency'] = 'high_frequency'
    lines_str_dict['radial'] = 'radial'
    lines_str_dict['corridor'] = 'corridor'
    lines_str_dict['151'] = "line_151"
    lines_str_dict['transfer_hubs'] = 'transfer_hubs'
    lines_str_dict['to_low_frequency'] = 'to_low_frequency'
    all_lines_string = lines_str_dict[network_style]
    return(all_lines_string)

def plot_travel_time_change_distribution(instance_name,
                                         line_name,
                                         base_folder="output/fixed_line/gtfs",
                                         network_style = '',
                                         transfers = 0,
                                         ss = None, sp = None):
    """
    This function plots the distribution of travel time changes for passengers. 
    It creates a violin plot for each algorithm and setting, showing the change in total passenger travel time compared to the baseline.
    Parameters:
    - instance_name: Name of the test instance folder
    - line_name: Name of the bus line(s) to compare
    - base_folder: Base folder for the output data
    - network_style: Style of the network (e.g., 'all', 'grid', 'low_frequency', etc.)
    - transfers: Type of transfer data (0 for all passengers, 1 for passengers without transfers, 2 for passengers with transfers)

    Violin plots:
    (1) If no algo is specified
        X-axis: Test cases (Baseline, Hold-D, Hold-R, ..., All tactics-PI)
        Y-axis: Change in total passenger travel time (compared to the baseline)
    (2) If skip-stop and speedup specified
        X-axis: Test cases: All passengers, Passengers without transfers, Passengers with transfers for these tactics (D, R, PI)
        Y-axis: Change in total passenger travel time (compared to the baseline)
        """

    output_folder_path = os.path.join(base_folder, instance_name)
    
    # Check if this is for one particular case of tactics or not
    is_particular_case = ss is not None or sp is not None
    # Define the labels for main groups
    if not is_particular_case:
        group_labels = ["Hold", "Hold&\nSpeedup", "Hold&\nSkip-Stop", "Hold, Speedup&\nSkip-Stop"]
        group_labels_short = ['H', 'H&SP', 'H&SS', 'AllTactics']
    else: 
        group_labels = ["All passengers", "Passengers\nwithout transfers", "Passengers\nwith transfers"]
        group_labels_short = ['All', 'NoTransfers', 'YesTransfers']
    sub_labels = ["Deterministic", "Regret", "Perfect Info"]

    # Get params
    base_params, algo_params = get_params(line_name, ss = ss, sp = sp)
    baseline_folder = get_output_subfolder(output_folder_path, *base_params)
    baseline_file = os.path.join(baseline_folder, "trips_details_observations_df_new.csv")
    # check if file exists
    if not os.path.exists(baseline_file):
        print('Baseline file not found:', baseline_file)
        return()
    # Load the baseline data
    baseline_df = pd.read_csv(baseline_file)
    baseline_dict = {}
    # Get the travel time for each passenger
    for index, row in baseline_df.iterrows():
        id = row['id']
        baseline_dict[id] = {}
        baseline_dict[id]['wait_before_boarding'] = row['wait_before_boarding']
        baseline_dict[id]['onboard_time'] = row['onboard_time']
        baseline_dict[id]['transfer_time'] = row['transfer_time']
        baseline_dict[id]['total_time'] = row['wait_before_boarding'] + row['onboard_time'] + row['transfer_time']
        baseline_dict[id]['nbr_transfers'] = row['nbr_transfers']
    baseline_data = [baseline_dict[id]['total_time'] for id in baseline_dict.keys()]
    baseline_p5 = np.percentile(baseline_data, 5)
    baseline_p95 = np.percentile(baseline_data, 95)
    p5 = {}
    p95 = {}
    travel_times_changes ={}
    if is_particular_case:
        print('Algo params:',len(algo_params), algo_params)
    for i, params in enumerate(algo_params):
        sim_folder = get_output_subfolder(output_folder_path, *params)
        sim_file = os.path.join(sim_folder, "trips_details_observations_df_new.csv")
        # check if file exists
        if not os.path.exists(sim_file):
            print('Simulation file not found:', sim_file)
            continue
        # Load the simulation data
        group_index = i // 3  # Group index based on the 6 groups specified
        if is_particular_case:
            key = f"{sub_labels[i % 3]}"
        else:
            key = f"{group_labels[group_index]} {sub_labels[i % 3]}"
        travel_times_changes[key] = {}
        sim_df = pd.read_csv(sim_file)
        sim_dict = {}
        # Get the travel time for each passenger
        for index, row in sim_df.iterrows():
            id = row['id']
            sim_dict[id] = {}
            sim_dict[id]['wait_before_boarding'] = row['wait_before_boarding']
            sim_dict[id]['onboard_time'] = row['onboard_time']
            sim_dict[id]['transfer_time'] = row['transfer_time']
            sim_dict[id]['total_time'] = row['wait_before_boarding'] + row['onboard_time'] + row['transfer_time']
            sim_dict[id]['nbr_transfers'] = row['nbr_transfers']
        # Calculate the change in travel time for each passenger    
        for id in sim_dict.keys():
            travel_times_changes[key][id] = (sim_dict[id]['wait_before_boarding'] - baseline_dict[id]['wait_before_boarding'],
                                             sim_dict[id]['onboard_time'] - baseline_dict[id]['onboard_time'],
                                             sim_dict[id]['transfer_time'] - baseline_dict[id]['transfer_time'],
                                             sim_dict[id]['total_time'] - baseline_dict[id]['total_time'],
                                             sim_dict[id]['nbr_transfers'])
        temp_data = [sim_dict[id]['total_time'] for id in sim_dict.keys()]
        p5[key] = np.percentile(temp_data, 5)
        p95[key] = np.percentile(temp_data, 95)
    
    # Compute p-values 
    compute_p_values_between_algorithms(travel_times_changes,
                                        label_prefix="All passengers",
                                        verbose=True)
    input()
    # Define consistent colors for each algorithm across groups
    algorithm_colors = get_algorithm_colors(greyscale = False)
    
    # Plotting 
    ### 1st plot: Violin plots
    fig, ax = plt.subplots(figsize=figsize)
    positions = []
    data = []
    q5_values_simple = []
    q95_values_simple = []
    group_ticks = []  # One tick per main group
    color_map = []  # Track colors to apply to each box
    group_tick_labels = []  # Track labels for main groups
    pos = 1
    all_labels = []
    for i, group in enumerate(group_labels):
        group_ticks.append(pos + 0.7)
        group_tick_labels.append(group)
        # Sub-groups for algorithms
        label = group_labels_short[i]
        for j, sub_label in enumerate(sub_labels):
            key = f"{group} {sub_label}"
            if is_particular_case:
                key = f"{sub_label}"
            if key in travel_times_changes:
                q5_values_simple.append(p5[key])
                q95_values_simple.append(p95[key])
                sub_label = sub_labels[j]
                all_labels.append((label, sub_label))
                if is_particular_case:
                    if i == 0:  # All passengers
                        data.append([change[3]/60 for change in travel_times_changes[key].values()])
                    elif i == 1:  # Passengers without transfers
                        data.append([change[3]/60 for change in travel_times_changes[key].values() if change[4] == 0])
                    else: # Passengers with transfers
                        data.append([change[3]/60 for change in travel_times_changes[key].values() if change[4] > 0])
                else:
                    if transfers == -1: # All passengers
                        data.append([change[3]/60 for change in travel_times_changes[key].values()])
                    elif transfers == 0:
                        data.append([change[3]/60 for change in travel_times_changes[key].values() if change[4] == 0])
                    else:
                        data.append([change[3]/60 for change in travel_times_changes[key].values() if change[4] > 0])
                color_map.append(algorithm_colors[sub_label])  # Consistent color per algorithm
                positions.append(pos)
                pos += 0.7
        pos += 0.7  # Add space between main groups

    # Plot violin plots
    vp = ax.violinplot(data, positions=positions, showmeans=False, showmedians=False, showextrema=False)

    # Apply consistent colors for vp
    for patch, color in zip(vp['bodies'], color_map):
        # No transparency to patch 
        patch.set_alpha(0.9)
        patch.set_facecolor(color)

    # Compute quartiles
    q5_values = [np.percentile(d, 5) for d in data]
    q95_values = [np.percentile(d, 95) for d in data]
    for i, pos in enumerate(positions):
        # Extract violin body path to get its width
        body = vp['bodies'][i]
        path = body.get_paths()[0]
        verts = path.vertices  # Nx2 array of [x, y] points
        x_min, x_max = verts[:, 0].min(), verts[:, 0].max()
        # Now use this width for the hlines
        ax.hlines(np.median(data[i]), x_min, x_max, colors=median_color, linestyle="-", linewidth=2)
        ax.hlines(np.mean(data[i]), x_min, x_max, colors=mean_color, linestyle="--", linewidth=2)
        # Annotate values
        ax.text(x_max, np.median(data[i]), f'{np.median(data[i]):.1f}',
                ha='left', va='bottom', fontsize=fontsize-4, color=median_color)
        ax.text(x_max, np.mean(data[i]), f'{np.mean(data[i]):.1f}',
                ha='left', va='top', fontsize=fontsize-4, color=mean_color, zorder=15)  
        # Add vertical line between percentiles
        ax.vlines(pos, q5_values[i], q95_values[i], colors=percentile_color, linestyle="dotted", linewidth=2, zorder = 1)

    # Set ylim for first y-axis
    if len(q5_values) > 10:
        y_min = q5_values[10] - 5
    else: 
        y_min = min([min(group) for group in data]) * 0.7
    ax.set_ylim(-40, 20)  # Set y-limit for better visibility
    ax.set_ylabel("Change in travel times compared\n to baseline (minutes)", fontsize=fontsize)
    ax.tick_params(axis='y', which='major', labelsize=14, labelleft=True, labelright=False, left=True, right=False)
    ax.set_xticks(group_ticks)
    ax.set_xticklabels(group_tick_labels, fontsize=fontsize)

    #Set title
    all_lines_string = get_line_str(network_style, line_name)
    titles= {}
    titles[-1] = f"Change in travel times for\nall passengers for {all_lines_string}"
    titles[0] = f"Change in travel times for passengers\nwithout transfers for {all_lines_string}"
    titles[1] = f"Change in travel times for passengers\nwith transfers for {all_lines_string}"
    if is_particular_case:
        add = ''
        if sp is None:
            sp = False
        if ss is None:
            ss = False
        # Tactics addendum
        if ss and sp:
            name = 'Hold, Speedup&\nSkip-Stop'
            add += '_SPSS' # Skip stop speed up, and hold
        elif ss:
            name = 'Hold&\nSkip-Stop'
            add += '_SS' # Skip stop and hold
        elif sp:
            name = 'Hold&\nSpeedup'
            add += '_SP' # Speed up and hold
        else:
            name = 'Hold'
            add += '_H' # Hold
        title = f'Travel time variations for all {all_lines_string}'
        ax.set_title(title, fontsize=fontsize + 2)
    else:
        ax.set_title(titles[transfers], fontsize=fontsize + 2)
    plt.tight_layout()

    # Add legend for algorithm colors with bold font
    legend_patches = [mlines.Line2D([0], [0], color=color, lw=7, label=label)
                      for label, color in algorithm_colors.items() if label in sub_labels]
    
    # Add mean, median, and missed transfer line entries to the legend
    mean_line = mlines.Line2D([0], [0], color=mean_color, linestyle='--', linewidth=2, label='Mean')
    median_line = mlines.Line2D([0], [0], color=median_color, linestyle='-', linewidth=2, label='Median')
    legend_patches.extend([mean_line, median_line])

    # Add percentile lines to the legend (5% and 95%)
    percentile_line = mlines.Line2D([0], [0], color=percentile_color, linestyle='dotted', linewidth=2, label='5-95%')
    legend_patches.append(percentile_line)
    
    # Optimize legend position and style
    ax.legend(handles=legend_patches, loc='lower left', fontsize=fontsize-2, title_fontsize=fontsize,
             framealpha=0.9, shadow=True, ncol = 3, frameon=True)

    plt.tight_layout()
    line_string = get_image_name(network_style, line_name)
    if transfers == -1:
        addendum = 'all_passengers'
    elif transfers == 0:
        addendum = 'no_transfers'
    else:
        addendum = 'transfers_only'
    if is_particular_case:
        addendum = add
    figure_name = f"{line_string}_travel_time_change_distribution" +addendum+".png"
    plt.savefig(os.path.join(base_folder, instance_name, figure_name), dpi = 300, bbox_inches='tight')
    # plt.show()
    plt.close()
    # Save percentiles under the same name in a csv file
    # round to 2 decimal places
    q5_values = [round(q, 2) for q in q5_values]
    q95_values = [round(q, 2) for q in q95_values]
    
    ### Calculate p5 and p95 variation in percent
    q5_values_simple = [round((q5 - baseline_p5) / baseline_p5 * 100, 2) for q5 in q5_values_simple]
    q95_values_simple = [round((q95 - baseline_p95) / baseline_p95 * 100, 2) for q95 in q95_values_simple]

    # Create a DataFrame for the percentiles
    percentiles = pd.DataFrame({'q5%var': q5_values_simple, 'q95%var': q95_values_simple, 'algorithm': [label[1] for label in all_labels], 'tactics': [label[0] for label in all_labels]})
    # Add labels to the percentiles
    percentiles.to_csv(os.path.join(base_folder, instance_name, f"{line_string}_travel_time_change_distribution" + addendum +"_percentiles.csv"), index=False)
    return()

def get_bus_trip_ids(route_name, requests_file_path):
    """
    Get the bus trip ids for a given route.
    """
    bus_trip_ids = []
    trips_file = os.path.join(requests_file_path, 'trips.txt')
    with open(trips_file, 'r') as trips:
        reader = csv.reader(trips, delimiter=',')
        # Skip the header
        next(reader)
        for row in reader:
            # Check if the route_id matches the given route_name
            if str(row[0])[:-1] == route_name:
                bus_trip_ids.append(str(row[2]))
    return bus_trip_ids

def compute_p_values_between_algorithms(travel_times_changes,
                                        label_prefix="All passengers",
                                        verbose=True):
    """
    Computes the paired t-test and Wilcoxon test p-values comparing Algorithm R and PI
    using per-passenger total travel time changes (in minutes).
    
    Only uses the "All passengers" case (i.e., label_prefix).
    
    Parameters:
    - travel_times_changes: dict of {label: {id: (Δwait, Δonboard, Δtransfer, Δtotal, nbr_transfers)}}
    - label_prefix: prefix used to construct the keys in the dictionary (e.g., 'Hold, Speedup&\nSkip-Stop')
    - verbose: whether to print results

    Returns:
    - Dictionary with t-test and Wilcoxon test results
    """
    key_r = "Regret"
    key_pi = "Perfect Info"
    if key_r not in travel_times_changes or key_pi not in travel_times_changes:
        if key_r not in travel_times_changes:
            print(f"Missing data for keys: {key_r}")
        if key_pi not in travel_times_changes:
            print(f"Missing data for keys: {key_pi}")
        return

    delta_r = travel_times_changes[key_r]
    delta_pi = travel_times_changes[key_pi]

    # Keep only IDs present in both
    common_ids = set(delta_r.keys()) & set(delta_pi.keys())

    delta_r_values = [delta_r[i][3] / 60 for i in common_ids]  # Total time change in minutes
    delta_pi_values = [delta_pi[i][3] / 60 for i in common_ids]

    # Paired t-test
    t_stat, p_val_t = ttest_rel(delta_r_values, delta_pi_values)

    # Wilcoxon signed-rank test
    try:
        w_stat, p_val_w = wilcoxon(delta_r_values, delta_pi_values)
    except ValueError as e:
        p_val_w = None
        if verbose:
            print(f"Wilcoxon test failed: {e}")

    if verbose:
        print("=== P-value comparison between Algorithm R and PI ===")
        print(f"Number of passengers: {len(common_ids)}")
        print(f"Paired t-test p-value: {p_val_t:.4e}")
        if p_val_w is not None:
            print(f"Wilcoxon signed-rank p-value: {p_val_w:.4e}")
        print("====================================")
    return

def plot_single_line_comparisons(instance_name,
                            requests_file_path,
                            algo,
                            ss = False, 
                            sp = False,
                            line_name="70E",
                            base_folder="output/fixed_line/gtfs",
                            network_style = ''):
    """ 
    Compare the passenger travel times across different algorithms and settings. Plot a single figure comparing all lines
    to network wide optimization. 
    The figure contains 3 boxplots for each single line : 
    - Baseline (for passengers that boarder that line)
    - Single line optimization (for passengers that boarder that line)
    - Network wide optimization (for passengers that boarder that line)

    Parameters:
    - instance_name: Name of the test instance folder
    - requests_file_path: Path to the requests file
    - algo: Algorithm to use for the comparison (0 = Baseline, 1 = Deterministic, 2 = Regret, 3 = Perfect Information)
    - ss: Whether to use skip-stop (True/False)
    - sp: Whether to use speedup (True/False)
    - line_name: Name of the line to compare (e.g., "70E")
    - base_folder: Base folder for the output files
    - network_style: Style of the network (e.g., "grid", "radial", etc.)
    """
    single_lines_data = {}
    route_names = list(set([route_id[:-1] for route_id in line_name]))
    route_names = sorted(route_names)
    print('Route names:', route_names)
    for route_name in route_names:
        print('Route name:', route_name)
        # Get params
        base_params, algo_params = get_params(route_name, algo, ss, sp)
        # Prepare to collect output data for each comparison
        single_line_addendum = '_SINGLE' + route_name
        instance_name_single = instance_name + single_line_addendum
        output_folder_path = os.path.join(base_folder, instance_name_single)
        
        # Prepare to collect output data for each comparison
        group_data = {}
        missed_transfer_data = {}

        # Get trips for this route
        bus_trip_ids = get_bus_trip_ids(route_name, requests_file_path)
        ## Get the total number of transfers
        transfers, total_transfers, request_legs = get_request_transfer_data(requests_file_path=requests_file_path, bus_trip_ids=bus_trip_ids)

        # Define the labels for main groups
        group_labels = ["Baseline", 'Single line\noptimization', 'Network-wide\noptimization']

        # Get data for Baseline (no tactics)
        baseline_folder = get_output_subfolder(output_folder_path, *base_params)
        if os.path.exists(os.path.join(baseline_folder, 'trips_observations_df.csv')):
            number_of_completed_transfers_notactics, percentage_missed_transfers_notactics, transfer_times_notactics, total_times_notactics = get_transfer_and_travel_time_stats(baseline_folder, transfers, total_transfers, request_legs)
        # Ensure the baseline file exists
        baseline_file = os.path.join(baseline_folder, "trips_details_observations_df_new.csv")
        if not os.path.exists(baseline_file):
            raise FileNotFoundError(f"Baseline file not found: {baseline_file}")
        group_data["Baseline"] = [time / 60 for time in total_times_notactics]
        missed_transfer_data["Baseline"] = np.mean(transfer_times_notactics)/60

        # Get data for Single line optimization (algo_params)
        params = algo_params[0]
        sim_folder = get_output_subfolder(output_folder_path, *params)
        if os.path.exists(os.path.join(sim_folder, 'trips_observations_df.csv')):
            number_of_completed_transfers_key, percentage_missed_transfers_key, transfer_times_key, total_times_key = get_transfer_and_travel_time_stats(sim_folder, transfers, total_transfers, request_legs)
        else:
            print('*** PROBLEM ***')
            print('ALGO PARAMS', params)
            print('SIM FOLDER', sim_folder)
            print('NO DATA')
            continue
        group_data["Single line\noptimization"] = [time / 60 for time in total_times_key]
        missed_transfer_data["Single line\noptimization"] = np.mean(transfer_times_key)/60

        ### Get data for network wide optimization
        base_params, algo_params = get_params(line_name, algo, ss, sp)
        output_folder_path = os.path.join(base_folder, instance_name)
        # Prepare to collect output data for each comparison
        network_wide_opt_folder = get_output_subfolder(output_folder_path, *algo_params[0])
        if os.path.exists(os.path.join(network_wide_opt_folder, 'trips_observations_df.csv')):
            number_of_completed_transfers_key, percentage_missed_transfers_key, transfer_times_key, total_times_key = get_transfer_and_travel_time_stats(network_wide_opt_folder, transfers, total_transfers, request_legs)
        else:
            print('*** PROBLEM ***')
            print('ALGO PARAMS', params)
            print('SIM FOLDER', sim_folder)
            print('NO DATA')
            continue
        group_data["Network-wide\noptimization"] = [time / 60 for time in total_times_key]
        missed_transfer_data["Network-wide\noptimization"] = np.mean(transfer_times_key)/60

        # Save data to dictionary
        single_lines_data[route_name] = {}
        single_lines_data[route_name]['group_data'] = group_data
        single_lines_data[route_name]['missed_transfer_data'] = missed_transfer_data
    
    # Plot these into a single figure
    # Define consistent colors for algorthms
    algorithm_colors = get_algorithm_colors(greyscale=False)
    colors = {}
    if algo == 0:
        colors['Network-wide\noptimization'] = algorithm_colors['No tactics']
        add = ' (B)'
    elif algo == 1:
        colors['Network-wide\noptimization'] = algorithm_colors['Deterministic']
        add = ' (D)'
    elif algo == 2:
        colors['Network-wide\noptimization'] = algorithm_colors['Regret']
        add = ' (R)'
    elif algo == 3:
        colors['Network-wide\noptimization'] = algorithm_colors['Perfect Info']
        add = ' (PI)'
    colors['Baseline'] = algorithm_colors['No tactics']
    # Get a paler version of the 'Network-wide\noptimization' color
    colors["Single line\noptimization"] = lighten_color(colors['Network-wide\noptimization'], 0.5)
    
    # Get data for boxplots: Iterate over lines, and then over groups 
    positions = []
    data = []
    group_ticks = []  # One tick per main group
    color_map = []  # Track colors to apply to each box
    group_tick_labels = []  # Track labels for main groups
    # Prepare data for boxplot with spacing between groups
    pos = 1
    missed_transfer_percentages = []  # Track missed transfer percentage for each boxplot
    for i, route_name in enumerate(route_names):
        group_data = single_lines_data[route_name]['group_data']
        missed_transfer_data = single_lines_data[route_name]['missed_transfer_data']
        group_ticks.append(pos + 1)
        group_tick_labels.append(route_name)
        # Iterate over groups
        for group in group_labels:
            if group in group_data:
                data.append(group_data[group])
                missed_transfer_percentages.append(missed_transfer_data[group])
                color_map.append(colors[group])  # Default color if missing
                positions.append(pos)
                pos += 0.7
        pos += 0.7  # Add space between main groups
    
    # Get original legend patches
    # In colors remove 'Network-wide\noptimization' and replace it with the new label ('Network-wide\noptimization' + add)
    colors['Network-wide\noptimization' + add] = colors.pop('Network-wide\noptimization')
    legend_patches = [mlines.Line2D([0], [0], color=color, lw=7, label=label)
                      for label, color in colors.items()]
    # Get title
    all_lines_string = get_line_str(network_style, line_name)
    title = "Comparison of passenger travel and transfer times\nfor single line optimization versus network-wide optimization\nfor "+ all_lines_string
    
    # Get image name
    # Algorithm addendum
    add = ''
    if algo == 0:
        add += 'O' # Offline    
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
    figure_name = get_image_name(network_style, line_name)
    figure_name = f"{figure_name}_network_vs_single_"+add+"comparison.png"
    complete_figure_name = os.path.join(base_folder, instance_name, figure_name)
    
    # Plot figure
    plot_boxplots(data = data,
                  missed_transfer_percentages = missed_transfer_percentages,
                  positions = positions,
                  group_ticks = group_ticks,  # One tick per main group
                  group_tick_labels = group_tick_labels,  # Track labels for main groups
                  color_map = color_map,  # Track colors to apply to each box
                  transfer_type = 2, 
                  title = title,
                  complete_figure_name = complete_figure_name,
                  legend_patches = legend_patches,
                  xlabel = 'Single line number',
                  )
    print('Figure saved to', complete_figure_name)
    return()

if __name__ == "__main__":
    # Define the test instance name
    route_dict = get_route_dictionary()
    data_name = 'gtfs2019-11-25_EveningRushHour'
    single_lines_dict = {}
    for network_style in route_dict:
        single_lines_dict[network_style] = ['']
        route_names = list(set([route_id[:-1] for route_id in route_dict[network_style]]))
        if network_style != 'all' and network_style != 'transfer_hubs':
            for route_name in route_names:
                single_lines_dict[network_style].append('_SINGLE' + route_name)
        single_lines_dict[network_style] = ['']
        print('Getting stats for network style:', network_style)
        requests_file_path = os.path.join('data','fixed_line','gtfs','gtfs2019-11-25-EveningRushHour'+network_style)
        route_ids_list = route_dict[network_style]
        instance_name = data_name + '_' + network_style
        for algo in [2]:
            for ss in [True, False]:
                for sp in [True, False]:
                    try:
                        plot_single_line_comparisons(instance_name,
                                                    requests_file_path = requests_file_path,
                                                    algo = algo,
                                                    ss = ss,
                                                    sp = sp,
                                                    line_name = route_ids_list,
                                                    network_style = network_style)
                    except Exception as e:
                        traceback.print_exc()
                        print('Could not plot single line comparisons for:', network_style)

        for ss in [False, True]:
            for sp in [False, True]:
                try:
                    plot_travel_time_change_distribution(instance_name, route_ids_list, network_style = network_style, ss = ss, sp = sp)
                except Exception as e:
                    traceback.print_exc()
                    input('PROBLEM')

        for transfer_type in [2]:
            try:
                ## Run the function to compare and plot passenger travel times across different parameters
                plot_network_comparisons(instance_name, requests_file_path=requests_file_path, line_name = route_ids_list, transfer_type = transfer_type, network_style = network_style)
            except Exception as e:
                traceback.print_exc()

        for single_line_addendum in single_lines_dict[network_style]:
            instance_name = data_name+single_line_addendum+'_'+network_style
            for transfers in [-1, 0, 1]:
                try:
                    plot_travel_time_change_distribution(instance_name, route_ids_list, network_style = network_style, transfers = transfers)
                except Exception as e:
                    traceback.print_exc()
                    print('Could not plot travel time change distribution for:', network_style)