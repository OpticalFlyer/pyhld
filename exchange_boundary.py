#!/usr/bin/env python3

import sys
import geopandas as gpd
import numpy as np
from shapely.geometry import MultiPoint, MultiPolygon, Polygon
from scipy.spatial import Delaunay

def alpha_shape(points, alpha):
    if len(points) < 4:
        return MultiPoint(list(points)).convex_hull

    def add_edge(edges, edge_points, coords, i, j):
        """Add a line between the i-th and j-th points, if not in the list already"""
        if (i, j) in edges or (j, i) in edges:
            # already added
            return
        edges.add((i, j))
        edge_points.append(coords[i])  # First point of the edge
        edge_points.append(coords[j])  # Second point of the edge

    coords = np.array([point.coords[0] for point in points])
    tri = Delaunay(coords)
    edges = set()
    edge_points = []
    for ia, ib, ic in tri.simplices:
        pa = coords[ia]
        pb = coords[ib]
        pc = coords[ic]
        a = np.linalg.norm(pa - pb)
        b = np.linalg.norm(pb - pc)
        c = np.linalg.norm(pc - pa)
        s = (a + b + c) / 2.0
        area = np.sqrt(s * (s - a) * (s - b) * (s - c))
        circum_r = a * b * c / (4.0 * area)
        if circum_r < 1.0 / alpha:
            add_edge(edges, edge_points, coords, ia, ib)
            add_edge(edges, edge_points, coords, ib, ic)
            add_edge(edges, edge_points, coords, ic, ia)

    # Make sure edge_points are tuples, as Shapely expects
    edge_points = [tuple(pt) for pt in edge_points]
    
    # Create a MultiPoint object from edge_points
    m = MultiPoint(edge_points).convex_hull
    if m.geom_type in ['Polygon', 'MultiPolygon']:
        return m
    elif m.geom_type == 'GeometryCollection':
        # Correct iteration over geometries in GeometryCollection
        polygons = [geom for geom in m.geoms if geom.geom_type in ['Polygon', 'MultiPolygon']]
        if polygons:
            return MultiPolygon(polygons)
        else:
            # Fallback to convex hull if no polygonal geometries are found
            print("Warning: No polygonal geometries found in the geometry collection. Falling back to convex hull.")
            return MultiPoint(list(points)).convex_hull
    else:
        raise ValueError(f"Unsupported geometry type: {m.geom_type}")

def create_concave_hull_shapefile(input_shapefile, output_shapefile, alpha=0.0000003):
    points_df = gpd.read_file(input_shapefile)
    concave_hull_polygon = alpha_shape(points_df.geometry, alpha)
    polygon_gdf = gpd.GeoDataFrame([1], geometry=[concave_hull_polygon], columns=['dummy'])
    polygon_gdf.crs = points_df.crs
    polygon_gdf.to_file(output_shapefile)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <path/to/your/point_shapefile.shp>")
        sys.exit(1)

    input_shapefile = sys.argv[1]
    output_shapefile = 'exchange_boundary.shp'
    create_concave_hull_shapefile(input_shapefile, output_shapefile)
