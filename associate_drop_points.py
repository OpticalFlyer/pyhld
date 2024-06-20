#!/usr/bin/env python3

import geopandas as gpd
import pandas as pd
from shapely.ops import nearest_points
import sys

print("Associating home points to drop points...")

# Load the NODES and HOME_POINT shapefiles
nodes_gdf = gpd.read_file('nodes.shp')
home_points_gdf = gpd.read_file('home_points.shp')

# Check if 'drop_point' column exists in home_points_gdf, if not add it
if 'drop_point' not in home_points_gdf.columns:
    home_points_gdf['drop_point'] = pd.NA

# Check if 'type' column exists in nodes_gdf, if not add it
if 'type' not in nodes_gdf.columns:
    nodes_gdf['type'] = None  # Initialize with None (or use pd.NA for pandas >= 1.0)

total_home_points = len(home_points_gdf)

# Iterating through each home point
for hp_index, home_point in home_points_gdf.iterrows():
    # Create a temporary DataFrame with distances to each node
    distances = nodes_gdf.geometry.apply(lambda node: home_point.geometry.distance(node))

    # Find the index of the closest node
    closest_node_index = distances.idxmin()

    # Get the ID of the closest node
    closest_node_id = nodes_gdf.iloc[closest_node_index]['id']

    # Update 'drop_point' for the home point
    home_points_gdf.at[hp_index, 'drop_point'] = closest_node_id

    # Mark the node as associated with a home point by setting its 'type' to 'HP'
    nodes_gdf.at[closest_node_index, 'type'] = 'HP'

    # Print progress indicator
    print(f"Processing home point {hp_index + 1}/{total_home_points}...", end='\r')
    sys.stdout.flush()  # Ensure the progress text is displayed immediately

# Save the updated home_points_gdf back to a shapefile, overwriting if it exists
home_points_gdf.to_file('home_points.shp', overwrite=True)

# Also, save the updated nodes_gdf with the 'type' attribute
nodes_gdf.to_file('nodes.shp', overwrite=True)

print("\nDone.")
