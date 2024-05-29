import re

def validate_time_format(time_string):
    # Regular expression to match the format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ
    pattern = r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$'
    return bool(re.match(pattern, time_string))