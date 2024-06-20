#!/usr/bin/env python3

import os
import subprocess

def open_with_google_earth(directory):
    # Check if the directory exists
    if not os.path.isdir(directory):
        print(f"Directory {directory} does not exist.")
        return

    # Walk through all files and folders within the directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.kml') or file.endswith('.kmz'):
                # Construct the full file path
                file_path = os.path.join(root, file)
                print(f"Opening {file_path} with Google Earth...")
                try:
                    # Attempt to open the file with the default application
                    subprocess.run(['open', file_path], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Failed to open {file_path}: {e}")

# Use the current directory as the starting point
directory_path = os.getcwd()
open_with_google_earth(directory_path)
