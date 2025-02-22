import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np
from stl_network_analysis import get_color_dict, analyze_network, get_route_dictionary

# Define the base directory for the data
base_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'fixed_line')

# Paths for the specific data files
shapes_file_path = os.path.join(base_dir, 'gtfs', 'shapes.txt')
gtfs_2019_dir = os.path.join(base_dir, 'gtfs', 'gtfs2019-11-01')
stops_file_path = os.path.join(gtfs_2019_dir, 'stops.txt')
trips_file_path = os.path.join(gtfs_2019_dir, 'trips.txt')
stop_times_file_path = os.path.join(gtfs_2019_dir, 'stop_times.txt')
connections_file_path = os.path.join(gtfs_2019_dir, 'available_connections.json')
background_image_path = os.path.join(os.path.dirname(__file__), 'figures', 'streetmap_Laval_color.png')

# Load the GTFS data files
stops_df = pd.read_csv(stops_file_path)
new_trips_df = pd.read_csv(trips_file_path)
new_stop_times_df = pd.read_csv(stop_times_file_path)
shapes_df = pd.read_csv(shapes_file_path)

# Map boundaries for displaying the map
map_bounds = (45.73201, 45.50393, -73.47764, -73.90119)

# Define the contrasting color palette
contrasting_color_palette =  ['red', 'blue', 'green', 'deeppink', 'dodgerblue']
fourty_colors_palette = ['red', 'blue', 'green', 'brown','purple', 'darkcyan',  'gray', 'olive', 'cyan', 'black', 'pink', 'orange', 'yellow', 'magenta', 'lime', 'teal', 'indigo', 'maroon', 'navy', 'peru', 'plum', 'salmon', 'sienna', 'tan', 'thistle', 'tomato', 'turquoise', 'violet', 'wheat', 'yellowgreen', 'aquamarine', 'bisque', 'blueviolet', 'burlywood', 'cadetblue', 'chartreuse', 'chocolate', 'coral', 'cornflowerblue', 'cornsilk', 'crimson']

def load_connections(connections_file):
    """
    Load available connections from a JSON file and create a dictionary mapping each stop to its connected stops.
    """
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

def get_first_shape_for_route(route_id, shapes_data):
    """
    Get the first representation of a shape for a given route_id from the shapes data.
    """
    # Check if the route_id is present in the shapes data
    if not any(shapes_data['shape_id'].str.contains(route_id)):
        # return empty dataframe if the route_id is not present
        return None
    first_shape_id = shapes_data[shapes_data['shape_id'].str.contains(route_id)]['shape_id'].iloc[0]
    shape_points = shapes_data[shapes_data['shape_id'] == first_shape_id].sort_values(by='shape_pt_sequence')
    return shape_points

def get_ordered_stop_list(route_id, new_trips_data, new_stop_times_data):
    """
    Get an ordered list of unique stop_ids for a given route_id using new trips and stop_times data.
    """
    # Use the trips file to map trip_id to route_id
    relevant_trip_ids = new_trips_data[new_trips_data['route_id'] == route_id]['trip_id'].unique()
    relevant_stops = new_stop_times_df[new_stop_times_df['trip_id'].isin(relevant_trip_ids)].sort_values(by='stop_sequence')
    ordered_stop_ids = list(relevant_stops['stop_id'].drop_duplicates())
    return ordered_stop_ids

