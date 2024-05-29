import pandas as pd
from plyfile import PlyData
import numpy as np
import os
import sys
import yaml

# Load likely headers from YAML file
with open('config/possible_headers.yml', 'r') as file:
    likely_headers = yaml.safe_load(file)

# Not all of these are required
def ascii_to_df(filepath, header_row, data_start_row):

    gap = data_start_row-(header_row+1)
    if header_row == 0:
        df = pd.read_csv(filepath, header=None, skiprows=data_start_row-header_row)
    elif gap == 0:
        df = pd.read_csv(filepath, header=header_row-1)
    else:
        df = pd.read_csv(filepath, header=header_row, skiprows=data_start_row-(header_row+1))
    return df


def ply_to_df(filepath):
    ply_data = PlyData.read(filepath)

    # Extract the vertex element
    vertex_data = ply_data['vertex']

    # Prepare a dictionary to hold the vertex attributes
    attributes = {}
    for prop in vertex_data.properties:
        attributes[prop.name] = np.array(vertex_data[prop.name])

    # Create a pandas DataFrame
    df = pd.DataFrame(attributes)

    return df


def update_headers(df):
    '''
    Updating the column headers to a standard set of column headers that can be
    understood and processed by the rest of the program.
    '''
    # TODO: what should we do about unrecognized column headers?
    # Option 1: write them to the netcdf file unprocessed? What about the long name and units?
    # Option 2: ignore them and don't write them to the netcdf file. return a warning
    # Option 3: return an error and the netcdf file won't be written
    # Option 4: ask the user (prompt) what to do?
    for target_name, headers in likely_headers.items():
        for header in headers:
            if header.lower() in df.columns.str.lower():
                target_col = df.columns[df.columns.str.lower() == header.lower()][0]
                df.rename(columns={target_col: target_name}, inplace=True)
                break
    return df

def data_to_df(filepath):

    errors = []
    warnings = []

    file_name, file_extension = os.path.splitext(filepath)
    if file_extension.lower() in ['.csv', '.ascii', '.txt']:
        # Do something for CSV, ASCII, or TXT files
        print(f"Processing {file_extension} file: {filepath}")
        df = ascii_to_df(filepath)
    elif file_extension.lower() == '.ply':
        # Do something for PLY files
        print("Processing PLY file:", filepath)
        df = ply_to_df(filepath)
    else:
        # Handle other file extensions
        print(f"Unsupported file format: {filepath}")
        sys.exit()

    df = update_headers(df)

    return df, errors, warnings