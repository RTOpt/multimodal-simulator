import pandas as pd
import csv
import os
import matplotlib.pyplot as plt
from stl_gtfs_simulator import get_output_subfolder
import matplotlib.lines as mlines
from ast import literal_eval

def analyze_simulations(simulation1_path, simulation2_path, total_transfers, relative_increase_threshold=1.5):
    # Load the two simulation data files
    sim1_df = pd.read_csv(simulation1_path)
    sim2_df = pd.read_csv(simulation2_path)
    
    # Count rows with positive 'transfer_time' in each simulation
    positive_transfer_time_sim1 = sim1_df[sim1_df["transfer_time"] > 0].shape[0]
    positive_transfer_time_sim2 = sim2_df[sim2_df["transfer_time"] > 0].shape[0]
    # print('Positive transfer time sim1:', positive_transfer_time_sim1)
    # print('Positive transfer time sim2:', positive_transfer_time_sim2)

    # Identify total travel time for each passenger in each simulation
    sim1_df["total_travel_time"] = sim1_df["wait_before_boarding"] + sim1_df["onboard_time"] + sim1_df["transfer_time"]
    sim2_df["total_travel_time"] = sim2_df["wait_before_boarding"] + sim2_df["onboard_time"] + sim2_df["transfer_time"]

    # Filter out passengers with no transfers for transfer percentage calculation
    transfer_times_sim1 = sim1_df[sim1_df["transfer_time"] > 0]["transfer_time"]
    transfer_times_sim2 = sim2_df[sim2_df["transfer_time"] > 0]["transfer_time"]

    #Mean transfer time
    # print('Mean transfer time sim1:', transfer_times_sim1.mean())
    # print('Mean transfer time sim2:', transfer_times_sim2.mean())

    # Merge DataFrames on 'id' column to align passenger data from both simulations
    comparison_df = pd.merge(sim1_df, sim2_df, on="id", suffixes=('_sim1', '_sim2'))

    # Calculate individual travel time differences for plotting
    travel_times_sim1 = sim1_df["total_travel_time"]
    travel_times_sim2 = sim2_df["total_travel_time"]

    # Identify missed transfers based on a relative increase in transfer time
    comparison_df["relative_transfer_increase"] = (
        comparison_df["transfer_time_sim2"] / comparison_df["transfer_time_sim1"]
    )
    comparison_df["missed_transfer_sim2"] = comparison_df["relative_transfer_increase"] > relative_increase_threshold
    comparison_df["missed_transfer_sim1"] = comparison_df["relative_transfer_increase"] < (1 / relative_increase_threshold)
    
    # Count the total number of transfers (all individual transfers) in each simulation
    total_transfers_sim1 = positive_transfer_time_sim1
    total_transfers_sim2 = positive_transfer_time_sim2

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
        "travel_times_sim1": travel_times_sim1,
        "travel_times_sim2": travel_times_sim2,
        "transfer_times_sim1": transfer_times_sim1,
        "transfer_times_sim2": transfer_times_sim2,
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

