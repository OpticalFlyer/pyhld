#!/usr/bin/env python3

import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, box

# Load shapefiles
edges_gdf = gpd.read_file('edges.shp')
nodes_gdf = gpd.read_file('nodes.shp')
home_points_gdf = gpd.read_file('home_points.shp')

# Parameters for drop types
drop_length = {'Buried Drop': 1000, 'Aerial Drop': 1000}

# Initialize MST info, MST locations, and a structure to track homes to MST assignments
mst_info = {}
mst_locations = {}
mst_id_counter = 1
mst_to_homes = {}  # Correctly initialize mst_to_homes here

# Build initial graph
G = nx.Graph()
for _, edge in edges_gdf.iterrows():
    G.add_edge(edge['start_node'], edge['end_node'], weight=edge['cost'], type=edge['type'])

# Spatial indexing on nodes
nodes_gdf['geometry'] = nodes_gdf.apply(lambda row: Point(row['geometry'].x, row['geometry'].y), axis=1)
nodes_sindex = nodes_gdf.sindex

#Initialize a structure to hold MSTs and their assigned homes
mst_assignments = {}

# Function to determine the closest MST with available capacity
def find_closest_available_mst(home_point, max_length):
    closest_mst = None
    min_distance = float('inf')
    for mst_id, mst_data in mst_assignments.items():
        if len(mst_data['homes']) < 9:
            distance = home_point.distance(mst_data['geometry'])
            if distance <= max_length and distance < min_distance:
                min_distance = distance
                closest_mst = mst_id
    return closest_mst

# Build MST assignments
for _, home in home_points_gdf.iterrows():
    home_point = Point(home['geometry'].x, home['geometry'].y)
    max_length = 1000  # Adjusted allowable length

    # Attempt to find an existing MST within the allowable length with capacity
    closest_mst = find_closest_available_mst(home_point, max_length)
    
    if closest_mst:
        # Assign home to the closest available MST
        mst_assignments[closest_mst]['homes'].append(home['drop_point'])
    else:
        # Create a new MST for this home
        new_mst_id = f'MST_{len(mst_assignments) + 1}'
        mst_assignments[new_mst_id] = {'geometry': home_point, 'homes': [home['drop_point']]}

# Update home_points_gdf with assigned MST IDs
for mst_id, mst_data in mst_assignments.items():
    for home_id in mst_data['homes']:
        home_points_gdf.loc[home_points_gdf['drop_point'] == home_id, 'mst'] = mst_id

# Prepare and save the MST locations as a GeoDataFrame
mst_data = [{'mst_id': mst_id, 'geometry': mst_data['geometry']} for mst_id, mst_data in mst_assignments.items()]
mst_gdf = gpd.GeoDataFrame(mst_data, geometry='geometry', crs=home_points_gdf.crs)
mst_gdf.to_file('mstv2.shp')

# Save updated home points with MST ID
home_points_gdf.to_file('updated_home_points_with_mst.shp')