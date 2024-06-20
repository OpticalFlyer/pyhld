#!/usr/bin/env python3

import geopandas as gpd
import pandas as pd

# Load the network shapefile
network_gdf = gpd.read_file('network.shp')

# Load the home points shapefile
home_points_gdf = gpd.read_file('home_points.shp')

# Initialize a dictionary to hold the aggregated network data
report_data = {}

# Check if 'unit_count' exists in home_points_gdf
include_unit_count = 'unit_count' in home_points_gdf.columns
if include_unit_count:
    print("unit_count column found in home_points.shp.")
else:
    print("unit_count column not found in home_points.shp.")

# Count homes per fdh_id from home_points.shp
home_counts = home_points_gdf['fdh_id'].value_counts().to_dict()

# Aggregate Unit_count per fdh_id if available
unit_counts = home_points_gdf.groupby('fdh_id')['unit_count'].sum().to_dict() if include_unit_count else {}

for _, row in network_gdf.iterrows():
    fdh_id = row['fdh_id']
    type = row['type']
    length = row.geometry.length

    # Initialize the fdh_id entry if not already present
    if fdh_id not in report_data:
        report_data[fdh_id] = {'FDH ID': fdh_id, 'HP': 0, 'HHP': 0, 'Aerial Drop': 0, 'Buried Drop': 0, 'Aerial': 0, 'Underground': 0}
        # Add home count if available
        report_data[fdh_id]['HP'] = home_counts.get(fdh_id, 0)
        # Add unit count if available
        if include_unit_count:
            report_data[fdh_id]['HHP'] = unit_counts.get(fdh_id, 0)

    # Process network data
    if type in ['Aerial Drop', 'Buried Drop']:
        report_data[fdh_id][type] += 1  # Increment the count for drop types
    elif type in ['Aerial', 'Underground', 'Transition']:
        adjusted_type = 'Underground' if type == 'Transition' else type
        report_data[fdh_id][adjusted_type] += length  # Add length, including 'Transition' to 'Underground'

# Calculate additional columns and round lengths
for fdh_id, data in report_data.items():
    aerial = data['Aerial']
    underground = data['Underground']
    total_length = aerial + underground
    
    # Determine the divisor for FPP calculation based on the availability of HHP or HP
    if include_unit_count and data['HHP'] > 0:  # If HHP is available and greater than 0
        divisor = data['HHP']
    else:  # If HHP is not available or 0, use HP
        divisor = data['HP']

    data['Aerial'] = round(aerial)
    data['Underground'] = round(underground)
    data['% Aerial'] = round((aerial / total_length * 100) if total_length > 0 else 0, 2)  # Calculate % Aerial
    data['FPP'] = round((total_length / divisor) if divisor > 0 else 0, 2)  # Calculate Feet per Home Point

# Convert the data to a pandas DataFrame and sort by FDH ID
report_df = pd.DataFrame(list(report_data.values())).sort_values(by='FDH ID')

# Specify the column order, including the new 'HHP' column if applicable
columns_order = ['FDH ID', 'HP', 'HHP', 'Aerial Drop', 'Buried Drop', 'Aerial', 'Underground', '% Aerial', 'FPP'] if include_unit_count else ['FDH ID', 'HP', 'Aerial Drop', 'Buried Drop', 'Aerial', 'Underground', '% Aerial', 'FPP']
report_df = report_df[columns_order]

# Write the DataFrame to an Excel file
report_df.to_excel('network_report.xlsx', index=False, engine='openpyxl')

print("Sorted report with additional metrics has been saved to network_report.xlsx.")