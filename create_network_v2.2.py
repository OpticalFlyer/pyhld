#!/usr/bin/env python3

import geopandas as gpd
import networkx as nx
import time
from shapely.geometry import box

# Load shapefiles
edges_gdf = gpd.read_file('edges.shp')
nodes_gdf = gpd.read_file('nodes.shp')
home_points_gdf = gpd.read_file('home_points.shp')
fdh_gdf = gpd.read_file('fdh.shp')

print("Grouping homes by FDH and sorting by distance to FDH...")

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

# Group home points by FDH
fdh_to_homes = {}
for _, home_point in home_points_gdf.iterrows():
    fdh_id = home_point['fdh_id']
    if fdh_id not in fdh_to_homes:
        fdh_to_homes[fdh_id] = []
    fdh_to_homes[fdh_id].append(home_point['drop_point'])

# Before starting the sorting, ensure the graph is ready
G_temp = G.copy()
G_temp.remove_nodes_from(home_nodes)  # Initially remove all home nodes

# Sort homes within each FDH group by proximity to FDH
for fdh_id, homes in fdh_to_homes.items():
    target_node = fdh_to_node.get(fdh_id)
    if target_node:
        homes_with_distance = []
        for home in homes:
            if home in home_node_edges:
                # Temporarily add back the home node and its edges for distance calculation
                G_temp.add_node(home)
                G_temp.add_edges_from(home_node_edges[home])

                try:
                    # Calculate distance only if both nodes are present
                    if G_temp.has_node(home) and G_temp.has_node(target_node):
                        distance = nx.shortest_path_length(G_temp, source=home, target=target_node, weight='length')
                        homes_with_distance.append((home, distance))
                except nx.NetworkXNoPath:
                    print(f"No path found from home node {home} to FDH node {target_node}.")
                finally:
                    # Remove the home node again to ensure it's not included in the next home's calculation
                    G_temp.remove_node(home)

        # Sort homes by calculated distance
        homes_sorted = sorted(homes_with_distance, key=lambda x: x[1])
        fdh_to_homes[fdh_id] = [home for home, _ in homes_sorted]  # Update with sorted homes

# Create a new graph to store paths
home_graph = nx.Graph()

# Start the timer
print("Building the network...")
start_time = time.time()

# Process each FDH group
# Ensure nodes_gdf is indexed by node ID for efficient lookup
nodes_gdf = nodes_gdf.set_index('id')
nodes_sindex = nodes_gdf.sindex

for fdh_id, homes in fdh_to_homes.items():
    print(f"Processing FDH {fdh_id} with {len(homes)} homes...")
    target_node = fdh_to_node.get(fdh_id)
    if not target_node:
        continue

    G_temp = G.copy()
    G_temp.remove_nodes_from(home_nodes)  # Exclude home nodes

    for start_node in homes:
        if start_node in home_node_edges and start_node in nodes_gdf.index:
            start_geom = nodes_gdf.loc[start_node, 'geometry']
            
            G_temp.add_node(start_node)
            G_temp.add_edges_from(home_node_edges[start_node])

            try:
                path_to_fdh = nx.shortest_path(G_temp, start_node, target_node, weight='cost')
                path_to_fdh_cost = sum(G_temp[path_to_fdh[i]][path_to_fdh[i+1]]['cost'] for i in range(len(path_to_fdh)-1))

                alternate_path_cost = float('inf')
                alternate_path = []

                nearest_items = list(nodes_sindex.nearest(start_geom, 1))  # Using start_geom directly
                if nearest_items:
                    nearest_item_index = nearest_items[0]
                    nearest_node_id = nodes_gdf.iloc[nearest_item_index].index  # Correctly access the index of the GeoDataFrame
                    
                    if nearest_node_id != start_node and nearest_node_id in G_temp:
                        path = nx.shortest_path(G_temp, start_node, nearest_node_id, weight='cost')
                        path_cost = sum(G_temp[path[i]][path[i+1]]['cost'] for i in range(len(path)-1))
                        if path_cost < alternate_path_cost:
                            alternate_path_cost = path_cost
                            alternate_path = path
                    else:
                        print(f"Nearest node {nearest_node_id} is not a valid node in the graph.")
                else:
                    print(f"No nearest node found for home node {start_node}.")

                final_path = path_to_fdh if path_to_fdh_cost <= alternate_path_cost else alternate_path

                for i in range(len(final_path)-1):
                    home_graph.add_edge(final_path[i], final_path[i+1], weight=G[final_path[i]][final_path[i+1]]['cost'], fdh_id=fdh_id)
            
            except nx.NetworkXNoPath:
                print(f"No path found from home node {start_node} to FDH node {target_node}.")
            finally:
                G_temp.remove_node(start_node)


# Stop the timer and print the elapsed time
end_time = time.time()
elapsed_time = end_time - start_time
print(f"\nNetwork complete in {elapsed_time:.2f} seconds.")

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