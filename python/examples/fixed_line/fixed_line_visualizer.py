import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np

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
contrasting_color_palette =  ['red', 'blue', 'green', 'brown','purple', 'darkcyan',  'gray', 'olive', 'cyan' ]

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
            ax.scatter(stop_data['stop_lon'], stop_data['stop_lat'], color='black', s=50, marker='.', linewidths=0.5, zorder=10)

def mark_metro_stations(stops_data, ax, stop_connections):
    """
    Mark metro stations on the map by selecting one representative stop from each set of connected stops
    that contain 'METRO' in their name, and show its stop_name as a label.
    """
    color = 'black'
    marker_size = 80
    marker_shape = '^'
    label_size = 10
    marker_size = 80

    metro_stations = [(47911,'Cartier',-73.682497,45.559958, 45.565, 'center'),
                      (41006,'Concorde',-73.70785,45.561048,45.564, 'center'),
                      (48002,'Montmorrency',-73.720829,45.557936, 45.55, 'center')]
    for stop_id, stop_name, lon, lat, lat2, alignment in metro_stations:
        ax.scatter(lon, lat, color=color, s=marker_size, marker=marker_shape, zorder=6)
        ax.text(lon, lat2, stop_name, fontsize=label_size, ha=alignment, color=color, zorder=10)

def plot_map_with_dynamic_extent(route_ids, offset_distance=0.0004, padding=0.01, radial = False):
    """
    Plot the map with thinner transfer stop markers, an updated legend, and dynamic extent to focus on the plotted routes.
    The padding parameter controls how much extra space is added around the routes.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.imshow(Image.open(background_image_path), extent=[map_bounds[3], map_bounds[2], map_bounds[1], map_bounds[0]])
    route_stop_lists = {}
    plotted_routes = []  # Track plotted routes to handle offsets for shared segments
    lat_min, lat_max = float('inf'), float('-inf')
    lon_min, lon_max = float('inf'), float('-inf')

    offsets_applied = {}  # Track the offsets applied to each route for first and last stop adjustment

    for idx, route_id in enumerate(route_ids):
        color = contrasting_color_palette[idx % len(contrasting_color_palette)]
        if color == 'black':
            color = 'dodgerblue'

        # Get the shape points for the current route
        shape_points = get_first_shape_for_route(route_id, shapes_df)

        # Get the ordered list of stops for the current route
        ordered_stop_list = get_ordered_stop_list(route_id, new_trips_df, new_stop_times_df)
        route_stop_lists[route_id] = ordered_stop_list

        # Update the lat/lon boundaries for dynamic extent calculation
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
                    latitudes += lat_offset
                else:  # More vertical
                    lon_offset = offset_distance * (idx % 2 * 2 - 1)  # Apply offset to longitude
                    longitudes += lon_offset

        # Store the offsets for use when plotting the first and last stops
        offsets_applied[route_id] = (lat_offset, lon_offset)

        # Plot the adjusted shape
        ax.plot(longitudes, latitudes, label=f"Route {route_id}", color=color, linewidth=2, zorder=3)

        # Plot the route stops
        stops_data = stops_df[stops_df['stop_id'].isin(ordered_stop_list)]
        ax.scatter(stops_data['stop_lon'], stops_data['stop_lat'], color=color, s=30, marker='.', linewidths=0.5, zorder=10)
        plotted_routes.append(route_id)

    # Mark the first and last stops with applied offsets
    mark_first_and_last_stops_with_offsets(route_stop_lists, stops_df, ax, route_ids, color_palette=contrasting_color_palette, offsets_applied=offsets_applied)

    # Load available connections and mark transfer and connecting stops
    stop_connections = load_connections(connections_file_path)
    mark_transfer_and_connecting_stops(route_stop_lists, stops_df, ax, stop_connections)

    # Mark metro stations on the map
    mark_metro_stations(stops_df, ax, stop_connections)                                      

    # Add legend entries for first/last stops and transfer stops
    ax.scatter([], [], color='none', edgecolor='black', s=60, marker='o', label="First/Last Stop", zorder=5)
    ax.scatter([], [], color='black', s=20, marker='.', linewidths=0.5, label = "Transfer Stop", zorder=10)
    ax.scatter([], [], color='black', s = 80, marker='^', label = "Metro Station", zorder=6)

    # Adjust map extent to fit the plotted routes with some padding
    ax.set_xlim(lon_min - padding, lon_max + padding)
    ax.set_ylim(lat_min - padding, lat_max + padding)

    # Set the title including route_ids and stops in Laval, Quebec
    if radial: 
        title = "Radial style instance including transfer stops"
    else:
        title = "Quadrant style instance including transfer stops"
    ax.set_title(title, fontsize=14)
    legend = ax.legend(loc = 'best', fontsize = 10, title = 'STL lines', markerscale = 1.5)
    legend.get_frame().set_facecolor('white')  # Set the background color to white
    legend.get_frame().set_edgecolor('black')  # Set the edge color to black
    legend.get_frame().set_alpha(1)  # Make the legend fully opaque
    if radial:
        name = 'stl_radial_instance_map'
    else:
        name = 'stl_quadrant_instance_map'
    completename = os.path.join(os.path.dirname(__file__),'figures', name+'.png')
    plt.savefig(completename, dpi=300)
    # plt.show()
    plt.close()

#Define the route_ids to plot
# Route ids for a quadrant style network
route_ids = ['24E', '17S', '151S', '56E', '42E']

# Plot the map with the specified routes using dynamic extent
plot_map_with_dynamic_extent(route_ids, radial = False)

#Route ids for a radial style network
route_ids = ['70E', '31S', '37S', '39S', '33S']

# Plot the map with the specified routes using dynamic extent 
plot_map_with_dynamic_extent(route_ids, radial = True)
