import pandas as pd
import numpy as np
import os
import sys
import yaml
import spectral as sp
import open3d as o3d

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

def ply_to_df(ply_filepath):
    # Read PLY file
    point_cloud = o3d.io.read_point_cloud(ply_filepath)

    # Convert to pandas DataFrame
    df = pd.DataFrame(point_cloud.points, columns=["x", "y", "z"])
    #df = pd.DataFrame(point_cloud.colors, columns=["red", "green", "blue"])
    # if point_cloud.has_normals():
    #     df = pd.DataFrame(point_cloud.normals, columns=["nx", "ny", "nz"])

    return df

# Function to read Hyspex image and flatten it
def read_hyspex(hdr_filepath):
    hdr = sp.envi.open(hdr_filepath)
    wvl = hdr.bands.centers
    #rows, cols, bands = hdr.nrows, hdr.ncols, hdr.nbands
    #meta = hdr.metadata

    spectral_data = hdr.load()

    spectral_data_flattened = spectral_data.reshape(-1, hdr.nbands) # Flatten the data
    #TODO: I would like to be more sure that I have row and column the correct way round
    df = pd.DataFrame(spectral_data_flattened, columns=wvl)
    return df