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
contrasting_color_palette =  ['red', 'blue', 'green', 'deeppink', 'dodgerblue']
fourty_colors_paletter = ['red', 'blue', 'green', 'brown','purple', 'darkcyan',  'gray', 'olive', 'cyan', 'black', 'pink', 'orange', 'yellow', 'magenta', 'lime', 'teal', 'indigo', 'maroon', 'navy', 'peru', 'plum', 'salmon', 'sienna', 'tan', 'thistle', 'tomato', 'turquoise', 'violet', 'wheat', 'yellowgreen', 'aquamarine', 'bisque', 'blueviolet', 'burlywood', 'cadetblue', 'chartreuse', 'chocolate', 'coral', 'cornflowerblue', 'cornsilk', 'crimson']

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
            lat_offset, lon_offset = 0, 0 # Remove offsets for now

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
            ax.scatter(stop_data['stop_lon'], stop_data['stop_lat'], color='black', s=60, marker='.', linewidths=0.5, zorder=10)

def mark_metro_stations(stops_data, ax, stop_connections):
    """
    Mark metro stations on the map by selecting one representative stop from each set of connected stops
    that contain 'METRO' in their name, and show its stop_name as a label.
    """
    color = 'red'
    marker_shape = '^'
    label_size = 14
    marker_size = 150

    metro_stations = [(47911,'Cartier',-73.682497,45.559958, 45.565, 'center'),
                      (41006,'Concorde',-73.70785,45.561048,45.564, 'center'),
                      (48002,'Montmorrency',-73.720829,45.557936, 45.55, 'center')]
    for stop_id, stop_name, lon, lat, lat2, alignment in metro_stations:
        ax.scatter(lon, lat, color=color, s=marker_size, marker=marker_shape, zorder=10)
        # ax.text(lon, lat2, stop_name, fontsize=label_size, ha=alignment, color=color, zorder=10)

