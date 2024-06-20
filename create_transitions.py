#!/usr/bin/env python3

import geopandas as gpd
from shapely.geometry import LineString, Point, GeometryCollection
from shapely.ops import nearest_points, split
import pandas as pd

# Constants
SEARCH_RADIUS = 50  # feet, assuming your spatial data is in a feet-based coordinate system
COST_PER_FOOT = 1000  # cost per foot

# Load the shapefiles
poles_gdf = gpd.read_file('poles.shp')
edges_gdf = gpd.read_file('edges.shp')

# Separating 'Underground' edges from other edge types
underground_gdf = edges_gdf[edges_gdf['type'] == 'Underground']
other_edges_gdf = edges_gdf[edges_gdf['type'] != 'Underground']

# Creating spatial index for underground_gdf
underground_gdf_sindex = underground_gdf.sindex

# Set to keep track of indices of split edges
split_edges_indices = set()

# Function to split a line at a given point and return the segments
def split_line_at_point(line, point):
    """Split a line at a given point and return the segments."""
    # Create a temporary tiny line at the point to use for splitting
    buffer = Point(point).buffer(0.0001)  # Adjust buffer size if needed for precision
    split_line = split(line, buffer)

    # Check if the result is a GeometryCollection
    if isinstance(split_line, GeometryCollection):
        # Iterate through the geometries in the GeometryCollection
        return [geom for geom in split_line.geoms if isinstance(geom, LineString)]
    else:
        return [split_line]
    
def find_closest_edge(pole, underground_gdf, underground_gdf_sindex):
    # Using spatial index to find nearby edges
    possible_matches_index = list(underground_gdf_sindex.intersection(pole.geometry.buffer(SEARCH_RADIUS).bounds))
    possible_matches = underground_gdf.iloc[possible_matches_index]

    closest_edge = None
    closest_point = None
    min_dist = float('inf')

    # Iterate through potential nearby edges
    for edge_idx, edge in possible_matches.iterrows():
        # Find the closest point on the current edge to the pole
        point_on_edge = nearest_points(pole.geometry, edge.geometry)[1]
        dist = pole.geometry.distance(point_on_edge)

        # Update the closest edge if this one is closer
        if dist < min_dist:
            min_dist = dist
            closest_edge = edge
            closest_point = point_on_edge

    return closest_edge, closest_point, min_dist

# List to store new edges and transitions
new_edges = []
new_transitions = []

# Before the loop, filter out poles without valid geometries
valid_poles_gdf = poles_gdf[poles_gdf.geometry.notnull()]

# Progress indicator setup
total = len(valid_poles_gdf)
counter = 0

# Iterate over every pole
for idx, pole in valid_poles_gdf.iterrows():
    counter += 1
    print(f'Processing pole {counter}/{total}', end='\r')

    # Update the spatial index for the current state of underground_gdf
    underground_gdf_sindex = underground_gdf.sindex

    # Find the closest edge to the current pole
    closest_edge, closest_point, min_dist = find_closest_edge(pole, underground_gdf, underground_gdf_sindex)

    # Check if the closest edge is within the search radius
    if closest_edge is not None and min_dist <= SEARCH_RADIUS:
        # Create a transition edge to the closest point
        #transition_line = LineString([pole.geometry, closest_point])
        # Extract coordinates from Point objects before creating the LineString
        transition_line = LineString([(pole.geometry.x, pole.geometry.y), (closest_point.x, closest_point.y)])
        transition_length = transition_line.length
        transition_cost = transition_length * COST_PER_FOOT
        transition = {
            'type': 'Transition',
            'length': transition_length,
            'cost': transition_cost,
            'geometry': transition_line
        }
        new_transitions.append(transition)

        # Split the closest underground edge
        if closest_point.coords[:] not in closest_edge.geometry.coords[:]:
            split_segments = split_line_at_point(closest_edge.geometry, closest_point.coords[:])
            
            # Remove the split edge from underground_gdf
            underground_gdf = underground_gdf.drop(closest_edge.name)

            # Add new split segments to underground_gdf
            for segment in split_segments:
                new_edge = {
                    'type': 'Underground',
                    'length': segment.length,
                    'cost': segment.length * COST_PER_FOOT,
                    'geometry': segment
                }
                # Create a GeoDataFrame for the new edge and append it
                new_edge_gdf = gpd.GeoDataFrame([new_edge], crs=poles_gdf.crs)
                underground_gdf = pd.concat([underground_gdf, new_edge_gdf], ignore_index=True)

            # Update spatial index after modification
            underground_gdf_sindex = underground_gdf.sindex

# Filter out the split 'Underground' edges
unsplit_underground_gdf = underground_gdf[~underground_gdf.index.isin(split_edges_indices)]

# Create GeoDataFrames for the new edges and transitions
transitions_gdf = gpd.GeoDataFrame(new_transitions, crs=poles_gdf.crs)

# Concatenate the unsplit underground edges, the new (updated) underground edges, transitions, and other edge types
combined_edges_gdf = pd.concat([other_edges_gdf, underground_gdf, transitions_gdf], ignore_index=True)

# Save the updated edges GeoDataFrame back to the shapefile
combined_edges_gdf.to_file('edges.shp')

print("\nProcessing complete.")