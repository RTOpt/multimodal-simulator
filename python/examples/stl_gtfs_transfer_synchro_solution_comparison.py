import pandas as pd
import csv
import os
import matplotlib.pyplot as plt
from stl_gtfs_transfer_synchro import get_output_subfolder
import matplotlib.lines as mlines
from ast import literal_eval
import sys
import numpy as np
from stl_gtfs_parameter_parser_and_test_file_generator import get_route_dictionary


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

def get_transfer_stats(output_folder_path, transfers, total_transfers, request_legs):
    """This function retrieves data on the number of completed and missed transfers, as well as the percentage of missed transfers
    from the results of a simulation run.
    In order to retrieve missed transfers we compare the vehicles used in the simulation for each leg of each request with the vehicles
    that were used in the optimal solution for the same leg. If the vehicles are different, we consider the transfer as missed.
    This is true because the original assigned vehicle is the best possible option for the passenger to make the transfer. If a passenger misses that vehicle, 
    they are re-assigned to the next vehicle on the same line"""
    trips_observations_df = pd.read_csv(os.path.join(output_folder_path, 'trips_observations_df.csv'))
    number_of_completed_transfers = 0
    number_of_missed_transfers = 0
    
    # We only need the status.ONBOARD for passengers with transfers
    request_ids = list(sorted([request_id for request_id in transfers.keys()]))
    trips_observations_df = trips_observations_df[
                        (trips_observations_df['Status'].isin(['PassengersStatus.ONBOARD'])) &
                        (trips_observations_df['ID'].isin(request_ids))]
    
    #Remove rows if Assigned vehicle contains 'walking' (these are added legs for walking time due to skip-stop tactic)
    trips_observations_df = trips_observations_df[
                     ~trips_observations_df['Assigned vehicle'].astype(str).str.contains('walking', na=False)]
    
    #Sort by ID and time
    trips_observations_df = trips_observations_df.sort_values(by=['ID', 'Time'])

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
            not_completed_requests.append(request_id)
            break
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
        for leg in request_legs_list:
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
                #Check if the vehicle is the same for each leg of the trip
                if str(int(trips_observations_df.iloc[row_index]['Assigned vehicle'])) != leg[2]:
                    number_of_missed_transfers += 1
                else:
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
    return(number_of_completed_transfers, percentage_missed_transfers, not_completed_requests)

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

def get_travel_time_stats(output_folder_path, transfers, not_completed_requests):
    total_times = []
    transfer_times = []
    # Get total travel time for all passengers (not only transfer passengers)
    trips_details_observations_df = pd.read_csv(os.path.join(output_folder_path, 'trips_details_observations_df.csv'))
    for index, row in trips_details_observations_df.iterrows():
        total_time = row['wait_before_boarding'] + row['onboard_time'] + row['transfer_time']
        if row['id'] in not_completed_requests:
            total_time += 3600 # 30 minutes penalty for not completing the trip
        total_times.append(total_time)
        if row['id'] in transfers.keys():
            transfer_times.append(row['transfer_time'])
    return(total_times, transfer_times)

def get_transfer_and_travel_time_stats(output_folder_path, transfers, total_transfers, request_legs):
    number_of_completed_transfers, percentage_missed_transfers, not_completed_requests= get_transfer_stats(output_folder_path, transfers, total_transfers, request_legs)
    total_times, transfer_times = get_travel_time_stats(output_folder_path, transfers, not_completed_requests)
    return(number_of_completed_transfers, percentage_missed_transfers, transfer_times, total_times)

