#!/usr/bin/env python3

import geopandas as gpd
import networkx as nx
from scipy.spatial import distance_matrix
from shapely.geometry import LineString
import numpy as np
import pandas as pd

# Load the poles from a shapefile
poles_gdf = gpd.read_file('poles.shp')

# Extract the points coordinates for the distance matrix
points = np.array(list(zip(poles_gdf.geometry.x, poles_gdf.geometry.y)))

# Create a complete distance matrix
dist_matrix = distance_matrix(points, points)

# Create a complete graph from the distance matrix
G = nx.complete_graph(len(points))

# Add edges to the graph with distances as weights
for i, node in enumerate(G.nodes()):
    for j, neighbor in enumerate(G.nodes()):
        if i != j:  # skip if same node
            G[node][neighbor]['weight'] = dist_matrix[i][j]

# Compute the minimum spanning tree of the complete graph
mst = nx.minimum_spanning_tree(G)

# Generate the lines for the MST
mst_lines = []
for edge in mst.edges(data=False):
    point1 = points[edge[0]]
    point2 = points[edge[1]]
    line = LineString([point1, point2])
    mst_lines.append(line)

# Create a GeoDataFrame from the lines
lines_gdf = gpd.GeoDataFrame(geometry=mst_lines, crs=poles_gdf.crs)

# Save the lines to a new shapefile
lines_gdf.to_file('pole_lines.shp')

print("Pole lines have been saved to pole_lines.shp.")
