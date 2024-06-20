#!/usr/bin/env python3

import geopandas as gpd
import pandas as pd
import numpy as np

print("Associating home points to drop points and updating node types...")

# Load the NODES and HOME_POINT shapefiles
nodes_gdf = gpd.read_file('nodes.shp')
home_points_gdf = gpd.read_file('home_points.shp')

# Ensure 'drop_point' and 'type' columns exist
home_points_gdf['drop_point'] = pd.NA
nodes_gdf['type'] = None

def find_nearest_node(home_point, nodes):
    # Calculate distances from the home point to all nodes
    distances = nodes.geometry.distance(home_point.geometry)
    # Find the index of the minimum distance
    closest_node_index = distances.idxmin()
    # Return the ID of the closest node
    return nodes.iloc[closest_node_index].id

# Vectorize the find_nearest_node function if possible or use apply as a fallback
try:
    # Attempt to use a vectorized approach for performance
    home_points_gdf['drop_point'] = np.vectorize(find_nearest_node)(home_points_gdf.geometry, nodes_gdf)
except Exception as e:
    # Fallback to using apply if the vectorized approach fails
    home_points_gdf['drop_point'] = home_points_gdf.apply(lambda x: find_nearest_node(x, nodes_gdf), axis=1)

# Update nodes 'type' based on associated home points
unique_drop_points = home_points_gdf['drop_point'].unique()
nodes_gdf.loc[nodes_gdf['id'].isin(unique_drop_points), 'type'] = 'HP'

# Save the updated GeoDataFrames back to shapefiles
home_points_gdf.to_file('home_points.shp', overwrite=True)
nodes_gdf.to_file('nodes.shp', overwrite=True)

print("Done.")
