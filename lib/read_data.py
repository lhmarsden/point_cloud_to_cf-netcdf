import pandas as pd
import numpy as np
import spectral as sp
from plyfile import PlyData
from pyproj import Transformer, CRS
import laspy
import gc
import logging
import os
import re
from typing import Generator, Tuple
from lib.hyspex_calibration import HyspexRad


logger = logging.getLogger(__name__)

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


def get_cf_crs(ply_filepath=None, proj4str=None):
    """
    Get a dictionary of variable attributes to write to the CRS variable
    From a PROJ.4 string in the comment in the PLY file header
    """
    errors = []
    warnings = []

    if ply_filepath:
        try:
            comment_str = get_ply_comment(ply_filepath)
            # get projection string from the comment
            ind_crs = comment_str.find("utm_crs")
            if ind_crs == -1:
                return None

            proj4str = comment_str[ind_crs:].split(";")[0].split("utm_crs")[1]
            proj4str = proj4str[proj4str.find("=")+1:]
            crs = CRS.from_proj4(proj4str)
            cf_crs = crs.to_cf()
        except:
            warnings.append("Unable to compute CRS from proj4str in comments of header in PLY file. This is not required if latitude and longitude are already in the PLY file. You can alternatively use the proj4str or crs_config arguments.")
    elif proj4str:
        try:
            crs = CRS.from_proj4(proj4str)
            cf_crs = crs.to_cf()
        except:
            errors.append("Unable to compute CRS from proj4str provided")
    else:
        cf_crs = None
        errors.append("Couldn't find proj4str to compute CRS variable from")

    return cf_crs, errors, warnings


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
    variable_list = ['blue', 'red', 'green', 'scan_angle_rank', 'epoch', 'intensity']

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

def read_hyspex_stream(
    hdr_filepath: str,
    start_line: int,
    end_line: int,
    chunk_size: int = 1000,
    need_to_calibrate: bool = False,
    progress_interval: int = 1000,
) -> Tuple[Generator[np.ndarray, None, None], np.ndarray]:
    """
    Stream hyspex data line ranges as NumPy chunks.

    Returns:
        (generator, wavelengths)
        - generator yields np.ndarray of shape (n_pixels, nbands) dtype float32
        - wavelengths is the 1D array of band centres (same length as nbands)

    Notes:
    - chunk_size: number of *lines* to accumulate before yielding. Each line contributes number_of_samples pixels.
    - start_line and end_line are inclusive.
    - interleave must be 'bil' (function will raise ValueError otherwise).
    """
    hdr = sp.envi.open(hdr_filepath)
    wavelengths = np.asarray(hdr.bands.centers)
    nbands = int(hdr.nbands)

    # parse header for samples & interleave (robust to whitespace)
    number_of_samples = None
    interleave = None
    with open(hdr_filepath, 'r') as hdr_file:
        for line in hdr_file:
            if re.match(r"^\s*samples\s*=", line, flags=re.IGNORECASE):
                number_of_samples = int(line.split('=')[1].strip())
            elif re.match(r"^\s*interleave\s*=", line, flags=re.IGNORECASE):
                interleave = line.split('=')[1].strip().lower()

    if number_of_samples is None or interleave is None:
        raise ValueError(f"Couldn't read 'samples' or 'interleave' from {hdr_filepath}")

    if interleave != 'bil':
        raise ValueError(f"Unsupported interleave='{interleave}'. This reader expects 'bil'.")

    hyspex_file = os.path.splitext(hdr_filepath)[0] + ".hyspex"
    hrad = HyspexRad(hyspex_file)

    total_lines = end_line - start_line + 1
    logger.info(f"Streaming lines {start_line}..{end_line} ({total_lines} lines), chunk_size={chunk_size}")

    def _generator():
        buffer = []
        lines_in_buffer = 0
        processed_lines = 0

        # iterate inclusive
        for line in range(start_line, end_line + 1):
            processed_lines += 1
            if (processed_lines % progress_interval) == 0:
                logger.info(f"Read progress: processed {processed_lines} / {total_lines} lines")

            # create indices for this single line
            line_index = [line] * number_of_samples
            sample_index = list(range(number_of_samples))

            if need_to_calibrate:
                # calibrate_spectrum may return shape (n_samples, nbands) or (1, n_samples, nbands)
                calibrated_line = hrad.calibrate_spectrum(line_index, sample_index)
                line_arr = np.asarray(calibrated_line).reshape(-1, nbands)
            else:
                # raw BIL access (match your original indexing)
                raw_line = hrad.img_bil[line_index, :, sample_index].T
                line_arr = np.asarray(raw_line).reshape(-1, nbands)

            # ensure float32 (smaller memory footprint) — adjust if you need higher precision
            buffer.append(line_arr.astype(np.float32, copy=False))
            lines_in_buffer += 1

            if lines_in_buffer >= chunk_size:
                # stack and yield
                stacked = np.vstack(buffer)  # shape (chunk_lines * samples, nbands)
                yield stacked
                buffer.clear()
                lines_in_buffer = 0

        # yield any remainder
        if buffer:
            stacked = np.vstack(buffer)
            yield stacked

    return _generator(), wavelengths
