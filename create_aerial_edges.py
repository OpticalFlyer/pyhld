#!/usr/bin/env python3

import geopandas as gpd
from shapely.geometry import LineString
import pandas as pd

# Constants
COST_PER_UNIT = 2.5  # Assuming the unit is in the same as your CRS

# Load the shapefiles
pole_lines_gdf = gpd.read_file('pole_lines.shp')
edges_gdf = gpd.read_file('edges.shp')

# Ensure CRS match if necessary
# pole_lines_gdf = pole_lines_gdf.to_crs(edges_gdf.crs)

# List to store new edges
new_edges = []

# Iterate over every feature of the pole_lines_gdf GeoDataFrame
for idx, pole_line in pole_lines_gdf.iterrows():
    # Get the geometry of the feature
    geom = pole_line.geometry
    
    # Assume each feature is a LineString (not MultiLineString)
    if isinstance(geom, LineString):
        vertices = list(geom.coords)
        
        for i in range(1, len(vertices)):
            # Get two consecutive vertices
            pt1 = vertices[i - 1]
            pt2 = vertices[i]
            
            # Create a LineString from the vertices
            line = LineString([pt1, pt2])
            
            # Calculate the length of the line
            length = line.length  # Length is in CRS units
            
            # Calculate the cost
            cost = length * COST_PER_UNIT
            
            # Create a new edge feature with attributes and geometry
            new_edge = {
                'type': 'Aerial',
                'length': length,
                'cost': cost,
                'geometry': line
            }
            
            # Append the new edge to the list
            new_edges.append(new_edge)

# Create a GeoDataFrame from the list of new edges
new_edges_gdf = gpd.GeoDataFrame(new_edges, crs=edges_gdf.crs)

# Concatenate new edges with the existing edges GeoDataFrame
edges_gdf = pd.concat([edges_gdf, new_edges_gdf], ignore_index=True)

# Save the updated edges GeoDataFrame back to the shapefile
edges_gdf.to_file('edges.shp')

print("Aerial pole lines have been added to the edges shapefile.")
