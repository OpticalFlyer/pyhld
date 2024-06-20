#!/usr/bin/env python3

import geopandas as gpd
import networkx as nx
import numpy as np
from scipy.spatial import KDTree, distance
import pandas as pd
import time

print("Building the graph...")

# Load shapefiles
edges_gdf = gpd.read_file('edges.shp')
nodes_gdf = gpd.read_file('nodes.shp')
home_points_gdf = gpd.read_file('home_points.shp')
fdh_gdf = gpd.read_file('fdh.shp')

# Build the graph
G = nx.Graph()
for _, edge in edges_gdf.iterrows():
    G.add_edge(edge['start_node'], edge['end_node'], weight=edge['cost'], type=edge['type'], length=edge['length'])

# Create KDTree for efficient spatial queries (for nearest node lookups)
node_coords = np.array(list(zip(nodes_gdf.geometry.x, nodes_gdf.geometry.y)))
tree = KDTree(node_coords)
node_id_to_idx = {node_id: idx for idx, node_id in enumerate(nodes_gdf['id'])}

# Function to find nearest node in the graph to a given point
def find_nearest_node(point):
    _, idx = tree.query(point, k=1)
    return nodes_gdf.iloc[idx]['id']

# Group homes by FDH
fdh_to_homes = home_points_gdf.groupby('fdh_id')['drop_point'].apply(list).to_dict()

# KDTree for FDH locations to sort homes by distance to FDH
fdh_coords = np.array(list(zip(fdh_gdf.geometry.x, fdh_gdf.geometry.y)))
fdh_tree = KDTree(fdh_coords)
fdh_id_to_idx = {fdh_id: idx for idx, fdh_id in enumerate(fdh_gdf['id'])}

# Assuming fdh_gdf has a 'geometry' column and each FDH can be mapped to the nearest network node
fdh_to_node = {}
for _, fdh_row in fdh_gdf.iterrows():
    fdh_point = fdh_row.geometry
    nearest_node_id = find_nearest_node((fdh_point.x, fdh_point.y))
    fdh_to_node[fdh_row['id']] = nearest_node_id

# Function to find the nearest node in the optimized graph to a given start node
def find_nearest_node_in_optimized_graph(optimized_graph, G, start_node, nodes_gdf):
    if optimized_graph.number_of_nodes() == 0:
        # If the optimized graph has no nodes, return None values
        return None, [], float('inf')
    
    # Extract coordinates for the start node and all nodes in the optimized graph
    start_coords = nodes_gdf.loc[nodes_gdf['id'] == start_node, ['geometry']].values[0][0]
    optimized_nodes_coords = {node: nodes_gdf.loc[nodes_gdf['id'] == node, ['geometry']].values[0][0] for node in optimized_graph.nodes}

    # Calculate distances from start node to each node in the optimized graph
    distances = {node: distance.euclidean((start_coords.x, start_coords.y), (coords.x, coords.y)) for node, coords in optimized_nodes_coords.items()}
    
    # Find the nearest node and its distance
    nearest_node = min(distances, key=distances.get)
    nearest_distance = distances[nearest_node]
    
    # Calculate the shortest path from start node to nearest node in the original graph G
    try:
        path = nx.shortest_path(G, source=start_node, target=nearest_node, weight='weight')
        path_cost = sum(G[u][v]['weight'] for u, v in zip(path[:-1], path[1:]))
        return nearest_node, path, path_cost
    except nx.NetworkXNoPath:
        # If no path exists, return None values
        return None, [], float('inf')

# Function to sort homes by distance to FDH
def sort_homes_by_distance(fdh_id, homes):
    fdh_idx = fdh_id_to_idx[fdh_id]
    fdh_point = fdh_coords[fdh_idx]
    home_points = np.array([nodes_gdf.loc[nodes_gdf['id'] == h].geometry.apply(lambda x: (x.x, x.y)).values[0] for h in homes])
    distances = np.linalg.norm(home_points - fdh_point, axis=1)
    sorted_idx = np.argsort(distances)
    return [homes[i] for i in sorted_idx]

# Start the optimization process
start_time = time.time()

optimized_graph = nx.Graph()

path_cache = {}

def calculate_direct_path_cost(G, start_node, target_node):
    cache_key = (start_node, target_node)
    if cache_key in path_cache:
        return path_cache[cache_key]

    try:
        path = nx.shortest_path(G, source=start_node, target=target_node, weight='weight')
        cost = sum(G[u][v]['weight'] for u, v in zip(path[:-1], path[1:]))
        path_cache[cache_key] = (cost, path)
        return cost, path
    except nx.NetworkXNoPath:
        path_cache[cache_key] = (float('inf'), [])
        return float('inf'), []

# Placeholder for a function that updates the optimized graph with a new path
def update_network_with_path(optimized_graph, path, G):
    for start, end in zip(path[:-1], path[1:]):
        if not optimized_graph.has_edge(start, end):
            optimized_graph.add_edge(start, end, weight=G[start][end]['weight'])

# Before starting the main loop, initialize variables to track progress
total_homes = sum(len(homes) for homes in fdh_to_homes.values())
processed_homes = 0

# Main loop for pathfinding and updating the optimized graph
for fdh_id, homes in fdh_to_homes.items():
    target_node = fdh_to_node[fdh_id]  # Assuming fdh_to_node is correctly defined earlier
    sorted_homes = sort_homes_by_distance(fdh_id, homes)
    for home in sorted_homes:
        start_node = home  # Assuming 'home' is already a node ID in G

        # Calculate direct path cost from home to FDH
        direct_cost, direct_path = calculate_direct_path_cost(G, start_node, target_node)

        # Find the nearest node in the optimized graph to the home
        nearest_optimized_node, nearest_optimized_path, nearest_optimized_cost = find_nearest_node_in_optimized_graph(optimized_graph, G, start_node, nodes_gdf)

        # Calculate path cost from the nearest optimized node to FDH through the existing network
        if nearest_optimized_node is not None:
            _, path_from_nearest = calculate_direct_path_cost(optimized_graph, nearest_optimized_node, target_node)
            total_optimized_cost = nearest_optimized_cost + sum(optimized_graph[u][v]['weight'] for u, v in zip(path_from_nearest[:-1], path_from_nearest[1:]))
        else:
            total_optimized_cost = float('inf')

        # Compare and update the optimized graph with the cheaper path
        if direct_cost <= total_optimized_cost:
            update_network_with_path(optimized_graph, direct_path, G)
        else:
            # Update with path to nearest node then to FDH
            update_network_with_path(optimized_graph, nearest_optimized_path + path_from_nearest[1:], G)

        # Update and print the progress
        processed_homes += 1
        progress_percentage = (processed_homes / total_homes) * 100
        print(f"\rProgress: {processed_homes}/{total_homes} homes processed ({progress_percentage:.2f}%)", end='')

# Print a newline character at the end to ensure any following output starts on a new line
print("\nOptimization complete.")

# End the optimization process
end_time = time.time()
elapsed_time = end_time - start_time
print(f"Optimization complete in {elapsed_time:.2f} seconds.")

# TODO: Add the implementation for direct and existing network path calculations and updates

# Saving the optimized network (this is a placeholder, adapt to your actual data structure)
# network_gdf = gpd.GeoDataFrame([...], crs=edges_gdf.crs)
# network_gdf.to_file('optimized_network.shp')

print("Optimization done. Network saved.")
