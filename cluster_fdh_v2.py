#!/usr/bin/env python3

import numpy as np
import geopandas as gpd
from scipy.cluster.hierarchy import fcluster, linkage
from shapely.geometry import Point
from shapely.ops import nearest_points

def exclude_outliers(data):
    """Exclude outliers using the IQR method."""
    if len(data) == 0:
        return np.array([], dtype=bool)
    Q1 = np.percentile(data, 25, axis=0)
    Q3 = np.percentile(data, 75, axis=0)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return (data >= lower_bound) & (data <= upper_bound)

def find_median_center(cluster_points):
    """Find the median center of a cluster, excluding outliers."""
    if len(cluster_points) == 0:
        return None, None
    outlier_mask = exclude_outliers(cluster_points)
    filtered_points = cluster_points[np.all(outlier_mask, axis=1)]
    median_x = np.median(filtered_points[:, 0])
    median_y = np.median(filtered_points[:, 1])
    return median_x, median_y

def snap_to_nearest_node(median_center, nodes):
    """Snap median center to the closest node where 'type' does not equal 'HP'."""
    # Filter nodes to exclude those with type 'HP'
    eligible_nodes = nodes[nodes['type'] != 'HP']
    # Find the nearest eligible node
    closest_node = eligible_nodes.geometry.unary_union
    closest_point = nearest_points(median_center, closest_node)[1]
    # Get the ID of the closest node
    closest_node_id = eligible_nodes.loc[eligible_nodes.geometry == closest_point, 'id'].values[0]
    return closest_point, closest_node_id

def cluster_homes_and_save(shapefile_path, nodes_path='nodes.shp', home_points_path='home_points.shp', fdh_path='fdh.shp', max_homes_per_cluster=432):
    homes = gpd.read_file(shapefile_path)
    nodes = gpd.read_file(nodes_path)
    coordinates = np.array(list(homes.geometry.apply(lambda x: (x.x, x.y))))
    Z = linkage(coordinates, method='ward')

    max_distance = Z[-1, 2]
    distance_threshold = max_distance / 2
    clusters = fcluster(Z, t=distance_threshold, criterion='distance')
    while np.max(np.bincount(clusters)) > max_homes_per_cluster and distance_threshold > 0:
        distance_threshold *= 0.95
        clusters = fcluster(Z, t=distance_threshold, criterion='distance')
    
    if distance_threshold <= 0:
        print("Unable to find a suitable distance threshold to meet the cluster size constraint.")
        return

    homes['fdh_id'] = clusters
    homes.to_file(home_points_path, driver='ESRI Shapefile')
    print(f"Clustered homes saved to {home_points_path}")

    median_centers = []
    for cluster_id in np.unique(homes['fdh_id']):
        cluster_points = np.array(list(homes.loc[homes['fdh_id'] == cluster_id, 'geometry'].apply(lambda p: (p.x, p.y))))
        median_x, median_y = find_median_center(cluster_points)
        if median_x is not None and median_y is not None:
            median_center = Point(median_x, median_y)
            snapped_center, node_id = snap_to_nearest_node(median_center, nodes)
            median_centers.append({
                'geometry': snapped_center,
                'id': cluster_id,
                'node_id': node_id
            })

    median_centers_gdf = gpd.GeoDataFrame(median_centers, columns=['geometry', 'id', 'node_id'], crs=homes.crs)
    median_centers_gdf.to_file(fdh_path, driver='ESRI Shapefile')
    print(f"Median centers saved to {fdh_path}")

# Adjust the call to cluster_homes_and_save as needed
cluster_homes_and_save('home_points.shp')