def plot_simulation_results(output_data, output_folder_path=None):
    # Define colors for "Offline", "H", and median line
    offline_color = "#AEC6CF"  # Light pastel blue for "Offline"
    h_color = "#FFB347"        # Light pastel orange for "H"
    median_color = "#000000"   # Black color for median lines

    # Set up a figure with two subplots
    fig, axs = plt.subplots(1, 2, figsize=(14, 6))

    # 1. Boxplot for total travel times
    box1 = axs[0].boxplot([output_data["travel_times_sim1"], output_data["travel_times_sim2"]],
                          patch_artist=True, labels=["Offline", "H"], showfliers=False)
    axs[0].set_title("Total Travel Time Comparison")
    axs[0].set_ylabel("Total Travel Time (seconds)")
    axs[0].set_xticklabels([])  # Remove x-axis labels

    # Apply colors to the boxplots for total travel times
    for patch, color in zip(box1['boxes'], [offline_color, h_color]):
        patch.set_facecolor(color)
    for median in box1['medians']:
        median.set_color(median_color)

    # 2. Combined plot for transfer times and missed transfer percentages
    # Boxplot for transfer times
    # Remove outliers for better visibility
    box2 = axs[1].boxplot([output_data["transfer_times_sim1"], output_data["transfer_times_sim2"]],
                          patch_artist=True, positions=[1, 2], showfliers = False)
    
    axs[1].set_title("Transfer Time and Missed Transfer Percentage")
    axs[1].set_ylabel("Transfer Time (seconds)")
    axs[1].set_xticklabels([])  # Remove x-axis labels

    # Apply colors to the boxplots for transfer times
    for patch, color in zip(box2['boxes'], [offline_color, h_color]):
        patch.set_facecolor(color)
    for median in box2['medians']:
        median.set_color(median_color)

    # Create a secondary y-axis on the right for the missed transfer percentages
    ax2 = axs[1].twinx()
    missed_transfer_percentages = [
        output_data["missed_transfer_percentage_sim1"],
        output_data["missed_transfer_percentage_sim2"]
    ]
    ax2.bar([1, 2], missed_transfer_percentages, color=[offline_color, h_color], alpha=0.6, width=0.5, align='center')
    ax2.set_ylim(0, max(missed_transfer_percentages) * 1.2)  # Set y-limit for better visibility
    ax2.set_ylabel("Missed Transfer Percentage (%)")

    # Center x-ticks below the boxplots and bars
    axs[1].set_xticks([1, 2])
    axs[1].set_xticklabels(["Offline", "H"])

    # Display the plots
    plt.tight_layout()
    plt.show()

    # Save in the output folder
    name = "simulation_comparison_Offline_H.png"
    if output_folder_path:
        plt.savefig(os.path.join(output_folder_path, name))
    return()

def get_request_transfer_data(instance_name):
    data_folder = os.path.join('data','fixed_line','gtfs')
    new_instance_name = instance_name.replace('_','-')
    request_file_path = os.path.join(data_folder, new_instance_name, 'requests.csv')
    transfers = {}
    with open(request_file_path, 'r') as requests_file:
            requests_reader = csv.reader(requests_file, delimiter=';')
            next(requests_reader, None)
            total_transfers = 0
            for row in requests_reader:
                # print(row)
                request_id = row[0] 
                legs_stops_pairs_list = None
                if len(row) - 1 == 7:
                    legs_stops_pairs_list = literal_eval(
                        row[7])
                if legs_stops_pairs_list is not None:
                    current_transfer = -1
                    for stops_pair in legs_stops_pairs_list:
                        current_transfer += 1
                    total_transfers += current_transfer if current_transfer >= 0 else 0
                    if current_transfer > 0:
                        transfers[request_id] = current_transfer
    return(transfers, total_transfers)

def get_completed_transfers(output_folder_path, transfers, total_transfers):
    trips_observations_df = pd.read_csv(os.path.join(output_folder_path, 'trips_observations_df.csv'))
    trips_details_observations_df = pd.read_csv(os.path.join(output_folder_path, 'trips_details_observations_df.csv'))
    # For each request id in the transfers dict, check if there is a row in the trips_observations_df that
    ### has the same request ID
    ### has a Status of 'PassengersStatus.COMPLETE'
    ### has next_legs of []
    trips_observations_df = trips_observations_df[trips_observations_df['Status'] == 'PassengersStatus.COMPLETE']
    number_of_completed_transfers = 0
    completed_transfers = []
    for request_id, num_transfers in transfers.items():
        if trips_observations_df[(trips_observations_df['ID'].astype(str) == str(request_id)) & (trips_observations_df['Next legs'].astype(str) == '[]')].shape[0] > 0:
            number_of_completed_transfers += num_transfers
            completed_transfers.append(request_id)
    for completed_transfer in completed_transfers:
        # check if transfer time of completed transfer is greater than 0 
        if int(trips_details_observations_df[trips_details_observations_df['id'].astype(str) == str(completed_transfer)]['transfer_time'].values[0]) == 0:
            # set to 1 if transfer time is 0
            row = trips_details_observations_df[trips_details_observations_df['id'].astype(str) == str(completed_transfer)]
            row['transfer_time'] = transfers[completed_transfer]
            trips_details_observations_df[trips_details_observations_df['id'].astype(str) == str(completed_transfer)] = row
            continue
    ### Save updated trips_details_observations_df without the index
    trips_details_observations_df.to_csv(os.path.join(output_folder_path, 'trips_details_observations_df.csv'), index=False)
    print('Number of completed transfers:', number_of_completed_transfers)
    number_missed_transfers = total_transfers - number_of_completed_transfers
    percentage_missed_transfers = (number_missed_transfers/total_transfers)*100 if total_transfers > 0 else 0
    return(number_of_completed_transfers, number_missed_transfers, percentage_missed_transfers)

