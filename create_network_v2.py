#!/usr/bin/env python3

import geopandas as gpd
import networkx as nx
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
    G.add_edge(edge['start_node'], edge['end_node'], weight=edge['cost'], type=edge['type'], length=edge['length'], cost=edge['cost'])

# Create a mapping from fdh_id to node_id for quick lookup
fdh_to_node = fdh_gdf.set_index('id')['node_id'].to_dict()

# Identify home nodes
home_nodes = set(home_points_gdf['drop_point'].dropna())

# Store the edges connected to home nodes for re-adding later
home_node_edges = {}
for node in home_nodes:
    home_node_edges[node] = list(G.edges(node, data=True))

# Create a new graph to store paths
home_graph = nx.Graph()

total = len(home_points_gdf)
counter = 0

# Start the timer
start_time = time.time()

# Temporary copy of G to modify for each pathfinding operation, excluding home nodes initially
G_temp = G.copy()
G_temp.remove_nodes_from(home_nodes)

# Find the minimum cost path from each home node to its associated FDH node
for _, home_point in home_points_gdf.iterrows():
    start_node = home_point['drop_point']
    fdh_id = home_point['fdh_id']
    if fdh_id in fdh_to_node and start_node in home_node_edges:
        target_node = fdh_to_node[fdh_id]  # Lookup the target_node using fdh_id
        
        # Temporarily add the start node and its edges back to G_temp for pathfinding
        G_temp.add_node(start_node)
        G_temp.add_edges_from(home_node_edges[start_node])
        
        try:
            if G_temp.has_node(target_node):  # Ensure the target FDH node exists in the graph
                path = nx.shortest_path(G_temp, start_node, target_node, weight='cost')
                for i in range(len(path) - 1):
                    #home_graph.add_edge(path[i], path[i+1], weight=G[path[i]][path[i+1]]['cost'])
                    # Include fdh_id as an edge attribute
                    home_graph.add_edge(path[i], path[i+1], weight=G[path[i]][path[i+1]]['cost'], fdh_id=fdh_id)
        except nx.NetworkXNoPath:
            print(f"No path found from home node {start_node} to FDH node {target_node}.")
        finally:
            # Remove the start node again to reset G_temp for the next iteration
            G_temp.remove_node(start_node)

    counter += 1
    print(f'Progress: {counter}/{total}', end='\r')

# Stop the timer and print the elapsed time
end_time = time.time()
elapsed_time = end_time - start_time
print(f"\nGraph complete in {elapsed_time:.2f} seconds.")

print("Saving the network...")

# Extract edges data from the home_graph to create a GeoDataFrame
network_data = []

edge_counter = 0
total_edges = len(home_graph.edges(data=True))

for edge in home_graph.edges(data=True):
    start_node, end_node, edge_attrs = edge
    edge_data = edges_gdf[((edges_gdf['start_node'] == start_node) & (edges_gdf['end_node'] == end_node)) |
                           ((edges_gdf['start_node'] == end_node) & (edges_gdf['end_node'] == start_node))]
    if not edge_data.empty:
        fdh_id = edge_attrs['fdh_id']
        edge_geom = edge_data.iloc[0]['geometry']
        network_data.append({
            'geometry': edge_geom,
            'type': edge_data.iloc[0]['type'],
            'length': edge_data.iloc[0]['length'],
            'cost': edge_data.iloc[0]['cost'],
            'fdh_id': fdh_id
        })

        # Update the progress indicator
        edge_counter += 1
        print(f'Processing edge {edge_counter}/{total_edges}', end='\r')

network_gdf = gpd.GeoDataFrame(network_data, crs=edges_gdf.crs)
network_gdf.to_file('network.shp')

print("\nDone.")