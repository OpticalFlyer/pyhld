#!/usr/bin/env python3

import geopandas as gpd

# Load the shapefiles
network_gdf = gpd.read_file('network.shp')
poles_gdf = gpd.read_file('poles.shp')

# Check for invalid geometries
invalid_geometries = poles_gdf[~poles_gdf.is_valid]
if not invalid_geometries.empty:
    print(f"Found {len(invalid_geometries)} invalid geometries. Removing them.")
    poles_gdf = poles_gdf[poles_gdf.is_valid]

# Buffer value in feet (adjust as needed for your data's accuracy)
buffer_distance = 1  # 1 foot buffer

# List to collect poles that are used
poles_used = []

# Check each pole for intersection with any line in the network
for _, pole in poles_gdf.iterrows():
    # Apply buffer to the pole point for intersection check
    buffered_pole = pole.geometry.buffer(buffer_distance)
    
    # Check if the buffered pole intersects with any line in the network
    if any(buffered_pole.intersects(line) for line in network_gdf.geometry):
        # Add pole to the list
        poles_used.append(pole)

# Create a GeoDataFrame from the list of used poles
poles_used_gdf = gpd.GeoDataFrame(poles_used, columns=poles_gdf.columns, crs=poles_gdf.crs)

# Save the resulting GeoDataFrame to a new shapefile
poles_used_gdf.to_file('poles_used.shp')

# Output the number of poles saved
num_poles_saved = len(poles_used_gdf)
print(f"{num_poles_saved} poles used have been saved to poles_used.shp.")

