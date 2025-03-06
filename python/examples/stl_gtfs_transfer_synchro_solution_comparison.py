import pandas as pd
import csv
import os
import matplotlib.pyplot as plt
from stl_gtfs_transfer_synchro import get_output_subfolder
import matplotlib.lines as mlines
from ast import literal_eval
import sys
import numpy as np
from fixed_line.stl_network_analysis import get_route_dictionary
import traceback

sys.path.append(os.path.abspath('../..'))
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
sys.path.append(r"/home/kollau/Recherche_Kolcheva/Simulator/python/examples")

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

def get_request_transfer_data(requests_file_path):
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

def get_transfer_stats(output_folder_path, transfers, total_transfers, request_legs, no_tactics_boarding_times):
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
    i = 0
    row_index = 0
    while i < len(request_ids):
        request_id = request_ids[i]
        request_legs_list = request_legs[request_id]
        if row_index >= len(trips_observations_df):
            i+=1
            not_completed_requests.append(request_id)
            continue
        row = trips_observations_df.iloc[row_index]
        row_request_id = row['ID']
        while row_request_id != request_id and i < len(request_ids):
            not_completed_requests.append(request_id)
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
    print('Total requests:', len(request_ids))
    print('Counter missed transfers', number_of_missed_transfers)
    print('Counter completed transfers', number_of_completed_transfers)
    print('Total counted transfers', number_of_missed_transfers + number_of_completed_transfers)
    print('Total transfers in requests.csv file', total_transfers)
    if total_transfers != number_of_missed_transfers + number_of_completed_transfers:
        print('Error in counting transfers')
    percentage_missed_transfers = (number_of_missed_transfers/total_transfers)*100 if total_transfers > 0 else 0
    return(number_of_completed_transfers, percentage_missed_transfers)

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

def get_travel_time_stats(output_folder_path, transfers):
    total_times = []
    transfer_times = []
    # Get total travel time for all passengers (not only transfer passengers)
    create_trip_details_df(output_folder_path=output_folder_path)
    trips_details_observations_df = pd.read_csv(os.path.join(output_folder_path, 'trips_details_observations_df_new.csv'))
    for index, row in trips_details_observations_df.iterrows():
        total_time = row['wait_before_boarding'] + row['onboard_time'] + row['transfer_time']
        # if row['id'] in not_completed_requests:
        #     total_time += 3600 # 30 minutes penalty for not completing the trip
        total_times.append(total_time)
        if row['id'] in transfers.keys():
            transfer_times.append(row['transfer_time'])
    return(total_times, transfer_times)

def create_trip_details_df(output_folder_path):
    nbr_passengers_no_bus = 0
    observations_df = pd.read_csv(os.path.join(output_folder_path, 'trips_observations_df.csv'))
    observations_details = []
    id_col = "ID"
    status_col = 'Status'
    time_col = 'Time'
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
            time_penalty = (1+len(literal_eval(next_legs)))*1800
            transfer_penalty = len(literal_eval(next_legs))*1800
            wait_before_boarding = 0
            onboard_time = time_penalty
            transfer_time = transfer_penalty
            # print('ready row is empty, passenger did not get a bus at all')
            # print('Passenger id:', id)
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
                    time_penalty = (1+len(literal_eval(next_legs)))*1800 # 30 minutes penalty for each leg (including current leg)
                    transfer_penalty = len(literal_eval(next_legs))*1800
                    wait_before_boarding += 0
                    onboard_time += time_penalty
                    transfer_time += transfer_penalty
                else:
                    #get remaining legs
                    next_legs = last_row['Next legs'].iat[0]
                    time_penalty = (len(literal_eval(next_legs)))*1800
                    transfer_penalty =  (len(literal_eval(next_legs)))*1800
                    # get last row status
                    last_row_status = last_row[status_col].iat[0]
                    if last_row_status == 'PassengersStatus.ONBOARD':# current leg has started but we don't know how long it was (this could be improved if we know when the bus trip arrived at the stop.)
                        time_penalty += 1800
                    elif last_row_status in ['PassengersStatus.READY', 'PassengersStatus.RELEASE']: # current leg has not started AND it is a transfer (not the fist leg)
                        transfer_penalty += 1800
                        time_penalty += 1800
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
    observations_details_df = pd.DataFrame(observations_details)
    observations_details_df.to_csv(os.path.join(output_folder_path, 'trips_details_observations_df_new.csv'), index=False)
    print('Number of passengers that did not get a bus:', nbr_passengers_no_bus)
    return()