def mark_first_and_last_stops_with_offsets(route_stop_lists, stops_data, ax, route_ids, color_palette, offsets_applied):
    """
    Mark the first and last stops for each route with their stop_ids as labels, ensuring the labels appear in front,
    and applying any offsets used for the corresponding route.
    """
    for idx, route_id in enumerate(route_ids):
        stop_list = route_stop_lists.get(route_id, [])
        if stop_list:
            first_stop_id = stop_list[0]
            last_stop_id = stop_list[-1]
            first_stop_data = stops_data[stops_data['stop_id'] == first_stop_id]
            last_stop_data = stops_data[stops_data['stop_id'] == last_stop_id]

            # Retrieve the offsets applied for this route
            lat_offset, lon_offset = offsets_applied.get(route_id, (0, 0))
            # lat_offset, lon_offset = 0, 0 # Remove offsets for now

            if not first_stop_data.empty:
                first_stop_name = first_stop_data['stop_name'].values[0]  # Get the stop_name
                ax.scatter(first_stop_data['stop_lon'].values[0] + lon_offset, first_stop_data['stop_lat'].values[0] + lat_offset, 
                           color=color_palette[idx % len(color_palette)], s=80, zorder=5, marker='o')
                ax.text(first_stop_data['stop_lon'].values[0] + lon_offset, first_stop_data['stop_lat'].values[0] + lat_offset, 
                        "", fontsize=9, ha='right', color='black', zorder=10)

            if not last_stop_data.empty:
                last_stop_name = last_stop_data['stop_name'].values[0]  # Get the stop_name
                ax.scatter(last_stop_data['stop_lon'].values[0] + lon_offset, last_stop_data['stop_lat'].values[0] + lat_offset, 
                           color=color_palette[idx % len(color_palette)], s=80, zorder=5, marker='o')
                ax.text(last_stop_data['stop_lon'].values[0] + lon_offset, last_stop_data['stop_lat'].values[0] + lat_offset, 
                        "", fontsize=9, ha='right', color='black', zorder=10)

def mark_transfer_hubs(ax):
    """
    Mark transfer hubs on the map by selecting one representative stop from each set of connected stops
    and show its stop_name as a label.
    """
    transfer_stops =[(42482,'N. DAME/JARRY', -73.749336,45.54072),
     (43343,'SOUVENIR/AVENIR',-73.723699,45.561729),
     (41447,'C. LABELLE/FACE AU 289',-73.78708,45.573978),
    (41801,'LAURENTIDES/CONCORDE',-73.692524,45.570631)]
    for stop_id, stop_name, lon, lat in transfer_stops:
        #plot the stop with stop_id written above it
        # ax.text(lon, lat+0.0002, str(stop_id), fontsize=14, ha='right', color='black', zorder=10)
        ax.scatter(lon, lat, color='red', s=200, marker='o', zorder=10, label = str(stop_id))
        # draw a circle around the stop
        ax.add_artist(plt.Circle((lon, lat), 0.015, color='red', fill=False, zorder=10, linewidth=2))

def mark_transfer_and_connecting_stops(route_stop_lists, stops_data, ax, stop_connections):
    """
    Mark stops that are present on more than one route (transfer stops) and stops that have available connections
    to another route (connecting stops).
    """
    # Count occurrences of each stop across all routes to identify transfer stops
    stop_count = {}
    for stop_list in route_stop_lists.values():
        for stop_id in stop_list:
            stop_count[stop_id] = stop_count.get(stop_id, 0) + 1

    # Mark transfer stops: stops that appear on multiple routes
    transfer_stops = {stop_id for stop_id, count in stop_count.items() if count > 1}

    # Mark connecting stops: stops that have a connection to another route's stop
    connecting_stops = set()
    for route_id, stop_list in route_stop_lists.items():
        for stop_id in stop_list:
            # Check if any connected stops appear in other routes' stop lists
            for connected_stop in stop_connections.get(stop_id, []):
                if any(connected_stop in other_stop_list for other_route_id, other_stop_list in route_stop_lists.items() if other_route_id != route_id):
                    connecting_stops.add(stop_id)

    # Plot transfer and connecting stops
    for stop_id in transfer_stops | connecting_stops:
        stop_data = stops_data[stops_data['stop_id'] == stop_id]
        if not stop_data.empty:
            ax.scatter(stop_data['stop_lon'], stop_data['stop_lat'], color='black', s=60, marker='.', linewidths=0.5, zorder=10)

