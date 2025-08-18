import logging
import numpy as np
from dateutil.parser import isoparse

logger = logging.getLogger(__name__)

def validate_time_format(time_string):
    try:
        isoparse(time_string)
        return True
    except ValueError:
        return False

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
