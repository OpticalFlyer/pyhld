#!/usr/bin/env python3

import osmnx as ox
import geopandas as gpd
from shapely.geometry import LineString, box

print("Getting road centerlines...")

# Load home points from a shapefile
home_points_gdf = gpd.read_file('home_points.shp')

# Check if there's at least one feature in the DataFrame
if not home_points_gdf.empty:
    # Check if CRS is projected, if not, prompt to check the CRS
    if home_points_gdf.crs.is_geographic:
        print("Warning: The CRS of the shapefile is geographic. Buffering might be inaccurate.")
    else:
        print(f"Using projected CRS {home_points_gdf.crs} for buffering.")

    # Determine the units of the CRS
    crs_units = home_points_gdf.crs.axis_info[0].unit_name
    print(f"CRS units: {crs_units}")

    # Calculate the total bounds of the home points and extend by 1000 feet on each side
    extension_distance_feet = 1000  # Distance in feet
    extension_distance = extension_distance_feet  # Default in feet

    # Convert the extension distance from feet to the CRS units if necessary
    if crs_units == 'meter':
        extension_distance = extension_distance_feet * 0.3048  # Convert feet to meters

    minx, miny, maxx, maxy = home_points_gdf.total_bounds
    extended_bounds = (minx - extension_distance, miny - extension_distance,
                       maxx + extension_distance, maxy + extension_distance)

    # Create an extended bounding box around the home points
    bbox = box(*extended_bounds)
    
    # Reproject the bounding box to EPSG:4326 for OSMnx
    bbox_reprojected = gpd.GeoSeries([bbox], crs=home_points_gdf.crs).to_crs('epsg:4326')

    # Use OSMnx to download the street network
    G = ox.graph_from_polygon(bbox_reprojected.iloc[0], network_type='drive')

    # Convert the graph into GeoDataFrames
    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)

    # Check each row in each column and convert non-compatible types to strings, skip geometry column
    for column in gdf_edges.columns:
        if column != 'geometry':  # Skip the geometry column
            for idx, value in gdf_edges[column].items():
                if isinstance(value, (list, dict, set)):
                    gdf_edges.at[idx, column] = ', '.join(map(str, value))
                elif not isinstance(value, (int, float, str, type(None))):
                    gdf_edges.at[idx, column] = str(value)
            print(f"Processed column: {column}")

    # Reproject gdf_edges back to the original CRS of home points
    original_crs = home_points_gdf.crs
    gdf_edges = gdf_edges.to_crs(original_crs)

    print("Normalizing geometries...")

    # Normalize geometries and deduplicate
    def normalize_geometry(geometry):
        if isinstance(geometry, LineString):
            return LineString(sorted(geometry.coords))
        return geometry

    gdf_edges['normalized_geom'] = gdf_edges['geometry'].apply(normalize_geometry)
    gdf_edges_deduped = gdf_edges.drop_duplicates(subset=['osmid', 'normalized_geom'])

    # Drop the temporary 'normalized_geom' column
    gdf_edges_deduped = gdf_edges_deduped.drop(columns=['normalized_geom'])

    # Reproject gdf_edges_deduped back to the original CRS of home points
    original_crs = home_points_gdf.crs
    gdf_edges_deduped = gdf_edges_deduped.to_crs(original_crs)

    # Attempt to save the deduplicated DataFrame to a shapefile
    try:
        gdf_edges_deduped.to_file('road_centerlines.shp')
        print(f"Road centerlines have been saved to road_centerlines.shp in CRS {original_crs}.")
    except Exception as e:
        print(f"Error encountered: {e}")

else:
    print("No points found in the home_points.shp file.")

print("Done.")
