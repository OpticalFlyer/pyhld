#!/usr/bin/env python3

import networkx as nx
import geopandas as gpd

print("Building the graph...")

# Load shapefiles
edges_gdf = gpd.read_file('edges.shp')
nodes_gdf = gpd.read_file('nodes.shp')

# Build the graph
G = nx.Graph()
for _, edge in edges_gdf.iterrows():
    G.add_edge(edge['start_node'], edge['end_node'], weight=edge['cost'], type=edge['type'], length=edge['length'], cost=edge['cost'])

# Get connected components
components = list(nx.connected_components(G))

# Check if the graph is fully connected
if len(components) == 1:
    print("The graph is fully connected.")
else:
    num_components = len(components)
    print(f"The graph is not fully connected. It has {num_components} connected components.")
    for i, component in enumerate(components):
        print(f"Connected Component {i + 1}: {component}")

# Print nodes that are not connected
if len(components) > 1:
    isolated_nodes = set(G.nodes()) - set.union(*components)
    print(f"Isolated Nodes (not connected to any component): {isolated_nodes}")
