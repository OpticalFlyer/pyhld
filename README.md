# pyhld

Fiber to the home high level autodesign in Python using shapefiles for input/output.

## USAGE

Clone the repo

git clone https://gitea.bomar.cloud/OpticalFlyer/pyhld.git

Make all scripts executable if not already, i.e.

cd ~/scripts
chmod +x *.py

Add scripts folder to path:

nano ~/.zshrc

Add the following to end of file, save and close:

export PATH="/Users/youruser/path/to/scripts:$PATH"

Apply the changes:

source ~/.zshrc

Create a folder for your HLD project
Save sites to a shape file called home_points.shp.  Use a projected CRS.

Run centerlines_from_homes.py from your project directory containing home_points.shp

Run drops_split_centerlines.py - need progress

If the design will have aerial path and you have pole data, drop the pole shape file into your project folder and name it poles.shp

Run connect_poles.py if you need to generate aerial spans.  This connects all poles together using a minimum spanning tree.

Run create_aerial_drops.py

Run create_aerial_edges.py

Run create_transitions.py

Run create_nodes.py - need progress

Run associate_drop_points_v2.py

Run cluster_fdh_v2.py

Run create_network_v2.py

***Make Manual Revisions Here***

Run create_mst_clusters.py - need progress (v2 not ready)

Run poles_used.py - add progress indicator

Run report.py

Run create_map.py