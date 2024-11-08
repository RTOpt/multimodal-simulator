import pandas as pd
import os
import matplotlib.pyplot as plt

def analyze_simulations(simulation1_path, simulation2_path, relative_increase_threshold=1.5):
    # Load the two simulation data files
    sim1_df = pd.read_csv(simulation1_path)
    sim2_df = pd.read_csv(simulation2_path)
    
    # Identify total travel time for each passenger in each simulation
    sim1_df["total_travel_time"] = sim1_df["wait_before_boarding"] + sim1_df["onboard_time"] + sim1_df["transfer_time"]
    sim2_df["total_travel_time"] = sim2_df["wait_before_boarding"] + sim2_df["onboard_time"] + sim2_df["transfer_time"]

    # Filter out passengers with no transfers for transfer time boxplots
    transfer_times_sim1 = sim1_df[sim1_df["transfer_time"] > 0]["transfer_time"]
    transfer_times_sim2 = sim2_df[sim2_df["transfer_time"] > 0]["transfer_time"]

    # Merge DataFrames on 'id' column to align passenger data from both simulations
    comparison_df = pd.merge(sim1_df, sim2_df, on="id", suffixes=('_sim1', '_sim2'))

    # Calculate individual travel time differences for plotting
    travel_times_sim1 = sim1_df["total_travel_time"]
    travel_times_sim2 = sim2_df["total_travel_time"]

    # Identify missed transfers based on a relative increase in transfer time
    comparison_df["relative_transfer_increase"] = (
        comparison_df["transfer_time_sim2"] / comparison_df["transfer_time_sim1"]
    )
    comparison_df["missed_transfer_sim1"] = comparison_df["relative_transfer_increase"] > relative_increase_threshold
    comparison_df["missed_transfer_sim2"] = comparison_df["relative_transfer_increase"] < (1 / relative_increase_threshold)

    # Count the total number of transfers (all individual transfers) in each simulation
    total_transfers_sim1 = sim1_df["transfer_time"].astype(bool).sum()
    total_transfers_sim2 = sim2_df["transfer_time"].astype(bool).sum()

    # Count missed transfers (where relative increase indicates a missed transfer) in each simulation
    missed_transfers_sim1 = comparison_df["missed_transfer_sim1"].sum()
    missed_transfers_sim2 = comparison_df["missed_transfer_sim2"].sum()

    # Calculate percentage of missed transfers in each simulation
    missed_transfer_percentage_sim1 = (missed_transfers_sim1 / total_transfers_sim1) * 100 if total_transfers_sim1 > 0 else 0
    missed_transfer_percentage_sim2 = (missed_transfers_sim2 / total_transfers_sim2) * 100 if total_transfers_sim2 > 0 else 0

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
                          patch_artist=True, labels=["Offline", "H"])
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
    box2 = axs[1].boxplot([output_data["transfer_times_sim1"], output_data["transfer_times_sim2"]],
                          patch_artist=True, positions=[1, 2])
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

# Example Usage
if __name__ == "__main__":
    # Run analysis on two simulations
    output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs2019-11-01-TestInstance",)
    path_to_simulation2 = os.path.join(output_folder_path,'H', 'trips_details_observations_df.csv')
    path_to_simulation1 = os.path.join(output_folder_path,'offline', 'trips_details_observations_df.csv')
    output_data = analyze_simulations(path_to_simulation1, path_to_simulation2)
    
    # Plot the results
    plot_simulation_results(output_data, output_folder_path)