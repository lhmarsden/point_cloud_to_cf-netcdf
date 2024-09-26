import json
import os
import yaml
import numpy as np
from lib.utils import validate_time_format
from datetime import datetime, timezone


# Attributes derived during the code that the user does not need to provide
derived_attributes = [
    'date_created',
    'history',
    'geospatial_lat_min',
    'geospatial_lat_max',
    'geospatial_lon_min',
    'geospatial_lon_max',
    'Conventions',
    'featureType'
]

# Required attrbutes
required_attributes = [
    'title',
    'summary',
    'keywords',
    'keywords_vocabulary',
    'geospatial_lat_min',
    'geospatial_lat_max',
    'geospatial_lon_min',
    'geospatial_lon_max',
    'time_coverage_start',
    'time_coverage_end',
    'Conventions',
    'date_created',
    'creator_type',
    'creator_email',
    'creator_institution',
    'creator_url',
    'publisher_name',
    'publisher_email',
    'publisher_url',
    'project',
    'license',
    'featureType'
]

# Attributes that should have float values
float_attributes = [
    'geospatial_lat_min',
    'geospatial_lat_max',
    'geospatial_lon_min',
    'geospatial_lon_max',
    'geospatial_vertical_min',
    'geospatial_vertical_max'
]


class GlobalAttributes:

    def __init__(self):
        self.data = None

    def read_global_attributes(self, arg):
        """Determine if the argument is a file path (YAML) or a JSON string and read global attributes accordingly."""
        if os.path.isfile(arg):
            self.dict = self._read_from_yaml_file(arg)
        else:
            self.dict = self._read_from_json_string(arg)

    def _read_from_yaml_file(self, filepath):
        """Read global attributes from a YAML file."""
        with open(filepath, 'r') as file:
            data = yaml.safe_load(file)
        attributes = {key: value.get('value', None) for key, value in data.items() if value.get('value')}
        return attributes

    def _read_from_json_string(self, json_string):
        """Parse JSON string."""
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            raise ValueError('Invalid JSON data.')

    def reformat_attributes(self):
        '''
        Converting attribute values to required format
        For example, geospatial bounds must be floats
        '''
        # List to store errors
        errors = []
        warnings = []

        # Iterate through the dictionary
        for key, value in self.dict.items():
            try:
                if key in float_attributes:
                    # Convert value to float
                    self.dict[key] = float(value)
                else:
                    # Convert value to string
                    self.dict[key] = str(value)
            except ValueError:
                # Append to errors list if conversion fails
                errors.append(f"Error converting {key} to {'float' if key in float_attributes else 'string'}.")

        return errors, warnings

    def derive(self, ply_df):
        '''
        Derive global attributes in code or from PLY file
        Attributes will only be written if the user has not provided them
        '''
        # Derive bounding box for coordinates based on data
        self.dict.setdefault('geospatial_lat_min', ply_df['latitude'].min())
        self.dict.setdefault('geospatial_lat_max', ply_df['latitude'].max())
        self.dict.setdefault('geospatial_lon_min', ply_df['longitude'].min())
        self.dict.setdefault('geospatial_lon_max', ply_df['longitude'].max())
        self.dict.setdefault('geospatial_vertical_min', ply_df['z'].min())
        self.dict.setdefault('geospatial_vertical_max', ply_df['z'].max())

        # Get the current timestamp in ISO8601 format
        current_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.dict.setdefault('date_created', current_timestamp)
        self.dict.setdefault('history', f'{current_timestamp}: File created using the netCDF4 library in Python.')

        self.dict.setdefault('Conventions', 'CF-1.8, ACDD-1.3')
        self.dict.setdefault('featureType', 'point')

    def check(self):
        '''
        Check the values that the user has provided for the global attributes
        '''
        # List of errors that will be appended to throughout this function.
        # If there are any errors, no CF-NetCDF file will be created
        errors = []

        # List of warnings that will be appended to throughout this function
        # Warnings will be flagged to the user but this alone will not stop a CF-NetCDF file from being created
        warnings = []

        for required_attribute in required_attributes:
            if required_attribute not in self.dict.keys():
                errors.append(f'"{required_attribute}" is a required global attribute. Please provide a value')
        if len(errors) > 0:
            return errors, warnings

        for attribute, value in self.dict.items():

            if value in ['nan', np.nan, None, '']:
                if attribute in required_attributes and attribute not in derived_attributes:
                    errors.append(f'"{attribute}" is a required global attribute. Please provide a value')
                else:
                    pass
            else:
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

        geospatial_lat_min = self.dict['geospatial_lat_min']
        geospatial_lat_max = self.dict['geospatial_lat_max']
        geospatial_lon_min = self.dict['geospatial_lon_min']
        geospatial_lon_max = self.dict['geospatial_lon_max']
        time_coverage_start = self.dict['time_coverage_start']
        time_coverage_end = self.dict['time_coverage_end']

        if geospatial_lat_min > geospatial_lat_max:
            errors.append('geospatial_lat_max must be greater than or equal to geospatial_lat_min')

        if geospatial_lon_min > geospatial_lon_max:
            errors.append('geospatial_lon_max must be greater than or equal to geospatial_lon_min')

        if time_coverage_start > time_coverage_end:
            errors.append('time_coverage_end must be greater than or equal to time_coverage_start')

        return errors, warnings