def get_transfer_and_travel_time_stats(output_folder_path, transfers, total_transfers, request_legs, no_tactics_boarding_times = None):
    number_of_completed_transfers, percentage_missed_transfers = get_transfer_stats(output_folder_path, transfers, total_transfers, request_legs, no_tactics_boarding_times)
    total_times, transfer_times = get_travel_time_stats(output_folder_path, transfers)
    return(number_of_completed_transfers, percentage_missed_transfers, transfer_times, total_times)

def plot_single_line_comparisons(instance_name,
                                 requests_file_path,
                                 line_name="70E",
                                 base_folder="output/fixed_line/gtfs",
                                 transfer_type = 0,
                                 network_style = ''):
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
    group_labels = ["No tactics", "Hold", "Hold&\nSpeedup", "Hold&\nSkip-Stop", "Hold, Speedup&\nSkip-Stop"]
    sub_labels = ["Deterministic", "Regret", "Perfect Info"]

    # Initialize group_data with No tactics baseline
    baseline_folder = get_output_subfolder(output_folder_path, *base_params)
    baseline_file = os.path.join(baseline_folder, "trips_details_observations_df.csv")
    if os.path.exists(os.path.join(baseline_folder, 'trips_observations_df.csv')):
        no_tactics_boarding_times = get_no_tactics_boarding_times(get_observations_df(baseline_folder, transfers), transfers)
        number_of_completed_transfers_notactics, percentage_missed_transfers_notactics, transfer_times_notactics, total_times_notactics = get_transfer_and_travel_time_stats(baseline_folder, transfers, total_transfers, request_legs, no_tactics_boarding_times)
     # Ensure the baseline file exists
    if not os.path.exists(baseline_file):
        raise FileNotFoundError(f"Baseline file not found: {baseline_file}")
    group_data["No tactics"] = [time / 60 for time in total_times_notactics]
    if transfer_type == 0:
        missed_transfer_data["No tactics"] = percentage_missed_transfers_notactics #output_data_baseline["missed_transfer_percentage_sim1"] 
    elif transfer_type == 1:
        missed_transfer_data["No tactics"] = number_of_completed_transfers_notactics #output_data_baseline["total_transfers_sim1"]
    else:
        missed_transfer_data["No tactics"] = np.mean(transfer_times_notactics)/60

    # Generate comparisons for algo_params
    for i, params in enumerate(algo_params):
        sim_folder = get_output_subfolder(output_folder_path, *params)
        if os.path.exists(os.path.join(sim_folder, 'trips_observations_df.csv')):
            number_of_completed_transfers_key, percentage_missed_transfers_key, transfer_times_key, total_times_key = get_transfer_and_travel_time_stats(sim_folder, transfers, total_transfers, request_legs)
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
    algorithm_colors = get_algorithm_colors()
    mean_color = "black"
    median_color = "black"
    transfers_color = 'blue'#"#377eb8"#'dodgerblue'
    transfers_marker = "o-"
    transfers_marker_size = 8
    if transfer_type == 0:
        transfers_label = "Missed Transfers (%)"
    elif transfer_type == 1:
        transfers_label = "Number of successful\ntransfers"
    else:
        transfers_label = "Mean transfer time\n(in minutes)"
    fontsize = 16

    # Plotting
    fig, ax = plt.subplots(figsize=(12, 6))
    ax2 = ax.twinx()  # Create secondary y-axis for missed transfer percentages
    positions = []
    data = []
    group_ticks = []  # One tick per main group
    color_map = []  # Track colors to apply to each box
    group_tick_labels = []  # Track labels for main groups

    # Prepare data for boxplot with spacing between groups
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

    # Boxplot with custom colors, mean line, and labels
    bp = ax.boxplot(data, positions=positions, patch_artist=True, showmeans=True,
                    meanline=True, meanprops=dict(color=mean_color, linestyle='--', linewidth=2),
                    medianprops=dict(color=median_color, linewidth=2), showfliers=False)
    
    for patch, color in zip(bp['boxes'], color_map):  # Apply consistent colors
        patch.set_facecolor(color)

    for i, pos in enumerate(positions):
        median = bp['medians'][i]
        mean = bp['means'][i]

        # Get the y-values for median and mean
        median_value = median.get_ydata()[0]
        mean_value = mean.get_ydata()[0]

        # Annotate the median value above the median line
        ax.text(pos, median_value-0.5, f'{median_value:.1f}', ha='center', va='top', fontsize=fontsize-2, color=median_color)

        # Annotate the mean value below the mean line
        ax.text(pos, mean_value, f'{mean_value:.1f}', ha='center', va='bottom', fontsize=fontsize-2, color=mean_color)
    # Set ylim for first y-axis
    ax.set_ylim(0, max([max(group) for group in data]) * 0.7)  # Set y-limit for better visibility
    # ax.set_ylim(0, max([max(group) for group in data]) * 1)  # Set y-limit for better visibility
    ax.set_ylim(0, 100)  # Set y-limit for better visibility

    # Plot missed transfer percentages as points on the secondary y-axis
    ax2.plot(positions, missed_transfer_data.values(), transfers_marker, color=transfers_color, label=transfers_label, markersize=transfers_marker_size)
    # Add values as text annotations above the points
    for i, value in enumerate(missed_transfer_percentages):
        ax2.text(positions[i]-0.05, value+0.1, f'{value:.1f}', ha='center', va='bottom', fontsize=fontsize-2, color=transfers_color)
    ax2.set_ylim(min(missed_transfer_data.values())*0.7, max(missed_transfer_data.values()) * 1.2)  # Set y-limit for better visibility
    ax2.set_ylim(6, max(missed_transfer_data.values()) * 1.2)  # Set y-limit for better visibility
    # Set tick label color for the secondary y-axis

    if transfer_type == 0:
        ax2.set_ylabel("Missed Transfers (%)", fontsize=fontsize, color=transfers_color)
    elif transfer_type == 1:
        ax2.set_ylabel("Number of transfers", fontsize=fontsize, color=transfers_color)
    else:
        ax2.set_ylabel("Mean transfer time\n(in minutes)", fontsize=fontsize, color=transfers_color)
    ax2.tick_params(axis='y', which='major', labelsize=fontsize-2, labelleft=False, labelright=True, left=False, right=True, color=transfers_color, labelcolor=transfers_color)

    # Add group x-ticks and remove individual sub-label x-ticks
    ax.set_xticks(group_ticks)
    ax.set_xticklabels(group_tick_labels, fontsize=16)

    # Set primary y-axis parameters, remove last character from line_name for title
    all_lines_string = get_line_str(line_name, network_style)
    ax.set_title(f"Comparison of passenger travel and transfer times\nfor {all_lines_string}", fontsize=18)
    ax.set_ylabel("Travel Time (minutes)", fontsize=fontsize)
    ax.tick_params(axis='y', which='major', labelsize=fontsize-2, labelleft=True, labelright=False, left=True, right=False)
    
    # Add legend for algorithm colors with bold font
    legend_patches = [mlines.Line2D([0], [0], color=color, lw=7, label=label)
                      for label, color in algorithm_colors.items() if label in sub_labels + ["No tactics"]]
    
    # Add mean, median, and missed transfer line entries to the legend
    mean_line = mlines.Line2D([0], [0], color=mean_color, linestyle='--', linewidth=2, label='Mean')
    median_line = mlines.Line2D([0], [0], color=median_color, linestyle='-', linewidth=2, label='Median')
    missed_transfers_line = mlines.Line2D([0], [0], color=transfers_color, lw=2, label=transfers_label)
    legend_patches.extend([mean_line, median_line, missed_transfers_line])
    # ordered_legend_patches = [legend_patches[0], legend_patches[2], legend_patches[4], legend_patches[6], legend_patches[1], legend_patches[3], legend_patches[5]]

    # Optimize legend position and style
    ax.legend(handles=legend_patches, loc='upper left', fontsize=fontsize-2, title_fontsize=fontsize,
             framealpha=0.9, shadow=True, ncol = 4)

    plt.tight_layout()
    if transfer_type == 0:
        addendum = 'pecentage_missed_transfers'
    elif transfer_type == 1:
        addendum = 'number_transfers'
    else:
        addendum = 'mean_transfer_time'
    figure_name = get_image_name(network_style, line_name)
    figure_name = f"{figure_name}_travel_time_and_"+addendum+"_comparison.png"
    plt.savefig(os.path.join(base_folder, instance_name, figure_name))
    # plt.show()
    return()

