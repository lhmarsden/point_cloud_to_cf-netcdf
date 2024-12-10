import json
import os
import yaml
import numpy as np
from lib.utils import validate_time_format
from datetime import datetime, timezone

# Required attrbutes
required_attributes = [
    'units',
    'long_name',
    'standard_name',
    'coverage_content_type'
]

class VariableMapping:

    def __init__(self):
        self.data = None

    def read_variable_mapping(self, filepath):
        """Read variable mapping from yaml file"""
        with open(filepath, 'r') as file:
            self.dict = yaml.safe_load(file)

    def check_variable_names(self, variable_names):
        # Flatten all possible_names into a set of lowercase names for faster, case-insensitive lookup
        all_possible_names = {
            name.lower() for details in self.dict.values() for name in details["possible_names"]
        }
        # Normalise variable_names to lowercase and check for unrecognised names
        warnings = [
            f"({name} is not recognised as a possible name for any variable in the variable mapping file. The variable shall be ignored.)"
            for name in variable_names if name.lower() not in all_possible_names
        ]
        return warnings

    def check(self, variable_names):
        '''
        Check the values that the user has provided for the variable attributes
        '''
        # List of errors that will be appended to throughout this function.
        # If there are any errors, no CF-NetCDF file will be created
        errors = []

        # List of warnings that will be appended to throughout this function
        # Warnings will be flagged to the user but this alone will not stop a CF-NetCDF file from being created
        warnings = self.check_variable_names(variable_names)

        for variable in self.dict.keys():
            if 'possible_names' in self.dict[variable].keys():
                if variable in self.dict[variable]['possible_names']:
                    # Check only variables that are in the PLY or HYSPEX file
                    for required_attribute in required_attributes:
                        if 'attributes' in self.dict[variable].keys():
                            if required_attribute not in self.dict[variable]['attributes'].keys():
                                errors.append(f'"{required_attribute}" is a required variable attribute. Please provide a value for {variable}')
                        else:
                            errors.append(f'No "attributes" key found for the {variable} variable')
                        # for attribute, value in self.dict[variable]['attributes'].items():
                        #     if attribute == 'standard_name':
                        # TODO: Check standard_name values against the standard_name table
                else:
                    warnings.append(f"The variable '{variable}' in the mapping file has not been found in the input data. Skipping")
            else:
                warnings.append(f"The variable '{variable}' in the mapping file has no 'possible_names' key so can't be mapped nor written to the CF-NetCDF file. Skipping.")

        return errors, warnings