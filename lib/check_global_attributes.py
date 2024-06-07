import re

def validate_time_format(time_string):
    # Regular expression to match the format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ
    pattern = r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$'
    return bool(re.match(pattern, time_string))

def check_global_attributes(attributes):
    errors = []
    for attribute, value in attributes.items():

        if attribute in ['time_coverage_start', 'time_coverage_end', 'date_created']:
            if validate_time_format(value) == False:
                errors.append(f'{attribute} must be in the format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ')

        if attribute in ['geospatial_lat_min', 'geospatial_lat_max']:
            if -90 <= float(value) <= 90:
                pass
            else:
                errors.append(f'{attribute} must be between -90 and 90 inclusive')

        if attribute in ['geospatial_lon_min', 'geospatial_lon_max']:
            if -180 <= float(value) <= 180:
                pass
            else:
                errors.append(f'{attribute} must be between -180 and 180 inclusive')

    if attributes['geospatial_lat_min'] > attributes['geospatial_lat_max']:
        errors.append('geospatial_lat_max must be greater than or equal to geospatial_lat_min')

    if attributes['geospatial_lon_min'] > attributes['geospatial_lon_max']:
        errors.append('geospatial_lon_max must be greater than or equal to geospatial_lon_min')

    if attributes['time_coverage_start'] > attributes['time_coverage_end']:
        errors.append('time_coverage_end must be greater than or equal to time_coverage_start')

    return errors