def get_algorithm_colors():
    algorithm_colors = {
        "No tactics": "grey",
        "Optimal\ntravel paths": "#f781bf",
        "Deterministic": '#4daf4a',#"#377eb8",
        "Regret": "#ff7f00",
        "Perfect Info": '#f781bf'
    }
    return algorithm_colors

def get_params(line_name):
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
    all_lines_string = lines_str_dict[network_style]
    return(all_lines_string)

def plot_travel_time_change_distribution(instance_name, line_name, base_folder="output/fixed_line/gtfs", network_style = '', transfers = 0):
    """
    This function plots the distribution of travel time changes for passengers. 
    It plots 3 different graphs: 
    (1) Violin plots
        X-axis: Test cases (Baseline, Hold-D, Hold-R, ..., All tactics-PI)
        Y-axis: Change in total passenger travel time (compared to the baseline)
        
    (2) Violin plots for passengers with 0, 1 or 2 transfers (3 subplots, one above the other)
        X-axis: Test cases (Baseline, Hold-D, Hold-R, ..., All tactics-PI)
        Y-axis: Change in total passenger travel time (compared to the baseline)

    (3) 
        """

    output_folder_path = os.path.join(base_folder, instance_name)
    
    # Define the labels for main groups
    group_labels = ["Hold", "Hold&\nSpeedup", "Hold&\nSkip-Stop", "Hold, Speedup&\nSkip-Stop"]
    sub_labels = ["Deterministic", "Regret", "Perfect Info"]

    base_params, algo_params = get_params(line_name)
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
    
    travel_times_changes ={}
    for i, params in enumerate(algo_params):
        sim_folder = get_output_subfolder(output_folder_path, *params)
        sim_file = os.path.join(sim_folder, "trips_details_observations_df_new.csv")
        # check if file exists
        if not os.path.exists(sim_file):
            print('Simulation file not found:', sim_file)
            continue
        # Load the simulation data
        group_index = i // 3  # Group index based on the 6 groups specified
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
    
    # Define consistent colors for each algorithm across groups
    algorithm_colors = get_algorithm_colors()
    mean_color = "red"
    median_color = "black"
    percentile_color = median_color
    fontsize = 16

    # Plotting 
    ### 1st plot: Violin plots
    fig, ax = plt.subplots(figsize=(12, 6))
    positions = []
    data = []
    group_ticks = []  # One tick per main group
    color_map = []  # Track colors to apply to each box
    group_tick_labels = []  # Track labels for main groups
    # Prepare data for boxplot with spacing between groups
    pos = 1
    for i, group in enumerate(group_labels):
        # if group in travel_times_changes:
        #     data.append([change[3]/60 for change in travel_times_changes[group].values() if change[4] == 1])
        #     color_map.append(algorithm_colors.get(group, "#AEC6CF"))  # Default color if missing
        #     positions.append(pos)
        #     group_ticks.append(pos)  # Position for the x-tick label
        #     group_tick_labels.append(group)
        #     pos += 0.7
        # else:  # For groups with multiple sub-groups
        group_ticks.append(pos + 1)
        group_tick_labels.append(group)
        # Sub-groups for algorithms
        for j, sub_label in enumerate(sub_labels):
            key = f"{group} {sub_label}"
            if key in travel_times_changes:
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

    # # Plot violin plots
    vp = ax.violinplot(data, positions=positions, showmeans=False, showmedians=False, showextrema=False)

    # Apply consistent colors for vp
    for patch, color in zip(vp['bodies'], color_map):
        # No transparency to patch 
        patch.set_alpha(0.9)
        patch.set_facecolor(color)
    
    # Plot boxplots
    # bp = ax.boxplot(data, positions=positions)
    # # Apply consistent colors for bp
    # for patch, color in zip(bp['boxes'], color_map):
    #     patch.set_facecolor(color)
    #     patch.set_alpha(1)


    # Compute quartiles
    q5_values = [np.percentile(d, 5) for d in data]
    q25_values = [np.percentile(d, 25) for d in data]
    q75_values = [np.percentile(d, 75) for d in data]
    q95_values = [np.percentile(d, 95) for d in data]
    # q4_values = [np.percentile(d, 100) for d in data]
    hlines_half_length = 0.2
    # Annotate the median value above the median line
    for i, pos in enumerate(positions):
        # Extract median and mean values correctly
        mean_value = np.mean(data[i])
        median_value = np.median(data[i])
        
        # Add vertical line between percentiles
        ax.vlines(pos, q5_values[i], q95_values[i], colors=percentile_color, linestyle="dotted", linewidth=2, zorder = 1)
        # ax.hlines(q5_values[i], pos - hlines_half_length, pos + hlines_half_length, colors=percentile_color, linestyle="dotted", linewidth=2)
        # # ax.hlines(q25_values[i], pos - hlines_half_length, pos + hlines_half_length, colors=percentile_color, linestyle="dotted", linewidth=2)
        # # ax.hlines(q75_values[i], pos - hlines_half_length, pos + hlines_half_length, colors=percentile_color, linestyle="dotted", linewidth=2)
        # ax.hlines(q95_values[i], pos - hlines_half_length, pos + hlines_half_length, colors=percentile_color, linestyle="dotted", linewidth=2)

        # Annotate the median value above the median line
        ax.text(pos+0.3, median_value, f'{median_value:.1f}', ha='center', va='top', fontsize=fontsize-4, color=median_color)
        ax.scatter(pos, median_value, color=median_color, marker='s', s=40, zorder = 10)
        # ax.hlines(median_value, pos - hlines_half_length/2, pos + hlines_half_length/2, colors=median_color, linestyle="-", linewidth=2)
        
        # Annotate the mean value below the mean line
        ax.scatter(pos, mean_value, color=mean_color, marker='o', s=100)
        # ax.hlines(mean_value, pos - hlines_half_length, pos + hlines_half_length, colors=mean_color, linestyle="-", linewidth=2)
        ax.text(pos+0.3, mean_value, f'{mean_value:.1f}', ha='center', va='bottom', fontsize=fontsize-4, color=mean_color, zorder = 15)

    # Set ylim for first y-axis
    if len(q5_values) > 10:
        y_min = q5_values[10] - 5
    else: 
        y_min = min([min(group) for group in data]) * 0.7
    ax.set_ylim(y_min, 15)  # Set y-limit for better visibility
    ax.set_ylabel("Change in travel time (minutes)", fontsize=fontsize)
    ax.tick_params(axis='y', which='major', labelsize=14, labelleft=True, labelright=False, left=True, right=False)
    ax.set_xticks(group_ticks)
    ax.set_xticklabels(group_tick_labels, fontsize=fontsize)

    #Set title
    all_lines_string = get_line_str(network_style, line_name)
    titles ={}
    titles[-1] = f"Change in travel times for\nall passengers for {all_lines_string}"
    titles[0] = f"Change in travel times for passengers\nwithout transfers for {all_lines_string}"
    titles[1] = f"Change in travel times for passengers\nwith transfers for {all_lines_string}"
    ax.set_title(titles[transfers], fontsize=18)
    plt.tight_layout()

    # Add legend for algorithm colors with bold font
    legend_patches = [mlines.Line2D([0], [0], color=color, lw=7, label=label)
                      for label, color in algorithm_colors.items() if label in sub_labels]
    
    # Add mean, median, and missed transfer line entries to the legend
    mean_line = mlines.Line2D([0], [0], color=mean_color, linestyle='-', linewidth=2, label='Mean')
    median_line = mlines.Line2D([0], [0], color=median_color, linestyle='-', linewidth=2, label='Median')
    # legend_patches.extend([mean_line, median_line])

    ## Add mean and median scatters entries to legend
    mean_scatter = mlines.Line2D([0], [0], color=mean_color, marker='o', linestyle='None', label='-2.4 Mean')
    median_scatter = mlines.Line2D([0], [0], color=median_color, marker='s', linestyle='None', label='0.0 Median')
    legend_patches.extend([mean_scatter, median_scatter])

    # Add percentile lines to the legend (5% and 95%)
    percentile_line = mlines.Line2D([0], [0], color=percentile_color, linestyle='dotted', linewidth=2, label='5-95%')
    legend_patches.append(percentile_line)
    
    # Optimize legend position and style
    ax.legend(handles=legend_patches, loc='upper left', fontsize=fontsize-2, title_fontsize=fontsize,
             framealpha=0.9, shadow=True, ncol = 3, frameon=True)

    plt.tight_layout()
    line_string = get_image_name(network_style, line_name)
    if transfers == -1:
        addendum = 'all_passengers'
    elif transfers == 0:
        addendum = 'no_transfers'
    else:
        addendum = 'transfers_only'
    figure_name = f"{line_string}_travel_time_change_distribution" +addendum+".png"
    plt.savefig(os.path.join(base_folder, instance_name, figure_name))
    # plt.show()
    plt.close()
    return()

