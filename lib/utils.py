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

def scale_to_integers(arr, max_scale=1e6):
    """
    Scale a float NumPy array to integers using the smallest power-of-10 scale factor
    that preserves all precision, up to a sensible limit (default 1e6).

    Parameters:
        arr (np.ndarray): Input array of type float32.
        max_scale (int or float): Maximum scale factor to try (e.g. 1e6 for 6 decimal places).

    Returns:
        scaled_array (np.ndarray): Integer array with preserved precision.
        scale_factor (int): The scale factor used (e.g. 100000 for 5 decimal places).
    """
    if arr.dtype != np.float32:
        raise TypeError("Input array must be of type float32")

    max_decimal_places = int(np.log10(max_scale)) + 1

    for i in range(max_decimal_places):
        scale = 10 ** i
        scaled = arr * scale

        # Check if values are close enough to integers after scaling
        if np.allclose(scaled, np.round(scaled), rtol=0, atol=1e-6):
            return np.round(scaled).astype(np.int32), scale

    raise ValueError(f"No suitable scale factor found up to {int(max_scale):,}")