def plot_single_line_comparisons(instance_name,
                                 requests_file_path,
                                 line_name="70E",
                                 base_folder="output/fixed_line/gtfs",
                                 transfer_type = 0):
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
        print('NO TACTICS')
        number_of_completed_transfers_notactics, percentage_missed_transfers_notactics, transfer_times_notactics, total_times_notactics = get_transfer_and_travel_time_stats(baseline_folder, transfers, total_transfers, request_legs)
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
            print('ALGO PARAMS', params)
            number_of_completed_transfers_key, percentage_missed_transfers_key, transfer_times_key, total_times_key = get_transfer_and_travel_time_stats(sim_folder, transfers, total_transfers, request_legs)
        else: 
            continue
        group_index = 1 + i // 3  # Group index based on the 6 groups specified
        key = f"{group_labels[group_index]} {sub_labels[i % 3]}"
        group_data[key] = [time / 60 for time in total_times_key]
        if transfer_type == 0:
            missed_transfer_data[key] = percentage_missed_transfers_key#output_data["missed_transfer_percentage_sim2"] 
        elif transfer_type == 1:
            missed_transfer_data[key] = number_of_completed_transfers_key#output_data["total_transfers_sim2"]
        else:
            missed_transfer_data[key] = np.mean(transfer_times_key)/60

    # Define consistent colors for each algorithm across groups
    algorithm_colors = {
        "No tactics": "grey",
        "Optimal\ntravel paths": "#f781bf",
        "Deterministic": '#4daf4a',#"#377eb8",
        "Regret": "#ff7f00",
        "Perfect Info": '#f781bf'
    }
    mean_color = "black"
    median_color = "black"
    transfers_color = 'blue'#"#377eb8"#'dodgerblue'
    transfers_marker = "o-"
    transfers_marker_size = 8
    if transfer_type == 0:
        transfers_label = "Missed Transfers (%)"
    elif transfer_type == 1:
        transfers_label = "Number of transfers"
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
    # ax.set_ylim(0, max([max(group) for group in data]) * 0.7)  # Set y-limit for better visibility

    # Plot missed transfer percentages as points on the secondary y-axis
    ax2.plot(positions, missed_transfer_data.values(), transfers_marker, color=transfers_color, label=transfers_label, markersize=transfers_marker_size)
    # Add values as text annotations above the points
    for i, value in enumerate(missed_transfer_percentages):
        ax2.text(positions[i]-0.05, value+0.1, f'{value:.1f}', ha='center', va='bottom', fontsize=fontsize-2, color=transfers_color)
    # ax2.set_ylim(min(missed_transfer_data.values())*0.7, max(missed_transfer_data.values()) * 1.2)  # Set y-limit for better visibility
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
    if len(line_name)>10:
        all_lines_string = 'All lines'
    else:
        all_lines_string = ', '.join([str(line_name_single)[:-1] for line_name_single in line_name])
    ax.set_title(f"Comparison of passenger travel and transfer times\nfor line(s) {all_lines_string}", fontsize=18)
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
    if len(line_name) >10:
        line_name = 'AllLines'
    figure_name = f"{line_name}_travel_time_and_"+addendum+"_comparison.png"
    plt.savefig(os.path.join(base_folder, instance_name, figure_name))
    # plt.show()

# Define the test instance name
instance_name = "gtfs2019-11-27_LargeInstanceAll"
route_dict = get_route_dictionary()
data_name = 'gtfs2019-11-25_EveningRushHour'
for grid_style in route_dict:
    instance_name = data_name+'_'+grid_style
    data_gtfs_name = data_name.replace('_','-')
    requests_file_path = os.path.join('data','fixed_line','gtfs',data_gtfs_name)
    for route_ids_list in [route_dict[grid_style]]:
        for transfer_type in [0,1,2]:
            # Run the function to compare and plot passenger travel times across different parameters for line 70E
            plot_single_line_comparisons(instance_name, requests_file_path=requests_file_path, line_name = route_ids_list, transfer_type = transfer_type)
# Run the function to compare and plot passenger travel times across different parameters for line 70E
# data_name = "gtfs2019-11-25_TestInstanceDurationCASPT_NEW"
# instance_name = data_name
# data_gtfs_name = "gtfs2019-11-25-TestInstanceDurationCASPT_NEW"
# route_ids_list = [["17N", "151S", "26E", "42E", "56E"],"42E"]
# requests_file_path = os.path.join('data','fixed_line','gtfs',data_gtfs_name)
# for transfer_type in [0,1,2]:
#     plot_single_line_comparisons(instance_name, requests_file_path=requests_file_path, line_name = route_ids_list, transfer_type = transfer_type)