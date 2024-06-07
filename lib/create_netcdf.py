#!/usr/bin/env python3
import netCDF4 as nc
from datetime import datetime
import numpy as np


class NetCDF:

    def __init__(self, output_filepath):
        self.output_filepath = output_filepath
        self.ncfile = nc.Dataset(self.output_filepath, mode='w', format='NETCDF4')

    def write_1d_data(self, ply_df):
        num_points = len(ply_df)
        # Define a single dimension as an arbtrary counter for the points
        self.ncfile.createDimension('point', size=num_points)

        # Check and initialise the longitude variable
        if 'longitude' in ply_df.columns:
            longitude = self.ncfile.createVariable('longitude', 'f4', ('point',))
            # Add values to the longitude variable
            longitude[:] = ply_df['longitude']
            # Assign longitude variable attributes
            longitude.setncattr('units', 'degrees_east')
            longitude.setncattr('long_name', 'longitude')
            longitude.setncattr('standard_name', 'longitude')
            longitude.setncattr('axis', 'X')
            longitude.setncattr('valid_range', [-180.0, 180.0])

        # Check and initialise the latitude variable
        if 'latitude' in ply_df.columns:
            latitude = self.ncfile.createVariable('latitude', 'f4', ('point',))
            # Add values to the latitude variable
            latitude[:] = ply_df['latitude']
            # Assign latitude variable attributes
            latitude.setncattr('units', 'degrees_north')
            latitude.setncattr('long_name', 'latitude')
            latitude.setncattr('standard_name', 'latitude')
            latitude.setncattr('axis', 'Y')
            latitude.setncattr('valid_range', [-90.0, 90.0])

        # Check and initialise the altitude variable
        if 'altitude' in ply_df.columns:
            altitude = self.ncfile.createVariable('altitude', 'f4', ('point',))
            # Add values to the altitude variable
            altitude[:] = ply_df['altitude']
            # Assign altitude variable attributes
            altitude.setncattr('units', 'meters')
            altitude.setncattr('long_name', 'geometric height above geoid')
            altitude.setncattr('standard_name', 'altitude')
            altitude.setncattr('positive', 'up')
            altitude.setncattr('axis', 'Z')
            altitude.setncattr('valid_range', [-10000.0, 10000.0])

        # Check and initialise the x variable
        if 'X' in ply_df.columns:
            x = self.ncfile.createVariable('X', 'f4', ('point',))
            # Add values to the x variable
            x[:] = ply_df['X']
            # Assign x variable attributes
            x.setncattr('units', 'meters')
            x.setncattr('long_name', 'X coordinate')

        # Check and initialise the y variable
        if 'Y' in ply_df.columns:
            y = self.ncfile.createVariable('Y', 'f4', ('point',))
            # Add values to the y variable
            y[:] = ply_df['Y']
            # Assign y variable attributes
            y.setncattr('units', 'meters')
            y.setncattr('long_name', 'Y coordinate')

        # Check and initialise the z variable
        if 'Z' in ply_df.columns:
            z = self.ncfile.createVariable('Z', 'f4', ('point',))
            # Add values to the z variable
            z[:] = ply_df['Z']
            # Assign z variable attributes
            z.setncattr('units', 'meters')
            z.setncattr('long_name', 'Z coordinate')

        # Check and initialise the red variable
        if 'red' in ply_df.columns:
            red = self.ncfile.createVariable('red', 'f4', ('point',))
            # Add values to the red variable
            red[:] = ply_df['red']
            # Assign red variable attributes
            red.setncattr('units', '1')
            red.setncattr('long_name', 'red channel')

        # Check and initialise the green variable
        if 'green' in ply_df.columns:
            green = self.ncfile.createVariable('green', 'f4', ('point',))
            # Add values to the green variable
            green[:] = ply_df['green']
            # Assign green variable attributes
            green.setncattr('units', '1')
            green.setncattr('long_name', 'green channel')

        # Check and initialise the blue variable
        if 'blue' in ply_df.columns:
            blue = self.ncfile.createVariable('blue', 'f4', ('point',))
            # Add values to the blue variable
            blue[:] = ply_df['blue']
            # Assign blue variable attributes
            blue.setncattr('units', '1')
            blue.setncattr('long_name', 'blue channel')

    def write_2d_data(self, wavelength_2d):

        num_points, num_bands = wavelength_2d.shape
        # Define a dimension for each band
        self.ncfile.createDimension('band', size=num_bands)

        # Initialize the variable
        intensity = self.ncfile.createVariable('intensity', 'f4', ('point','band'))

        # Add values to the intensity variable
        intensity[:] = wavelength_2d

        # Assign intensity variable attributes
        intensity.setncattr('units', 'degrees_east')
        intensity.setncattr('long_name', 'intensity')
        intensity.setncattr('standard_name', '')

    def assign_global_attributes_from_data_or_code(self,ply_df):

        # Derive bounding box for coordinates based on data
        self.ncfile.setncattr('geospatial_lat_min', ply_df['latitude'].min(skipna=True))
        self.ncfile.setncattr('geospatial_lat_max', ply_df['latitude'].max(skipna=True))
        self.ncfile.setncattr('geospatial_lon_min', ply_df['longitude'].min(skipna=True))
        self.ncfile.setncattr('geospatial_lon_max', ply_df['longitude'].max(skipna=True))
        self.ncfile.setncattr('geospatial_vertical_min', ply_df['altitude'].min(skipna=True))
        self.ncfile.setncattr('geospatial_vertical_max', ply_df['altitude'].max(skipna=True))

        # Get the current timestamp in ISO8601 format
        current_timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        self.ncfile.setncattr('date_created', current_timestamp)
        self.ncfile.setncattr('history', f'{current_timestamp}: File created using netCDF4 using Python.')

    def assign_global_attributes_from_user(self,global_attributes):
        # TODO: global attributes are not always strings. Values must be written in the appropriate format.
        # TODO: Handle attributes that haven't been written. Checker?
        # for attribute, value in global_attributes.items():
        #    if attribute not in self.ncfile.ncattrs() and value:
        #         self.ncfile.setncattr(attribute, value)
        for idx, row in global_attributes.df.iterrows():
            attribute = row['Attribute']
            value = row['value']
            format = row['format']
            if attribute not in self.ncfile.ncattrs() and value not in [np.nan, '', 'None', None, 'nan']:
                if format == 'string':
                    self.ncfile.setncattr_string(attribute, value)
                elif format == 'number':
                    value = float(value)
                    self.ncfile.setncattr(attribute, value)
                else:
                    self.ncfile.setncattr(attribute, value)

    def close(self):
        # Close the file
        self.ncfile.close()


def create_netcdf(ply_df, wavelength_2d, output_filepath, global_attributes):
    '''
    ply_df : pandas dataframe with columns including latitude, longitude, z
    global_attributes : python dictionary of global attributes
    output_filepath: where to write the netcdf file
    '''
    netcdf = NetCDF(output_filepath)
    netcdf.write_1d_data(ply_df)
    netcdf.write_2d_data(wavelength_2d)
    netcdf.assign_global_attributes_from_data_or_code(ply_df)
    netcdf.assign_global_attributes_from_user(global_attributes)
    netcdf.close()
