#!/usr/bin/env python3

import geopandas as gpd
from shapely.geometry import LineString, Point
from shapely.affinity import translate
from shapely.ops import split, unary_union, nearest_points
from geopy.distance import great_circle
import math
import pandas as pd

# Define constants
underground_cpf = 1000.00
buried_drop_cpf = 200.00

# Function definitions
def extend_line(line, extension_length):
    """Extend a line by a given length."""
    if isinstance(line, LineString) and len(line.coords) >= 2:
        start_point = line.coords[0]
        end_point = line.coords[-1]
        dx = end_point[0] - start_point[0]
        dy = end_point[1] - start_point[1]
        length = math.sqrt(dx**2 + dy**2)
        extension_dx = dx / length * extension_length
        extension_dy = dy / length * extension_length
        extended_line = LineString([start_point, translate(Point(end_point), extension_dx, extension_dy).coords[0]])
        return extended_line
    return line

def closest_point_on_line(point, lines):
    """Find the closest point on the closest line to the given point."""
    nearest_line = min(lines, key=lambda line: line.distance(point))
    return nearest_points(point, nearest_line)[1]

# Load data from shapefiles
gdf_homes = gpd.read_file('home_points.shp')
gdf_centerlines = gpd.read_file('road_centerlines.shp')

# Ensure CRS match
gdf_homes = gdf_homes.to_crs(gdf_centerlines.crs)

print("Processing drops...")

# Process each home point
drops = []
drops_ext = []
for idx, home in gdf_homes.iterrows():
    nearest_point = closest_point_on_line(home.geometry, gdf_centerlines.geometry)
    line = LineString([home.geometry, nearest_point])
    drops.append({'geometry': line})
    line_ext = extend_line(line, line.length * 0.05)
    drops_ext.append({'geometry': line_ext})

# Convert drops to GeoDataFrames and save to shapefiles
gdf_drops = gpd.GeoDataFrame(drops, crs=gdf_centerlines.crs)
#gdf_drops.to_file('drops.shp')

gdf_drops_ext = gpd.GeoDataFrame(drops_ext, crs=gdf_centerlines.crs)
#gdf_drops_ext.to_file('drops_ext.shp')

print("Splitting centerlines...")

# Split the centerlines with extended drops
split_lines = []
for line in gdf_centerlines.geometry:
    split_line = split(line, unary_union(gdf_drops_ext.geometry))
    for geom in split_line.geoms:  # Iterate through the geometries in the GeometryCollection
        split_lines.append(geom)

gdf_split_roads = gpd.GeoDataFrame(geometry=split_lines, crs=gdf_centerlines.crs)
gdf_split_roads = gdf_split_roads.drop_duplicates(subset=['geometry'])

# Calculate additional attributes (length, cost, type)
gdf_split_roads['type'] = 'Underground'
gdf_split_roads['length'] = gdf_split_roads.geometry.length  # Length in CRS units
gdf_split_roads['cost'] = gdf_split_roads['length'] * underground_cpf

# Save outputs to shapefiles
#gdf_edges.to_file('split_roads.shp')

# Prepare drops for concatenation with edges
gdf_drops['type'] = 'Buried Drop'
gdf_drops['length'] = gdf_drops.geometry.length  # Length in CRS units
gdf_drops['cost'] = gdf_drops['length'] * buried_drop_cpf

# Combine drops with edges
gdf_combined = pd.concat([gdf_split_roads, gdf_drops], ignore_index=True)

# Save the combined GeoDataFrame to a shapefile
gdf_combined.to_file('edges.shp')

print("Processing complete.")
