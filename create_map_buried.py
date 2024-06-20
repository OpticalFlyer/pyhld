#!/usr/bin/env python3

import folium
import geopandas as gpd
from shapely.geometry import box
import matplotlib.pyplot as plt
import matplotlib.colors
import numpy as np

# Load the shapefiles
network_gdf = gpd.read_file('network.shp')
home_points_gdf = gpd.read_file('home_points.shp')
#poles_used_gdf = gpd.read_file('poles_used.shp')
mst_gdf = gpd.read_file('mst.shp')
#headend_gdf = gpd.read_file('headend.shp')
fdh_gdf = gpd.read_file('fdh.shp').to_crs(epsg=4326)

# Reproject to EPSG:4326 for Folium compatibility
network_gdf = network_gdf.to_crs(epsg=4326)
home_points_gdf = home_points_gdf.to_crs(epsg=4326)
#poles_used_gdf = poles_used_gdf.to_crs(epsg=4326)
mst_gdf = mst_gdf.to_crs(epsg=4326)
#headend_gdf = headend_gdf.to_crs(epsg=4326)

# Calculate the center based on the bounding box of network geometries
center = [network_gdf.total_bounds[1] + (network_gdf.total_bounds[3] - network_gdf.total_bounds[1]) / 2,
          network_gdf.total_bounds[0] + (network_gdf.total_bounds[2] - network_gdf.total_bounds[0]) / 2]

# Initialize a Folium map centered on the calculated center
m = folium.Map(location=center, zoom_start=14)

# Function to add lines to the map with specific styles
def add_lines(gdf, line_color, line_weight, line_dash_array=None):
    for _, row in gdf.iterrows():
        points = [[point[1], point[0]] for point in row.geometry.coords]
        folium.PolyLine(points, color=line_color, weight=line_weight, dash_array=line_dash_array).add_to(m)

# Add lines from network.shp with different styles based on type
add_lines(network_gdf[network_gdf['type'] == 'Underground'], 'green', 3)
add_lines(network_gdf[network_gdf['type'] == 'Aerial'], 'blue', 3)
add_lines(network_gdf[network_gdf['type'] == 'Aerial Drop'], 'cyan', 1)
add_lines(network_gdf[network_gdf['type'] == 'Buried Drop'], 'orange', 1)
add_lines(network_gdf[network_gdf['type'] == 'Transition'], 'green', 3, '5,5')

# Function to add filled circles to the map
def add_filled_circles(gdf, color, fill_color, radius):
    for _, row in gdf.iterrows():
        folium.Circle(
            location=[row.geometry.y, row.geometry.x], 
            radius=radius,
            color=color,
            fill=True,
            fill_color=fill_color,
            fill_opacity=1.0  # Ensure the fill is fully opaque
        ).add_to(m)

def add_fdh_markers(gdf, icon_color, icon_icon):
    for _, row in gdf.iterrows():
        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            icon=folium.Icon(color=icon_color, icon=icon_icon),
            popup=f"FDH Cabinet {row['id']}"  # Optional: Add a popup label to each FDH marker
        ).add_to(m)

# Add home points as orange filled circles
#add_filled_circles(home_points_gdf, 'orange', 'orange', 5)
        
def add_home_points_by_fdh(gdf, radius):
    # Generate a color palette with enough colors for each fdh_id
    unique_fdh_ids = gdf['fdh_id'].unique()
    # Update: Use recommended method for accessing colormaps in newer versions of Matplotlib
    color_palette = plt.colormaps['hsv'](np.linspace(0, 1, len(unique_fdh_ids)))
    
    # Create a dictionary to map each fdh_id to a color
    fdh_id_to_color = {fdh_id: color_palette[i] for i, fdh_id in enumerate(unique_fdh_ids)}
    
    # Add home points with colors based on their fdh_id
    for _, row in gdf.iterrows():
        fdh_id = row['fdh_id']
        color = matplotlib.colors.to_hex(fdh_id_to_color[fdh_id])  # Convert color to hex format for Folium
        folium.Circle(
            location=[row.geometry.y, row.geometry.x],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=1.0
        ).add_to(m)

# Replace the original call to add home points with the new function
add_home_points_by_fdh(home_points_gdf, 5)

# Add used poles as white filled circles, make them smaller
#add_filled_circles(poles_used_gdf, 'black', 'white', 3)

add_filled_circles(mst_gdf, 'black', 'red', 4)
'''
for _, row in headend_gdf.iterrows():
        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            icon=folium.Icon(color='darkblue', icon='cloud'),
            popup="Headend"
        ).add_to(m)
'''
add_fdh_markers(fdh_gdf, 'darkpurple', 'glyphicon-tower')

# Save the map to an HTML file
m.save('network_map.html')

print("Map has been saved to network_map.html.")