def plot_map_with_dynamic_extent(route_ids, other_routes =[], offset_distance=0.0004, padding=0.01, radial = False):
    """
    Plot the map with thinner transfer stop markers, an updated legend, and dynamic extent to focus on the plotted routes.
    The padding parameter controls how much extra space is added around the routes.
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(Image.open(background_image_path), extent=[map_bounds[3], map_bounds[2], map_bounds[1], map_bounds[0]])
    route_stop_lists = {}
    plotted_routes = []  # Track plotted routes to handle offsets for shared segments
    lat_min, lat_max = float('inf'), float('-inf')
    lon_min, lon_max = float('inf'), float('-inf')

    offsets_applied = {}  # Track the offsets applied to each route for first and last stop adjustment

    for idx, route_id in enumerate(other_routes):
        if route_id in route_ids:
            continue
        color = 'saddlebrown'

        # Get the shape points for the current route
        shape_points = get_first_shape_for_route(route_id, shapes_df)
        if shape_points is None: 
            continue

        # Get the ordered list of stops for the current route
        ordered_stop_list = get_ordered_stop_list(route_id, new_trips_df, new_stop_times_df)

        # Plot the adjusted shape
        print('route_id', route_id)
        latitudes = shape_points['shape_pt_lat'].values
        longitudes = shape_points['shape_pt_lon'].values
        # ax.plot(longitudes, latitudes, color=color, linewidth=1.5, zorder=2, label="Feeder lines")

        # Plot the route stops
        # stops_data = stops_df[stops_df['stop_id'].isin(ordered_stop_list)]
        # ax.scatter(stops_data['stop_lon'], stops_data['stop_lat'], color=color, s=30, marker='.', linewidths=0.5, zorder=10)
        
    for idx, route_id in enumerate(route_ids):
        color = contrasting_color_palette[idx % len(contrasting_color_palette)]
        if color == 'black':
            color = 'dodgerblue'
        color = 'blue'

        # Get the shape points for the current route
        shape_points = get_first_shape_for_route(route_id, shapes_df)

        # Get the ordered list of stops for the current route
        ordered_stop_list = get_ordered_stop_list(route_id, new_trips_df, new_stop_times_df)
        route_stop_lists[route_id] = ordered_stop_list

        # Update the lat/lon boundaries for dynamic extent calculation
        print('route_id', route_id)
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
                    lat_offset = 0
                    latitudes += lat_offset
                else:  # More vertical
                    lon_offset = offset_distance * (idx % 2 * 2 - 1)  # Apply offset to longitude
                    lon_offset = 0
                    longitudes += lon_offset

        # Store the offsets for use when plotting the first and last stops
        offsets_applied[route_id] = (lat_offset, lon_offset)

        # Plot the adjusted shape
        ## Get route_id without last caracter
        route_name = route_id[:-1]
        ax.plot(longitudes, latitudes, label=f"Line {route_name}", color=color, linewidth=2, zorder=3)

        # Plot the route stops
        # stops_data = stops_df[stops_df['stop_id'].isin(ordered_stop_list)]
        # ax.scatter(stops_data['stop_lon'], stops_data['stop_lat'], color=color, s=50, marker='.', linewidths=0.5, zorder=10)
        plotted_routes.append(route_id)

    # Mark the first and last stops with applied offsets
    # mark_first_and_last_stops_with_offsets(route_stop_lists, stops_df, ax, route_ids, color_palette=contrasting_color_palette, offsets_applied=offsets_applied)

    # Load available connections and mark transfer and connecting stops
    stop_connections = load_connections(connections_file_path)
    mark_transfer_and_connecting_stops(route_stop_lists, stops_df, ax, stop_connections)

    # Mark metro stations on the map
    mark_metro_stations(stops_df, ax, stop_connections)                                      

    # Add legend entries for first/last stops and transfer stops
    # ax.scatter([], [], color='none', edgecolor='black', s=60, marker='o', label="First/Last Stop", zorder=5)
    ax.scatter([], [], color='black', s=20, marker='.', linewidths=0.5, label = "Transfer stop \nbetween main lines", zorder=10)
    ax.scatter([], [], color='red', s = 100, marker='^', label = "Metro Station", zorder=2)
    ## Add legend handle with only one color for all routes
    ax.plot([], [], color='blue', linewidth=2, label="Main lines", zorder=3)

    # Adjust map extent to fit the plotted routes with some padding
    # Make sure to stay in map bounds
    lat_min = max(lat_min - padding, map_bounds[1])
    lat_max = min(lat_max + padding, map_bounds[0])
    lon_min = max(lon_min - padding, map_bounds[3])
    lon_max = min(lon_max + padding, map_bounds[2])
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)

    #Set x and y ticks (longitude and latitude) for the map and their size
    ### x and y ticks should be space by 0.05 and rounded to the second decimal
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
    if radial: 
        title = "Radial style instance including transfer stops"
    else:
        title = "Map of main lines in case study network of Laval, Canada"
    ax.set_title(title, fontsize=18)
    # Add a legend with a white background and black border
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))

    # Create the legend with unique labels
        # Create a custom legend with only the desired entries
    handles, labels = ax.get_legend_handles_labels()  # Get all handles and labels
    desired_labels = ["Main lines", "Metro Station", "Transfer stop \nbetween main lines",   "Feeder lines"]
    desired_handles = [handles[labels.index(label)] for label in desired_labels if label in labels]  # Filter handles

    # Set the legend with only the desired handles and labels
    legend = ax.legend(handles=desired_handles, labels=desired_labels, loc='best', fontsize=14, markerscale=1.5)
    # legend = ax.legend(unique.values(), unique.keys(), loc = 'best', fontsize = 14, markerscale = 1.5)
    legend.get_frame().set_facecolor('white')  # Set the background color to white
    legend.get_frame().set_edgecolor('black')  # Set the edge color to black
    legend.get_frame().set_alpha(1)  # Make the legend fully opaque

    ### Make sure there is no empty space around the plot
    plt.tight_layout()

    if radial:
        name = 'stl_radial_instance_map'
    else:
        name = 'stl_grid_instance_map'
    completename = os.path.join(os.path.dirname(__file__),'figures', name+'.png')
    plt.savefig(completename, dpi=300)
    # plt.show()
    plt.close()

# Define the route_ids to plot
# Route ids for a quadrant style network
route_ids = [ '17N', '151N', '26O', '42E', '56O']
route_ids = ['144E', '20E', '222E', '22E', '24E', '252E', '26E', '2E', '36E', '42E', '52E', '56E', '60E', '66E', '70E', '74E', '76E', '151S', '17S', '27S', '33S', '37S', '43S', '45S','46S', '55S', '61S', '63S', '65S', '901S', '902S', '903S','925S']
# #Route ids for a radial style network
# route_ids = ['70E', '31S', '37S', '39S', '33S']

# Read all other routes from new_trips_df
other_routes = new_trips_df['route_id'].unique()
other_routes = [route_id for route_id in other_routes if route_id not in route_ids]


# Plot the map with the specified routes using dynamic extent
plot_map_with_dynamic_extent(route_ids, other_routes=other_routes, radial = False)


