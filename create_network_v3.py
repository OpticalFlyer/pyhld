#!/usr/bin/env python3

import geopandas as gpd
import networkx as nx
import time
from shapely.geometry import LineString

print("Building the graph...")

# Load shapefiles
edges_gdf = gpd.read_file('edges.shp')
nodes_gdf = gpd.read_file('nodes.shp').set_index('id')
home_points_gdf = gpd.read_file('home_points.shp')
fdh_gdf = gpd.read_file('fdh.shp')  # Load fdh.shp

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

# Create a new graph to store paths and a list for circuits
home_graph = nx.Graph()
circuits_data = []

total = len(home_points_gdf)
counter = 0

# Start the timer
start_time = time.time()

# Temporary copy of G to modify for each pathfinding operation, excluding home nodes initially
G_temp = G.copy()
G_temp.remove_nodes_from(home_nodes)

# Find the minimum cost path from each home node to its associated FDH node and construct circuits
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
                # Calculate total cost for the path
                path_cost = sum(G_temp[path[i]][path[i+1]]['cost'] for i in range(len(path)-1))
                path_geoms = [nodes_gdf.loc[node, 'geometry'] for node in path if node in nodes_gdf.index]
                if len(path_geoms) > 1:  # Ensure there are at least two points to form a line
                    linestring = LineString(path_geoms)
                    circuits_data.append({
                        'geometry': linestring,
                        'home_node': start_node,
                        'fdh_id': fdh_id,
                        'cost': path_cost  # Include the total path cost
                    })
                for i in range(len(path) - 1):
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

# Create GeoDataFrame for circuits and save as shapefile
circuits_gdf = gpd.GeoDataFrame(circuits_data, crs=edges_gdf.crs)
circuits_gdf.to_file('circuits.shp')

print("\nDone.")
