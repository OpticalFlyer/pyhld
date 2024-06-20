#!/usr/bin/env python3

import geopandas as gpd
from scipy.spatial import KDTree
from shapely.geometry import Point, LineString
from shapely.ops import nearest_points
import numpy as np

# Load home points from a shapefile
home_points_gdf = gpd.read_file('home_points.shp')

# Load network lines from a shapefile
network_gdf = gpd.read_file('network.shp')

# Filter network lines by type
network_gdf = network_gdf[(network_gdf['type'] == 'Underground') | (network_gdf['type'] == 'Aerial')]

# Extract coordinates as a NumPy array
coords = np.array(list(zip(home_points_gdf.geometry.x, home_points_gdf.geometry.y)))

# Create a KDTree for fast nearest neighbor search
tree = KDTree(coords)

# Parameters for clustering
distance_threshold = 700  # feet
max_homes_per_cluster = 9

# Initialize clusters and a flag for each home indicating if it has been assigned to a cluster
clusters = []
is_clustered = np.zeros(len(home_points_gdf), dtype=bool)

# Greedy clustering
for i, coord in enumerate(coords):
    if is_clustered[i]:
        continue

    # Find all points within the distance threshold
    indices = tree.query_ball_point(coord, r=distance_threshold)
    
    # Remove points that are already clustered
    indices = [idx for idx in indices if not is_clustered[idx]]
    
    # If more points than max cluster size, keep only the nearest ones
    if len(indices) > max_homes_per_cluster:
        distances, nearest_indices = tree.query(coord, k=max_homes_per_cluster)
        indices = nearest_indices.tolist()
    
    # Create the cluster and update the flags
    clusters.append(indices)
    is_clustered[indices] = True

# Function to snap point to nearest line
def snap_to_nearest_line(point, lines_gdf):
    nearest_line = None
    min_distance = float('inf')

    for line in lines_gdf.geometry:
        if line.distance(point) < min_distance:
            nearest_line = line
            min_distance = line.distance(point)

    nearest_point_on_line = nearest_points(point, nearest_line)[1]
    return nearest_point_on_line

# Calculate the centroids for each cluster and snap to nearest line
cluster_centroids = []
for cluster_indices in clusters:
    cluster_coords = coords[cluster_indices]
    centroid = Point(np.mean(cluster_coords[:, 0]), np.mean(cluster_coords[:, 1]))
    snapped_point = snap_to_nearest_line(centroid, network_gdf)
    cluster_centroids.append({'geometry': snapped_point})

# Create a GeoDataFrame for cluster centroids
clusters_gdf = gpd.GeoDataFrame(cluster_centroids, crs=home_points_gdf.crs)

# Save the cluster centroids to mst.shp
clusters_gdf.to_file('mst.shp')

# Add a new attribute 'mst' to the home points GeoDataFrame
home_points_gdf['mst'] = None

# Assign the 'mst' id from the clusters to the corresponding home points
for idx, cluster_indices in enumerate(clusters):
    home_points_gdf.loc[cluster_indices, 'mst'] = idx

# Save the home points with the 'mst' attribute to a new shapefile (home_points_clustered.shp)
home_points_gdf.to_file('home_points_clustered.shp')

print(f"{len(clusters)} clusters have been created and saved to mst.shp.")