if __name__ == "__main__":
    # Define the test instance name
    instance_name = "gtfs2019-11-27_LargeInstanceAll"
    route_dict = get_route_dictionary()
    data_name = 'gtfs2019-11-25_EveningRushHour'
    for network_style in route_dict:
    # for network_style in ['151']:
        print('Getting stats for network style:', network_style)
        instance_name = data_name+'_'+network_style
        requests_file_path = os.path.join('data','fixed_line','gtfs','gtfs2019-11-25-EveningRushHour'+network_style)
        for route_ids_list in [route_dict[network_style]]:
            for transfer_type in [0,1,2]:
                try:
                    ## Run the function to compare and plot passenger travel times across different parameters for line 70E
                    plot_single_line_comparisons(instance_name, requests_file_path=requests_file_path, line_name = route_ids_list, transfer_type = transfer_type, network_style = network_style)
                except:
                    continue
            for transfers in [-1, 0, 1]:
                try:
                    plot_travel_time_change_distribution(instance_name, route_ids_list, network_style = network_style, transfers= transfers)
                except Exception as e:
                #     traceback.print_exc()
                # print('Could not plot travel time change distribution for:', network_style)
                    continue
    # Run the function to compare and plot passenger travel times across different parameters for line 70E
    # data_name = "gtfs2019-11-25_TestInstanceDurationCASPT_NEW"
    # instance_name = data_name
    # data_gtfs_name = "gtfs2019-11-25-TestInstanceDurationCASPT_NEW"
    # route_ids_list = ["17N", "151S", "26E", "42E", "56E"]
    # requests_file_path = os.path.join('data','fixed_line','gtfs',data_gtfs_name)
    # for transfer_type in [0,1,2]:
    #     plot_single_line_comparisons(instance_name, requests_file_path=requests_file_path, line_name = route_ids_list, transfer_type = transfer_type, network_style='')