def mark_metro_stations(stops_data, ax, stop_connections):
    """
    Mark metro stations on the map by selecting one representative stop from each set of connected stops
    that contain 'METRO' in their name, and show its stop_name as a label.
    """
    color = 'red'
    marker_shape = '^'
    label_size = 14
    marker_size = 200

    metro_stations = [(47911,'Cartier',-73.682497,45.559958, 45.565, 'center'),
                      (41006,'Concorde',-73.70785,45.561048,45.564, 'center'),
                      (48002,'Montmorrency',-73.720829,45.557936, 45.55, 'center')]
    for stop_id, stop_name, lon, lat, lat2, alignment in metro_stations:
        ax.scatter(lon, lat, color=color, s=marker_size, marker=marker_shape, zorder=10)

def plot_map_with_dynamic_extent(network_style, offset_distance=0.0004, padding=0.01):
    """
    Plot the map with thinner transfer stop markers, an updated legend, and dynamic extent to focus on the plotted routes.
    The padding parameter controls how much extra space is added around the routes.
    """
    route_ids = get_route_dictionary()[network_style]
    # Read all other routes from new_trips_df
    other_routes = [route_id for route_id in new_trips_df['route_id'].unique() if route_id not in route_ids]
    color_dict = get_color_dict(route_ids)
    fig, ax = plt.subplots(figsize=(12, 8))

    # Make background image transparent
    ax.imshow(Image.open(background_image_path), extent=[map_bounds[3], map_bounds[2], map_bounds[1], map_bounds[0]], alpha=0.4, zorder=0)
    route_stop_lists = {}
    plotted_routes = []  # Track plotted routes to handle offsets for shared segments
    lat_min, lat_max = float('inf'), float('-inf')
    lon_min, lon_max = float('inf'), float('-inf')

    offsets_applied = {}  # Track the offsets applied to each route for first and last stop adjustment

    for idx, route_id in enumerate(other_routes):
        if route_id in route_ids:
            continue
        color = 'sienna'

        # Get the shape points for the current route
        shape_points = get_first_shape_for_route(route_id, shapes_df)
        if shape_points is None or shape_points['shape_pt_lat'] is None or shape_points['shape_pt_lon'] is None:
            continue

        # Get the ordered list of stops for the current route
        ordered_stop_list = get_ordered_stop_list(route_id, new_trips_df, new_stop_times_df)

        # Plot the adjusted shape
        latitudes = shape_points['shape_pt_lat'].values
        longitudes = shape_points['shape_pt_lon'].values
        if network_style != 'all' and network_style != 'transfer_hubs':
            ax.plot(longitudes, latitudes, color=color, linewidth=1.5, zorder=2, label="Feeder lines")

        # Plot the route stops
        # stops_data = stops_df[stops_df['stop_id'].isin(ordered_stop_list)]
        # ax.scatter(stops_data['stop_lon'], stops_data['stop_lat'], color=color, s=30, marker='.', linewidths=0.5, zorder=10)
    if network_style =='corridor':
        offset_distance = 0.0008
    else: 
        offset_distance = 0
    for idx, route_id in enumerate(route_ids):
        # Get the ordered list of stops for the current route
        ordered_stop_list = get_ordered_stop_list(route_id, new_trips_df, new_stop_times_df)
        route_name = route_id[:-1]
        if route_name in route_stop_lists:
            route_stop_lists[route_name] += ordered_stop_list
            #Only keep unique stops
            route_stop_lists[route_name] = list(set(route_stop_lists[route_name]))
        else:
            route_stop_lists[route_name] = ordered_stop_list
    for idx, route_id in enumerate(route_ids):
        color = contrasting_color_palette[idx % len(contrasting_color_palette)]
        route_name = route_id[:-1]
        if route_name in plotted_routes:
            continue
        color = color_dict[route_name]
        if color == 'black':
            color = 'dodgerblue'
        if network_style=='all' or network_style=='transfer_hubs':
            color = 'blue'

        # Get the shape points for the current route
        shape_points = get_first_shape_for_route(route_id, shapes_df)

        # Update the lat/lon boundaries for dynamic extent calculation
        if shape_points is None or shape_points['shape_pt_lat'] is None or shape_points['shape_pt_lon'] is None:
            continue
        latitudes = shape_points['shape_pt_lat'].values
        longitudes = shape_points['shape_pt_lon'].values
        lat_min = min(lat_min, np.min(latitudes))
        lat_max = max(lat_max, np.max(latitudes))
        lon_min = min(lon_min, np.min(longitudes))
        lon_max = max(lon_max, np.max(longitudes))

        # Check if the current route shares any segments with previously plotted routes
        lat_offset = 0
        lon_offset = 0
        for previous_route in plotted_routes:
            # Find common stops between the current route and the previously plotted route
            common_stops = set(ordered_stop_list) & set(route_stop_lists[previous_route])
            if len(common_stops) > 1:  # If there are multiple common stops, we have a shared segment
                # Determine if the segment is more horizontal or vertical
                lat_diff = np.max(latitudes) - np.min(latitudes)
                lon_diff = np.max(longitudes) - np.min(longitudes)
                if lon_diff > lat_diff:  # More horizontal
                    lat_offset = offset_distance * (idx % 2 * 2 - 1)  # Apply offset to latitude
                    # if network_style=='all' or len(route_ids)>8:
                    #     lat_offset = 0
                    latitudes += lat_offset
                else:  # More vertical
                    lon_offset = offset_distance * (idx % 2 * 2 - 1)  # Apply offset to longitude
                    # if network_style=='all' or len(route_ids)>8:
                    #     lon_offset = 0
                    longitudes += lon_offset

        # Store the offsets for use when plotting the first and last stops
        offsets_applied[route_id] = (lat_offset, lon_offset)

        # Plot the adjusted shape
        ## Get route_id without last caracter
        route_name = route_id[:-1]
        if network_style =='corridor':
            linewidth = 3
        else:
            linewidth = 4
        ax.plot(longitudes, latitudes, label=f"Line {route_name}", color=color, linewidth=linewidth, zorder=3)

        # Plot the route stops
        # stops_data = stops_df[stops_df['stop_id'].isin(ordered_stop_list)]
        # ax.scatter(stops_data['stop_lon'], stops_data['stop_lat'], color=color, s=50, marker='.', linewidths=0.5, zorder=10)
        plotted_routes.append(route_name)

    # Mark the first and last stops with applied offsets
    # mark_first_and_last_stops_with_offsets(route_stop_lists, stops_df, ax, route_ids, color_palette=contrasting_color_palette, offsets_applied=offsets_applied)

    # Load available connections and mark transfer and connecting stops
    stop_connections = load_connections(connections_file_path)
    
    mark_transfer_and_connecting_stops(route_stop_lists, stops_df, ax, stop_connections)
    if network_style == 'transfer_hubs':
        mark_transfer_hubs(ax)
    # Mark metro stations on the map
    mark_metro_stations(stops_df, ax, stop_connections)                                      

    # Add legend entries for first/last stops and transfer stops
    # ax.scatter([], [], color='none', edgecolor='black', s=60, marker='o', label="First/Last Stop", zorder=5)
    ax.scatter([], [], color='black', s = 20, marker='.', linewidths=0.5, label = "Transfer stop \nbetween main lines", zorder=5)
    ax.scatter([], [], color='red', s = 100, marker='^', label = "Metro Station", zorder=2)
    ## Add legend handle with only one color for all routes
    if network_style== 'all' or network_style== 'transfer_hubs':
        ax.plot([], [], color='blue', linewidth=2, label="Main lines", zorder=3)
    if network_style == 'transfer_hubs':
        ax.scatter([],[], color='red', s=100, marker='o', label='Transfer hubs', zorder=10)
    # Adjust map extent to fit the plotted routes with some padding
    # Make sure to stay in map bounds
    if network_style != 'all' and network_style != 'radial' and network_style != 'transfer_hubs':
        padding = 0
    lat_min = max(lat_min - padding, map_bounds[1])
    lat_max = min(lat_max + padding, map_bounds[0])
    lon_min = max(lon_min - padding, map_bounds[3])
    lon_max = min(lon_max + padding, map_bounds[2])
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)

    #Set x and y ticks (longitude and latitude) for the map and their size
    ax.set_xticks([])
    ax.set_yticks([])

    ### Add a scale bar to the map
    ### The scale bar should be 1 km long
    ### The scale bar should be located at the bottom right corner of the map
    dist = 2/110.574
    ax.plot([lon_max-2*dist, lon_max-1*dist], [lat_min + 0.01, lat_min + 0.01], color='black', linewidth = 2)
    ### Add edges
    ax.plot([lon_max-2*dist, lon_max-2*dist], [lat_min + 0.009, lat_min + 0.011], color='black', linewidth = 2)
    ax.plot([lon_max-1*dist, lon_max-1*dist], [lat_min + 0.009, lat_min + 0.011], color='black', linewidth = 2)
    ax.text(lon_max-1.5*dist, lat_min + 0.012, '2 km', fontsize=10, ha='center', color='black')

    # Set the title including route_ids and stops in Laval, Quebec
    titles ={}
    titles['grid'] = "Map of grid style sub-network in Laval, Canada"
    titles['radial'] = "Map of radial style sub-network in Laval, Canada"
    titles['low_frequency'] = "Map of selected low frequency lines in Laval, Canada"
    titles['high_frequency'] = "Map of selected high frequency lines in Laval, Canada"
    titles['all'] = "Map of all main lines in case study network of Laval, Canada"
    titles['151'] = "Map of line 151 and its transferring lines in Laval, Canada"
    titles['corridor'] = "Map of corridor network in Laval, Canada"
    titles['transfer_hubs'] = "Map of all lines with transfer hubs in Laval, Canada"
    ax.set_title(titles[network_style], fontsize=18)

    # Add a legend with a white background and black border
    handles, labels = ax.get_legend_handles_labels()
    # Set the legend with only the desired handles and labels
    legend_zorder = 10  # Set the zorder for the legend to be on top of the plot elements
    nbr_columns = 1  # Set the number of columns in the legend to 1 by default
    if network_style== 'all' :
        desired_labels = ["Main lines", "Metro Station", "Transfer stop \nbetween main lines", "Feeder lines", "Transfer hubs"]
        desired_handles = [handles[labels.index(label)] for label in desired_labels if label in labels]  # Filter handles
    elif network_style == 'transfer_hubs':
        desired_labels = ["Main lines", "Metro Station","Transfer stop \nbetween main lines", "Transfer hubs"]
        desired_handles = [handles[labels.index(label)] for label in desired_labels if label in labels]
    else:
        nbr_columns = 1+len(route_ids)//8# Set the number of columns in the legend to 2
        unique = dict(zip(labels, handles))  # Create a dictionary with unique labels and handles
        desired_handles = unique.values()  # Get the handles for the desired labels
        desired_labels = unique.keys()  # Get the labels for the desired handles
    legend = ax.legend(handles=desired_handles, labels = desired_labels, loc = 'best', fontsize = 14, markerscale=1.5, ncol = nbr_columns)  # Add the legend to the plot with the desired handles and labels
    legend.get_frame().set_facecolor('white')  # Set the background color to white
    legend.get_frame().set_edgecolor('black')  # Set the edge color to black
    legend.get_frame().set_alpha(0.9)  # Make the legend fully opaque

    ### Make sure there is no empty space around the plot
    plt.tight_layout()
    # Save the figure as a PNG file with a high resolution (300 DPI) and close the plot to free up memory
    name = 'Stl_'+network_style+'_instance_map.png'
    folder_name = 'figures_'+network_style
    folder = os.path.join(os.path.dirname(__file__),'figures', folder_name)
    if not os.path.exists(folder):  # Check if the folder exists
        os.makedirs(folder)  # Create the folder if it doesn't exist
    completename = os.path.join(os.path.dirname(__file__),'figures', folder_name, name)
    plt.savefig(completename, dpi=300)
    plt.close()

# Plot the map with the specified routes using dynamic extent
# for network_style in ['151', 'corridor','low_frequency', 'all', 'grid', 'radial']:
for network_style in get_route_dictionary().keys():
    plot_map_with_dynamic_extent(network_style = network_style)
    analyze_network(network_style = network_style, route_ids = get_route_dictionary()[network_style])