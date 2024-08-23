import pandas as pd
import numpy as np
import os
import sys
import yaml
import spectral as sp
import open3d as o3d
from plyfile import PlyData
from pyproj import Proj, Transformer

# Load likely headers from YAML file
with open('config/possible_headers.yml', 'r') as file:
    likely_headers = yaml.safe_load(file)

# # Not all of these are required
# def ascii_to_df(filepath, header_row, data_start_row):

#     gap = data_start_row-(header_row+1)
#     if header_row == 0:
#         df = pd.read_csv(filepath, header=None, skiprows=data_start_row-header_row)
#     elif gap == 0:
#         df = pd.read_csv(filepath, header=header_row-1)
#     else:
#         df = pd.read_csv(filepath, header=header_row, skiprows=data_start_row-(header_row+1))
#     return df

# def update_headers(df):
#     '''
#     Updating the column headers to a standard set of column headers that can be
#     understood and processed by the rest of the program.
#     '''
#     # TODO: what should we do about unrecognized column headers?
#     # Option 1: write them to the netcdf file unprocessed? What about the long name and units?
#     # Option 2: ignore them and don't write them to the netcdf file. return a warning
#     # Option 3: return an error and the netcdf file won't be written
#     # Option 4: ask the user (prompt) what to do?
#     for target_name, headers in likely_headers.items():
#         for header in headers:
#             if header.lower() in df.columns.str.lower():
#                 target_col = df.columns[df.columns.str.lower() == header.lower()][0]
#                 df.rename(columns={target_col: target_name}, inplace=True)
#                 break
#     return df

# def data_to_df(filepath):

#     errors = []
#     warnings = []

#     file_name, file_extension = os.path.splitext(filepath)
#     if file_extension.lower() in ['.csv', '.ascii', '.txt']:
#         # Do something for CSV, ASCII, or TXT files
#         print(f"Processing {file_extension} file: {filepath}")
#         df = ascii_to_df(filepath)
#     elif file_extension.lower() == '.ply':
#         # Do something for PLY files
#         print("Processing PLY file:", filepath)
#         df = ply_to_df(filepath)
#     else:
#         # Handle other file extensions
#         print(f"Unsupported file format: {filepath}")
#         sys.exit()

#     df = update_headers(df)

#     return df, errors, warnings

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

def get_projection(ply_filepath=None):
    """
    Get map projection
    """
    #TODO: Alternatively get from grid mapping file
    comment_str = get_ply_comment(ply_filepath)

    # get projection string from the comment
    ind_crs = comment_str.find("utm_crs")
    if ind_crs == -1:
        raise IOError("Projection is not specified in the ply file comment")

    proj4str = comment_str[ind_crs:].split(";")[0].split("utm_crs")[1]
    proj4str = proj4str[proj4str.find("=")+1:]

    return proj4str

def utm_to_latlon(x, y, proj4str, crs="EPSG:4326"):

    # Create a Transformer object for UTM to WGS84 conversion
    transformer = Transformer.from_crs(proj4str, crs, always_xy=True)

    # Convert UTM (x, y) arrays to lat/lon arrays
    lon, lat = transformer.transform(x, y)
    return lat, lon

def ply_to_df(ply_filepath, proj4str):
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
    lat, lon = utm_to_latlon(combined_df['x'].values, combined_df['y'].values, proj4str)
    combined_df['latitude'], combined_df['longitude'] = lat, lon

    return combined_df

# Function to read Hyspex image and flatten it
def read_hyspex(hdr_filepath):
    hdr = sp.envi.open(hdr_filepath)
    wavelengths = hdr.bands.centers
    #rows, cols, bands = hdr.nrows, hdr.ncols, hdr.nbands
    #meta = hdr.metadata

    spectral_data = hdr.load()

    spectral_data_flattened = spectral_data.reshape(-1, hdr.nbands) # Flatten the data
    #TODO: I would like to be more sure that I have row and column the correct way round
    df = pd.DataFrame(spectral_data_flattened, columns=wavelengths)
    return df