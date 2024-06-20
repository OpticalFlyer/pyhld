#!/usr/bin/env python3

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString
import numpy as np
from scipy.spatial import cKDTree

# Constants
SEARCH_RADIUS = 200  # Search radius in feet
COST_PER_FOOT = 1.5  # Cost per foot

# Load the shapefiles
home_points_gdf = gpd.read_file('home_points.shp')
poles_gdf = gpd.read_file('poles.shp')
edges_gdf = gpd.read_file('edges.shp')

# Convert search radius to the CRS units of the poles layer (assuming it's in feet if in a projected CRS)
# If the CRS is in meters, use a conversion factor from feet to meters
conversion_factor = 1 # if poles_gdf.crs.axis_info[0].unit_name == 'foot' else 0.3048
search_radius_in_crs_units = SEARCH_RADIUS * conversion_factor

# Check for invalid geometries
invalid_geometries = poles_gdf[~poles_gdf.is_valid]
if not invalid_geometries.empty:
    print(f"Found {len(invalid_geometries)} invalid geometries. Removing them.")
    poles_gdf = poles_gdf[poles_gdf.is_valid]

# Ensure all coordinates are finite
finite_coords_check = np.isfinite(poles_gdf.geometry.x) & np.isfinite(poles_gdf.geometry.y)
if not finite_coords_check.all():
    print("Found non-finite coordinates. Removing corresponding entries.")
    poles_gdf = poles_gdf[finite_coords_check]

# Create KDTree for poles for efficient nearest neighbor search
poles_coords = np.array(list(zip(poles_gdf.geometry.x, poles_gdf.geometry.y)))
tree = cKDTree(poles_coords)

# List to store new drop edges
new_edges = []

# Iterate over every home point
for idx, home in home_points_gdf.iterrows():
    # Query the nearest pole within the search radius
    distance, index = tree.query(home.geometry.coords[0], k=1, distance_upper_bound=search_radius_in_crs_units)
    if distance != np.inf:
        # If a pole is found within the search radius, create the new edge
        nearest_pole = poles_gdf.iloc[index].geometry
        #line = LineString([home.geometry, nearest_pole])
        home_coords = (home.geometry.x, home.geometry.y)
        nearest_pole_coords = (nearest_pole.x, nearest_pole.y)
        line = LineString([home_coords, nearest_pole_coords])
        
        # Calculate cost
        length = line.length  # Length in CRS units
        cost = length * conversion_factor * COST_PER_FOOT  # Convert length to feet and calculate cost
        
        # Create a new edge feature with the specified attributes
        new_edge = {
            'type': 'Aerial Drop',
            'length': length,
            'cost': cost,
            'geometry': line
        }
        new_edges.append(new_edge)

# Append new edges to the existing edges GeoDataFrame
new_edges_gdf = gpd.GeoDataFrame(new_edges, columns=['type', 'length', 'cost', 'geometry'], crs=edges_gdf.crs)

# Concatenate new edges with the existing edges GeoDataFrame
edges_gdf = pd.concat([edges_gdf, new_edges_gdf], ignore_index=True)

# Save the updated edges GeoDataFrame back to the shapefile
edges_gdf.to_file('edges.shp')

print("Aerial drops have been added to the edges shapefile.")