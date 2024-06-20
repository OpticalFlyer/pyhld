#!/usr/bin/env python3

import sys
import geopandas as gpd

def reproject_shapefile(input_shapefile, output_shapefile, target_epsg):
    gdf = gpd.read_file(input_shapefile)
    gdf = gdf.to_crs(epsg=target_epsg)
    gdf.to_file(output_shapefile)

    print(f"Shapefile has been reprojected to EPSG:{target_epsg} and saved as {output_shapefile}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python reproject.py <input_shapefile> <output_shapefile> <target_epsg_code>")
        sys.exit(1)
    
    input_shapefile = sys.argv[1]
    output_shapefile = sys.argv[2]
    target_epsg = sys.argv[3]  # EPSG code as a string is fine here, GeoPandas handles the conversion

    reproject_shapefile(input_shapefile, output_shapefile, target_epsg)
