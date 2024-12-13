import re
import spectral as sp
import logging

logger = logging.getLogger(__name__)

def validate_time_format(time_string):
    # Regular expression to match the format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ
    pattern = r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$'
    return bool(re.match(pattern, time_string))

def define_chunk_size(pc_df, hdr_filepath):
    errors = []
    try:
        if hdr_filepath:
            hdr = sp.envi.open(hdr_filepath)
            number_of_samples = None
            interleave = None

            # Read the file and extract the required fields
            with open(hdr_filepath, 'r') as hdr_file:
                for line in hdr_file:
                    if re.match(r"^samples\s*=", line):
                        number_of_samples = int(line.split('=')[1].strip())
            if interleave == 'bil': # Data organised line by line
                logger.info(f'Data will be divided into chunks line by line')
                chunk_size = number_of_samples
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