def plot_single_line_comparisons(instance_name,
                                 line_name="70E",
                                 relative_increase_threshold = 1.5,
                                 base_folder="output/fixed_line/gtfs",
                                 transfer_type = 0):
    """ 
    Compare the passenger travel times for across different algorithms and settings.

    Parameters:
    - instance_name: Name of the test instance folder
    - line_name: Name of the bus line(s) to compare
    - relative_increase_threshold: Threshold for missed transfer detection
    - base_folder: Base folder for the output data
    - transfer_type: 0 for percentage of missed transfers
                     1 for number of missed transfers
                     2 for mean transfer time

    """
    # Define base parameters for comparisons
    base_params = (0, False, False, line_name, True)  # Offline, smartcard data (baseline)
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
    transfers, total_transfers = get_request_transfer_data(instance_name)
    print('Total transfers:', total_transfers)

    # Define the labels for main groups
    group_labels = ["Offline", "Hold", "Hold&\nSpeedup", "Hold&\nSkip-Stop", "Hold, Speedup&\nSkip-Stop"]
    
    sub_labels = ["Deterministic", "Regret", "Perfect Info"]

    # Initialize group_data with Offline baseline
    baseline_folder = get_output_subfolder(output_folder_path, *base_params)
    baseline_file = os.path.join(baseline_folder, "trips_details_observations_df2.csv")
    if os.path.exists(os.path.join(baseline_folder, 'trips_observations_df.csv')):
        number_of_completed_transfers_offline, number_missed_transfers_offline, percentage_missed_transfers_offline = get_completed_transfers(baseline_folder, transfers, total_transfers)
     # Ensure the baseline file exists
    if not os.path.exists(baseline_file):
        raise FileNotFoundError(f"Baseline file not found: {baseline_file}")
    output_data_baseline = analyze_simulations(baseline_file, baseline_file, relative_increase_threshold)
    group_data["Offline"] = [time / 60 for time in output_data_baseline["travel_times_sim1"]]
    if transfer_type == 0:
        missed_transfer_data["Offline"] = percentage_missed_transfers_offline #output_data_baseline["missed_transfer_percentage_sim1"]
    elif transfer_type == 1:
        missed_transfer_data["Offline"] = number_of_completed_transfers_offline #output_data_baseline["total_transfers_sim1"]
    else:
        missed_transfer_data["Offline"] = output_data_baseline["transfer_times_sim1"].mean()/60

    # Generate comparisons for algo_params
    for i, params in enumerate(algo_params):
        sim_folder = get_output_subfolder(output_folder_path, *params)
        if os.path.exists(os.path.join(sim_folder, 'trips_observations_df.csv')):
            number_of_completed_transfers_key, number_missed_transfers_key, percentage_missed_transfers_key = get_completed_transfers(sim_folder, transfers, total_transfers)
        sim_file = os.path.join(sim_folder, "trips_details_observations_df2.csv")
        if os.path.exists(sim_file):
            output_data = analyze_simulations(baseline_file, sim_file, relative_increase_threshold)
            # print('Output data for algos:', output_data)
            # group_index = 2 + i // 3  # Group index based on the 6 groups specified
            group_index = 1 + i // 3  # Group index based on the 6 groups specified
            key = f"{group_labels[group_index]} {sub_labels[i % 3]}"
            group_data[key] = [time / 60 for time in output_data["travel_times_sim2"]]
            if transfer_type == 0:
                missed_transfer_data[key] = percentage_missed_transfers_key#output_data["missed_transfer_percentage_sim2"]
            elif transfer_type == 1:
                missed_transfer_data[key] = number_of_completed_transfers_key#output_data["total_transfers_sim2"]
            else:
                missed_transfer_data[key] = output_data["transfer_times_sim2"].mean()/60

        else:
            print(f"Warning: No results found for {params} in {sim_folder}")

    # Define consistent colors for each algorithm across groups
    algorithm_colors = {
        "Offline": "grey",
        "Optimal\ntravel paths": "#f781bf",
        "Deterministic": "#377eb8",
        "Regret": "#4daf4a",
        "Perfect Info": "#ff7f00"
    }
    mean_color = "black"
    median_color = "black"
    transfers_color = "purple"
    transfers_marker = "o-"
    if transfer_type == 0:
        transfers_label = "Missed Transfers (%)"
    elif transfer_type == 1:
        transfers_label = "Number of transfers"
    else:
        transfers_label = "Mean transfer time (in minutes)"
    fontsize = 16

    # Plotting
    fig, ax = plt.subplots(figsize=(14, 8))
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
            pos += 1
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
                pos += 1
        pos += 1  # Add space between main groups

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
        ax.text(pos, median_value, f'{median_value:.1f}', ha='center', va='top', fontsize=fontsize-2, color=median_color)

        # Annotate the mean value below the mean line
        ax.text(pos, mean_value, f'{mean_value:.1f}', ha='center', va='bottom', fontsize=fontsize-2, color=mean_color)


    # Plot missed transfer percentages as points on the secondary y-axis
    ax2.plot(positions, missed_transfer_data.values(), transfers_marker, color=transfers_color, label=transfers_label)
    # ax2.set_ylim(0, max(missed_transfer_data.values()) * 1.2)  # Set y-limit for better visibility
    if transfer_type == 0:
        ax2.set_ylabel("Missed Transfers (%)", fontsize=fontsize)
    elif transfer_type == 1:
        ax2.set_ylabel("Number of transfers", fontsize=fontsize)
    else:
        ax2.set_ylabel("Mean transfer time (in minutes)", fontsize=fontsize)
    ax2.tick_params(axis='y', which='major', labelsize=fontsize-2, labelleft=False, labelright=True, left=False, right=True, color=transfers_color)

    # Add group x-ticks and remove individual sub-label x-ticks
    ax.set_xticks(group_ticks)
    ax.set_xticklabels(group_tick_labels, fontsize=16)

    # Set primary y-axis parameters
    ax.set_title(f"Comparison of Passenger Travel Times for line(s) {line_name}", fontsize=fontsize, fontweight='bold')
    ax.set_ylabel("Travel Time (minutes)", fontsize=fontsize)
    ax.tick_params(axis='y', which='major', labelsize=fontsize-2, labelleft=True, labelright=False, left=True, right=False)
    
    # Add legend for algorithm colors with bold font
    legend_patches = [mlines.Line2D([0], [0], color=color, lw=6, label=label)
                      for label, color in algorithm_colors.items() if label in sub_labels + ["Offline"]]
    
    # Add mean, median, and missed transfer line entries to the legend
    mean_line = mlines.Line2D([0], [0], color=mean_color, linestyle='--', linewidth=2, label='Mean')
    median_line = mlines.Line2D([0], [0], color=median_color, linestyle='-', linewidth=2, label='Median')
    missed_transfers_line = mlines.Line2D([0], [0], color=transfers_color, lw=2, label=transfers_label)
    legend_patches.extend([mean_line, median_line, missed_transfers_line])

    # Optimize legend position and style
    ax.legend(handles=legend_patches, title="Algorithm", loc="best", fontsize=fontsize-2, title_fontsize=fontsize,
             framealpha=0.9, shadow=True,)

    plt.tight_layout()
    if transfer_type == 0:
        addendum = 'pecentage_missed_transfers'
    elif transfer_type == 1:
        addendum = 'number_transfers'
    else:
        addendum = 'mean_transfer_time'
    figure_name = f"{line_name}_travel_time_and_"+addendum+"_comparison.png"
    plt.savefig(os.path.join(base_folder, instance_name, figure_name))
    plt.show()


# Example Usage
if __name__ == "__main__":
    # # Run analysis on two simulations
    # output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs2019-11-01-TestInstance",)
    # path_to_simulation2 = os.path.join(output_folder_path,'H', 'trips_details_observations_df.csv')
    # path_to_simulation1 = os.path.join(output_folder_path,'offline', 'trips_details_observations_df.csv')
    # output_data = analyze_simulations(path_to_simulation1, path_to_simulation2)
    
    # # Plot the results
    # plot_simulation_results(output_data, output_folder_path)

    # Define the test instance name
    instance_name = "gtfs2019-11-01_TestInstanceDurationShort"
    transfer_time = False
    for line_name in [[ '17N', '151N', '26O', '42E', '56O'], ['42E']]:
        for transfer_type in [0, 1, 2]:
            # Run the function to compare and plot passenger travel times across different parameters for line 70E
            plot_single_line_comparisons(instance_name, line_name = line_name, relative_increase_threshold = 1.4, transfer_type = transfer_type)