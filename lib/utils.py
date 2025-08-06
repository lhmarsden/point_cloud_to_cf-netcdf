import re
import spectral as sp
import logging
import numpy as np

logger = logging.getLogger(__name__)

def validate_time_format(time_string):
    # Regular expression to match the format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ
    pattern = r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$'
    return bool(re.match(pattern, time_string))

def define_chunk_size(pc_df, hdr_filepath):
    errors = []
    try:
        if hdr_filepath:
            number_of_samples = None
            interleave = None

            # Read the file and extract the required fields
            with open(hdr_filepath, 'r') as hdr_file:
                for line in hdr_file:
                    if re.match(r"^samples\s*=", line):
                        number_of_samples = int(line.split('=')[1].strip())
                    elif re.match(r"^interleave\s*=", line):
                        interleave = line.split('=')[1].strip()
            if interleave == 'bil': # Data organised line by line
                logger.info(f'Data will be divided into chunks line by line')
                chunk_size = number_of_samples
            else:
                chunk_size = None
        else:
            num_points = len(pc_df)
            if num_points > 2000000:
                chunk_size = 1000000
                logger.info(f'Data will be divided into chunks of {chunk_size} points')
            else:
                chunk_size = None

        return chunk_size, errors
    except:
        chunk_size = None
        errors = ['Error calculating chunk size to divide data into']
        return chunk_size, errors

def scale_to_integers(arr: np.ndarray, scale_factor, chunk_size: int = 1_000_000) -> np.ndarray:
    """
    Scales a float32 array to integers by multiplying by 1e6 and rounding.
    
    Parameters:
        arr (np.ndarray): Input array of dtype float32 with values expected in [0, 1].
        scale_factor: Value of scale_factor attribute to be written in CF-NetCDF file.
        chunk_size (int): Size of chunks for processing, to manage memory.
    
    Returns:
        np.ndarray: Array of int32 values representing arr * scale, rounded.
    """
    if arr.dtype != np.float32:
        raise TypeError("Input array must be of type float32")

    n = arr.size
    arr_flat = arr.ravel()
    scaled = np.empty_like(arr_flat, dtype=np.int32)

    scale = 1 / scale_factor

    for start in range(0, n, chunk_size):
        end = start + chunk_size
        chunk = arr_flat[start:end]
        scaled[start:end] = np.round(chunk * scale).astype(np.int32)

    return scaled.reshape(arr.shape)
