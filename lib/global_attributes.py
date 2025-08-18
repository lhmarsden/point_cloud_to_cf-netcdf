import json
import os
import yaml
import toml
import math
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
    'featureType',
    'naming_authority'
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

    def read_global_attributes(self, user_global_attributes_filepath, met_global_attributes_filepath):
        """Determine if the filepath is a file path (YAML) or a JSON string and read global attributes accordingly."""
        if os.path.isfile(user_global_attributes_filepath):
            # Extract the file extension
            _, ext = os.path.splitext(user_global_attributes_filepath)

            # Determine file type based on extension
            if ext in ['.yaml', '.yml']:
                user_global_attributes = self._read_from_yaml_file(user_global_attributes_filepath)
            elif ext == '.toml':
                user_global_attributes = self._read_from_toml_file(user_global_attributes_filepath)
        else:
            user_global_attributes = self._read_from_json_string(user_global_attributes_filepath)
        
        met_global_attributes = self._read_from_yaml_file(met_global_attributes_filepath)

        def clean_dict(d):
            # Remove NaN or empty-string values
            return {
                k: v for k, v in d.items()
                if not (
                    v == '' 
                    or (isinstance(v, float) and math.isnan(v)) 
                    or v is np.nan
                )
            }
        
        met_global_attributes = clean_dict(met_global_attributes)
        user_global_attributes = clean_dict(user_global_attributes)
        
        self.dict = {**met_global_attributes, **user_global_attributes}
        

    def _read_from_yaml_file(self, filepath):
        """Read global attributes from a YAML file."""
        with open(filepath, 'r') as file:
            data = yaml.safe_load(file)
        attributes = {key: value.get('value', None) for key, value in data.items() if value.get('value')}
        return attributes

    def _read_from_toml_file(self, filepath, sep='_'):
        """Read global attributes from a TOML file."""
        # Open and load the TOML file
        with open(filepath, 'r') as f:
            toml_data = toml.load(f)

        # Flatten the TOML data into a dictionary, ignoring parent keys
        flat_dict = {}
        stack = [toml_data]

        while stack:
            current_dict = stack.pop()
            for key, value in current_dict.items():
                if isinstance(value, dict):
                    # If it's a nested dictionary, add its values to the stack
                    stack.append(value)
                else:
                    # If it's not a dictionary, add the value to the flat_dict
                    flat_dict[key] = value

        return flat_dict

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
        self.dict.setdefault('geospatial_vertical_min', ply_df['Z'].min())
        self.dict.setdefault('geospatial_vertical_max', ply_df['Z'].max())

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
            if required_attribute not in self.dict.keys() and required_attribute not in derived_attributes:
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

        time_coverage_start = self.dict['time_coverage_start']
        time_coverage_end = self.dict['time_coverage_end']
        if time_coverage_start > time_coverage_end:
            errors.append('time_coverage_end must be greater than or equal to time_coverage_start')

        lat_min_key = 'geospatial_lat_min'
        lat_max_key = 'geospatial_lat_max'
        lon_min_key = 'geospatial_lon_min'
        lon_max_key = 'geospatial_lon_max'

        # Only check latitudes if both keys exist
        if lat_min_key in self.dict and lat_max_key in self.dict:
            geospatial_lat_min = self.dict[lat_min_key]
            geospatial_lat_max = self.dict[lat_max_key]
            if geospatial_lat_min > geospatial_lat_max:
                errors.append(f"{lat_max_key} must be greater than or equal to {lat_min_key}")

        # Only check longitudes if both keys exist
        if lon_min_key in self.dict and lon_max_key in self.dict:
            geospatial_lon_min = self.dict[lon_min_key]
            geospatial_lon_max = self.dict[lon_max_key]
            if geospatial_lon_min > geospatial_lon_max:
                errors.append(f"{lon_max_key} must be greater than or equal to {lon_min_key}")
        
        return errors, warnings