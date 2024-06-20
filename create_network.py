#!/usr/bin/env python3

import geopandas as gpd
import networkx as nx
import time

print("Building the graph...")

# Load shapefiles
edges_gdf = gpd.read_file('edges.shp')
nodes_gdf = gpd.read_file('nodes.shp')
home_points_gdf = gpd.read_file('home_points.shp')

# Build the graph
G = nx.Graph()
for _, edge in edges_gdf.iterrows():
    G.add_edge(edge['start_node'], edge['end_node'], weight=edge['cost'], type=edge['type'], length=edge['length'], cost=edge['cost'])

# Identify home nodes
home_nodes = set(home_points_gdf['drop_point'].dropna())

# Create a new graph that only contains the home nodes
home_graph = nx.Graph()

total = len(home_nodes)
counter = 0

target_node = '202'

# Store the edges connected to home nodes
home_node_edges = {}
for node in home_nodes:
    home_node_edges[node] = list(G.edges(node, data=True))

# Remove all home nodes from the graph
G_temp = G.copy()
G_temp.remove_nodes_from(home_nodes)

# Start the timer
start_time = time.time()

# Find the minimum cost path from each home node to the target node
for start_node in home_nodes:
    # Add the current start node back to the graph along with its edges
    G_temp.add_node(start_node)
    G_temp.add_edges_from(home_node_edges[start_node])

    try:
        path = nx.shortest_path(G_temp, start_node, target_node, weight='cost')
        for i in range(len(path) - 1):
            home_graph.add_edge(path[i], path[i+1])
    except nx.NetworkXNoPath:
        pass
    finally:
        # Remove the start node again
        G_temp.remove_node(start_node)

    counter += 1
    print(f'Progress: {counter}/{total}', end='\r')

# Stop the timer and print the elapsed time
end_time = time.time()
elapsed_time = end_time - start_time
print(f"\nDone in {elapsed_time:.2f} seconds.")

# Create a GeoDataFrame for the network
network_data = []

# Iterate over the edges in the home_graph and use edge geometry from edges.shp
for edge in home_graph.edges():
    start_node, end_node = edge
    edge_data = edges_gdf[((edges_gdf['start_node'] == start_node) & (edges_gdf['end_node'] == end_node)) | ((edges_gdf['start_node'] == end_node) & (edges_gdf['end_node'] == start_node))]
    if not edge_data.empty:
        edge_geom = edge_data.iloc[0]['geometry']
        network_data.append({'geometry': edge_geom, 'type': edge_data.iloc[0]['type'], 'length': edge_data.iloc[0]['length'], 'cost': edge_data.iloc[0]['cost']})

network_gdf = gpd.GeoDataFrame(network_data, crs=edges_gdf.crs)
network_gdf.to_file('network.shp')
