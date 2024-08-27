import pandas as pd
import numpy as np
import os
import sys
import yaml
import spectral as sp
import open3d as o3d
from plyfile import PlyData
from pyproj import Proj, Transformer, CRS

# Load likely headers from YAML file
with open('config/possible_headers.yml', 'r') as file:
    likely_headers = yaml.safe_load(file)

def get_ply_comment(plyfile):
    """
    Get the ply file comment string
    """
    with open(plyfile, 'rb') as fd:
        for line in fd:
            # Decode the line to a string
            decoded_line = line.decode('utf-8').strip()

            # Check if the line starts with 'comment'
            if decoded_line.startswith("comment"):
                return decoded_line

            # Check if the line indicates the end of the header
            elif decoded_line.startswith("end_header"):
                return None

        raise IOError("Didn't find end of header. This can't be a valid PLY file.")


def get_cf_grid_mapping(ply_filepath):
    """
    Get cf_grid_mapping
    """
    # TODO: Add control if doesn't work.
    # For example if config file or comment are erroneous

    comment_str = get_ply_comment(ply_filepath)

    # get projection string from the comment
    ind_crs = comment_str.find("utm_crs")
    if ind_crs == -1:
        raise IOError("Projection is not specified in the ply file comment")

    proj4str = comment_str[ind_crs:].split(";")[0].split("utm_crs")[1]
    proj4str = proj4str[proj4str.find("=")+1:]
    crs = CRS.from_proj4(proj4str)
    cf_grid_mapping = crs.to_cf()
    return cf_grid_mapping


def utm_to_latlon(x, y, cf_grid_mapping):

    crs = CRS.from_cf(cf_grid_mapping)

    # Create a Transformer object for UTM to WGS84 conversion
    transformer = Transformer.from_crs(crs, CRS.from_epsg(4326), always_xy=True)

    # Convert UTM (x, y) arrays to lat/lon arrays
    lon, lat = transformer.transform(x, y)
    return lat, lon

def ply_to_df(ply_filepath, cf_grid_mapping):
    # TODO: Need to be able to read latitude, longitude and altitude if they are present
    # Issue: plyfile library can't read the file provided because of early end-of-file warnings (corrupted?)
    # Issue: open3d is not able to read latitude and longitude directly as it does points, colors and normals
    # Read PLY file
    point_cloud = o3d.io.read_point_cloud(ply_filepath)

    # Convert to pandas DataFrame
    points_df = pd.DataFrame(point_cloud.points, columns=["x", "y", "z"])

    # Initialize an empty list to hold the DataFrames
    dataframes = [points_df]

    # Check if colors and normals exist and append them to the list
    if point_cloud.has_colors():
        colors_df = pd.DataFrame(point_cloud.colors, columns=["red", "green", "blue"])
        dataframes.append(colors_df)
    if point_cloud.has_normals():
        normals_df = pd.DataFrame(point_cloud.normals, columns=["nx", "ny", "nz"])
        dataframes.append(normals_df)

    # Use plyfile to manually extract velocities (vx, vy, vz)
    try:
        ply_data = PlyData.read(ply_filepath)
        vertex_data = ply_data['vertex'].data

        # Check if vx, vy, vz exist and extract them
        if all(field in vertex_data.dtype.names for field in ['vx', 'vy', 'vz']):
            vx = vertex_data['vx']
            vy = vertex_data['vy']
            vz = vertex_data['vz']
            velocities_df = pd.DataFrame(np.column_stack((vx, vy, vz)), columns=["vx", "vy", "vz"])
            dataframes.append(velocities_df)

    except Exception as e:
        print(f"Failed to extract velocities: {e}")

    # Concatenate all DataFrames horizontally
    combined_df = pd.concat(dataframes, axis=1)

    # Calculate latitude and longitude using bulk transformation
    lat, lon = utm_to_latlon(combined_df['x'].values, combined_df['y'].values, cf_grid_mapping)
    combined_df['latitude'], combined_df['longitude'] = lat, lon

    return combined_df

# Function to read Hyspex image and flatten it
def read_hyspex(hdr_filepath):
    hdr = sp.envi.open(hdr_filepath)
    wavelengths = hdr.bands.centers

    spectral_data = hdr.load()

    spectral_data_flattened = spectral_data.reshape(-1, hdr.nbands) # Flatten the data
    #TODO: I would like to be more sure that I have row and column the correct way round
    df = pd.DataFrame(spectral_data_flattened, columns=wavelengths)
    return df