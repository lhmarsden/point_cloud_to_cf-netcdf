import pandas as pd
import numpy as np
import spectral as sp
import open3d as o3d
from plyfile import PlyData
from pyproj import Transformer, CRS
import laspy
import gc
import dask.dataframe as dd
import dask.array as da

# TODO: Use variable mapping file to give column headers in df
# TODO: the column headers will be the variable names in the file
# TODO: add logging for each variable mapped and each variable not mapped

def combine_dataframes(dfs):
    '''
    Combining a list of dataframes with the same columns into one df
    '''
    combined_df = pd.DataFrame()  # Start with an empty DataFrame

    for chunk in dfs:
        combined_df = pd.concat([combined_df, chunk], ignore_index=True)
        # Clear the previous chunk from memory
        del chunk
        # Force garbage collection
        gc.collect()
        # TODO: What if the LAS file includes latitude and longitude?

    return combined_df

def get_ply_comment(plyfile):
    """
    Get the ply file comment string
    """
    #! This will not be neccessary if projection in metadata file
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


def get_cf_crs(ply_filepath=None):
    """
    Get a dictionary of variable attributes to write to the CRS variable
    From a PROJ.4 string in the comment in the PLY file header
    """
    if ply_filepath:
        comment_str = get_ply_comment(ply_filepath)
        # get projection string from the comment
        ind_crs = comment_str.find("utm_crs")
        if ind_crs == -1:
            return None

        proj4str = comment_str[ind_crs:].split(";")[0].split("utm_crs")[1]
        proj4str = proj4str[proj4str.find("=")+1:]
        crs = CRS.from_proj4(proj4str)
    else:
        # TODO: generalise this (or code below) to get from some argument or config file
        crs = CRS.from_proj4('+proj=utm +zone=33 +datum=WGS84 +units=m +no_defs')

    print(crs)
    cf_crs = crs.to_cf()
    return cf_crs


def utm_to_latlon(x, y, cf_crs):

    crs = CRS.from_cf(cf_crs)

    # Create a Transformer object for UTM to WGS84 conversion
    transformer = Transformer.from_crs(crs, CRS.from_epsg(4326), always_xy=True)

    # Convert UTM (x, y) arrays to lat/lon arrays
    lon, lat = transformer.transform(x, y)
    return lat, lon

def process_chunk(start, end, data_dict):
    chunk = {key: value[start:end] for key, value in data_dict.items()}
    return pd.DataFrame(chunk)

def las_to_df(las_filepath, cf_crs, variable_mapping, xcoord=None, ycoord=None, zcoord=None):
    # Open the LAS file
    las = laspy.read(las_filepath)
    print('File read in')

    data_dict = {}

    # Get x, y, z coordinates and convert them to NumPy arrays. Scalar and offset applied.
    data_dict['x'] = np.array(las.x)
    data_dict['y'] = np.array(las.y)
    data_dict['z'] = np.array(las.z)

    print('x,y,z added to dict')

    # List of variables to extract
    variable_list = ['blue', 'red', 'green', 'scan_angle_rank', 'gps_time', 'intensity']

    # Iterate over variable_list and check if the variable exists in las.point_format.dimensions
    for var in variable_list:
        if var in [dim.name for dim in las.point_format.dimensions]:
            print('adding ',var,' to dict')
            data_dict[var] = np.array(las[var])  # Ensure conversion to NumPy array

    # Convert the dictionary to a pandas DataFrame
    # Process in smaller chunks, for example, chunks of 10000 rows
    chunk_size = 10000000
    num_rows = len(data_dict['x'])

    # Process each chunk
    dfs = []
    print('Processing chunks to df')
    for i in range(0, num_rows, chunk_size):
        df_chunk = process_chunk(i, i + chunk_size, data_dict)
        # If X, Y and Z are equal to lat, lon, altitude
        if xcoord:
            df_chunk.rename(columns={'x': xcoord}, inplace=True)
        if ycoord:
            df_chunk.rename(columns={'y': ycoord}, inplace=True)
        if zcoord:
            df_chunk.rename(columns={'z': zcoord}, inplace=True)
        dfs.append(df_chunk)

    print('Calculating lat/lon')
    if not all(col in dfs[0].columns for col in ['latitude', 'longitude']):
        cf_crs = get_cf_crs()
        processed_dfs = []
        for df in dfs:
            # Calculate latitude and longitude from X and Y and the CRS
            lat, lon = utm_to_latlon(df['x'].values, df['y'].values, cf_crs)
            df['latitude'], df['longitude'] = lat, lon
            processed_dfs.append(df)
        dfs = processed_dfs
    else:
        pass

    print('combining dataframes')
    combined_df = combine_dataframes(dfs)

    return combined_df

def list_variables_in_ply(ply_filepath):
    # Read the PLY file
    with open(ply_filepath, 'rb') as file:
        ply_data = PlyData.read(file)

    # Extract the column names dynamically from the PLY header
    column_names = [prop.name for prop in ply_data['vertex'].properties]

    return column_names

def ply_to_df(ply_filepath, cf_crs, variable_mapping, xcoord=None, ycoord=None, zcoord=None):
    # Read the PLY file
    with open(ply_filepath, 'rb') as file:
        ply_data = PlyData.read(file)

    # Extract the column names dynamically from the PLY header
    column_names = [prop.name for prop in ply_data['vertex'].properties]

    # Dictionary to map columns based on possible names
    column_mapping = {}
    unused_columns = []

    # Extract vertex data into a DataFrame using the dynamic column names
    df = pd.DataFrame(ply_data['vertex'].data, columns=column_names)

    for col in df.columns:
        matched = False
        for var_name, details in variable_mapping.items():
            if col.lower() in [name.lower() for name in details['possible_names']]:
                column_mapping[col] = var_name
                matched = True
                break
        if not matched:
            unused_columns.append(col)

    # Rename columns based on the mapping
    df = df.rename(columns=column_mapping)

    # Drop unused columns and print a message
    if unused_columns:
        print(f"Removing columns not found in dictionary: {unused_columns}")
        df = df.drop(columns=unused_columns)

    # Define the chunk size
    chunk_size = 10_000_000

    # Split the dataframe into a list of smaller dataframes
    dataframes = [df[i:i + chunk_size] for i in range(0, len(df), chunk_size)]

    if not all(col in dataframes[0].columns for col in ['latitude', 'longitude']):
        processed_dfs = []
        for df in dataframes:
            # Calculate latitude and longitude from X and Y and the CRS
            lat, lon = utm_to_latlon(df['X'].values, df['Y'].values, cf_crs)
            df['latitude'], df['longitude'] = lat, lon
            processed_dfs.append(df)
        dfs = processed_dfs
    else:
        pass

    combined_df = combine_dataframes(dfs)

    return combined_df

def read_hyspex(hdr_filepath):
    # TODO: NORCE will send a python function to calibrate these values.
    # Function to read Hyspex image and flatten it to a pandas dataframe
    hdr = sp.envi.open(hdr_filepath)
    wavelengths = hdr.bands.centers

    spectral_data = hdr.load()
    spectral_data_flattened = spectral_data.reshape(-1, hdr.nbands) # Flatten the data
    # Columns: wavelengths, 1 row per point
    df = pd.DataFrame(spectral_data_flattened, columns=wavelengths)
    return df