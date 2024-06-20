#!/usr/bin/env python3

import geopandas as gpd
import pandas as pd
import itertools
from shapely.geometry import Point

print("Creating nodes...")

# Load the EDGES shapefile
edges_gdf = gpd.read_file('edges.shp')

# Prepare a GeoDataFrame for the NODES
nodes_gdf = gpd.GeoDataFrame(columns=['id', 'geometry'], crs=edges_gdf.crs)

# Prepare fields for start_node and end_node in the EDGES GeoDataFrame
edges_gdf['start_node'] = None
edges_gdf['end_node'] = None

# To store the unique nodes
unique_nodes = {}

# Using itertools.count to generate unique IDs
id_counter = itertools.count(start=1)

# Define a tolerance threshold for coordinate comparison
epsilon = 2

# Function to handle node creation and ID assignment
def handle_node(point, unique_nodes, nodes_gdf):
    for existing_point, node_id in unique_nodes.items():
        if abs(point[0] - existing_point[0]) < epsilon and abs(point[1] - existing_point[1]) < epsilon:
            return unique_nodes, nodes_gdf, node_id
    
    node_id = next(id_counter)
    unique_nodes[point] = node_id
    node_df = gpd.GeoDataFrame({'id': [node_id], 'geometry': [Point(point)]}, crs=edges_gdf.crs)
    nodes_gdf = pd.concat([nodes_gdf, node_df], ignore_index=True)
    return unique_nodes, nodes_gdf, node_id

for index, edge in edges_gdf.iterrows():
    start_point, end_point = edge.geometry.coords[0], edge.geometry.coords[-1]
    
    # Handle start node
    unique_nodes, nodes_gdf, start_node_id = handle_node(start_point, unique_nodes, nodes_gdf)

    # Handle end node
    unique_nodes, nodes_gdf, end_node_id = handle_node(end_point, unique_nodes, nodes_gdf)

    # Populate the start_node and end_node fields for the EDGES GeoDataFrame
    edges_gdf.at[index, 'start_node'] = start_node_id
    edges_gdf.at[index, 'end_node'] = end_node_id

# Save the NODES GeoDataFrame to a new shapefile
nodes_gdf.to_file('nodes.shp')
print("Nodes have been saved to nodes.shp.")

# Optionally, save the updated EDGES GeoDataFrame with start_node and end_node attributes
edges_gdf.to_file('edges.shp')
print("Edges with node attributes have been saved to edges.shp.")
print("Done.")
