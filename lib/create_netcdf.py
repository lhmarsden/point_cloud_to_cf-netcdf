#!/usr/bin/env python3
import netCDF4 as nc
from datetime import datetime
import numpy as np
import pyproj
import yaml


class NetCDF:

    def __init__(self, output_filepath):
        self.output_filepath = output_filepath
        self.ncfile = nc.Dataset(self.output_filepath, mode='w', format='NETCDF4')

    def calculate_vertical_bounds(self, altitude_values):
        return np.min(altitude_values), np.max(altitude_values)

    def define_grid_mapping(self, cf_crs):
        '''
        Write the CRS variable with the projection
        '''
        crs = self.ncfile.createVariable('crs', 'i4')

        for attr, value in cf_crs.items():
            crs.setncattr(attr, value)

    def write_coordinate_variables(self, ply_df, wavelength_df):

        if wavelength_df:
            num_points, num_bands = wavelength_df.shape
            wavelengths = wavelength_df.columns
        else:
            num_points = len(ply_df)
            num_bands = None
            wavelengths = None

        # Define a dimension as an arbitrary counter for the points
        self.ncfile.createDimension('point', size=num_points)
        # Write coordinate variable
        point_var = self.ncfile.createVariable('point', 'f4', ('point',))
        point_var[:] = range(num_points)
        # Adding variable attributes
        point_var.setncattr('units', '1')
        point_var.setncattr('long_name', 'Arbitrary counter for number of points in the point cloud')
        point_var.setncattr('standard_name', 'number_of_observations')
        point_var.setncattr('coverage_content_type', 'coordinate')

        if num_bands:
            # Define a dimension and coordinate variable for the wavelength bands
            self.ncfile.createDimension('band', size=num_bands)
            wavelength_var = self.ncfile.createVariable('band', 'f4', ('band',))
            wavelength_var[:] = wavelengths

            wavelength_var.setncattr('units', 'nanometers')
            wavelength_var.setncattr('long_name', 'Spectral band')
            wavelength_var.setncattr('standard_name', 'radiation_wavelength')
            wavelength_var.setncattr('coverage_content_type', 'coordinate')

    def write_1d_data(self, ply_df):

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
            longitude.setncattr('coverage_content_type', 'coordinate')

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
            latitude.setncattr('coverage_content_type', 'coordinate')

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
            altitude.setncattr('coverage_content_type', 'coordinate')

        # Check and initialise the x variable
        if 'X' in ply_df.columns or 'x' in ply_df.columns:
            x_column = 'X' if 'X' in ply_df.columns else 'x'
            x = self.ncfile.createVariable('X', 'f4', ('point',))
            # Add values to the x variable
            x[:] = ply_df[x_column]
            # Assign x variable attributes
            x.setncattr('units', 'meters')
            x.setncattr('long_name', 'X coordinate')
            x.setncattr('standard_name', 'projection_x_coordinate')
            x.setncattr('grid_mapping', 'crs')
            x.setncattr('coverage_content_type', 'coordinate')

        # Check and initialise the y variable
        if 'Y' in ply_df.columns or 'y' in ply_df.columns:
            y_column = 'Y' if 'Y' in ply_df.columns else 'y'
            y = self.ncfile.createVariable('Y', 'f4', ('point',))
            # Add values to the y variable
            y[:] = ply_df[y_column]
            # Assign y variable attributes
            y.setncattr('units', 'meters')
            y.setncattr('long_name', 'Y coordinate')
            y.setncattr('standard_name', 'projection_y_coordinate')
            y.setncattr('grid_mapping', 'crs')
            y.setncattr('coverage_content_type', 'coordinate')

        # Check and initialise the z variable
        if 'Z' in ply_df.columns or 'z' in ply_df.columns:
            z_column = 'Z' if 'Z' in ply_df.columns else 'z'
            z = self.ncfile.createVariable('Z', 'f4', ('point',))
            # Add values to the z variable
            z[:] = ply_df[z_column]
            # Assign z variable attributes
            z.setncattr('units', 'meters')
            z.setncattr('long_name', 'Z coordinate')
            z.setncattr('standard_name', 'height')
            z.setncattr('grid_mapping', 'crs')
            z.setncattr('coverage_content_type', 'coordinate')

        # Check and initialise the red variable
        if 'red' in ply_df.columns:
            red = self.ncfile.createVariable('red', 'f4', ('point',))
            # Add values to the red variable
            red[:] = ply_df['red']
            # Assign red variable attributes
            red.setncattr('units', '1')
            red.setncattr('long_name', 'red channel')
            red.setncattr('coverage_content_type', 'physicalMeasurement')
            if 'latitude' in ply_df.columns and 'longitude' in ply_df.columns:
                red.setncattr('coordinates', 'latitude longitude')

        # Check and initialise the green variable
        if 'green' in ply_df.columns:
            green = self.ncfile.createVariable('green', 'f4', ('point',))
            # Add values to the green variable
            green[:] = ply_df['green']
            # Assign green variable attributes
            green.setncattr('units', '1')
            green.setncattr('long_name', 'green channel')
            green.setncattr('coverage_content_type', 'physicalMeasurement')
            if 'latitude' in ply_df.columns and 'longitude' in ply_df.columns:
                green.setncattr('coordinates', 'latitude longitude')

        # Check and initialise the blue variable
        if 'blue' in ply_df.columns:
            blue = self.ncfile.createVariable('blue', 'f4', ('point',))
            # Add values to the blue variable
            blue[:] = ply_df['blue']
            # Assign blue variable attributes
            blue.setncattr('units', '1')
            blue.setncattr('long_name', 'blue channel')
            blue.setncattr('coverage_content_type', 'physicalMeasurement')
            if 'latitude' in ply_df.columns and 'longitude' in ply_df.columns:
                blue.setncattr('coordinates', 'latitude longitude')

        # Check and initialise the nomals
        # TODO: Check whether these should be written to the NetCDF file
        """ if 'nx' in ply_df.columns:
            nx = self.ncfile.createVariable('nx', 'f4', ('point',))
            nx[:] = ply_df['nx']
            nx.setncattr('units', '1')
            nx.setncattr('long_name', 'terrain normal vector, x channel')
            nx.setncattr('coverage_content_type', 'physicalMeasurement')
            if 'latitude' in ply_df.columns and 'longitude' in ply_df.columns:
                nx.setncattr('coordinates', 'latitude longitude')
        if 'ny' in ply_df.columns:
            ny = self.ncfile.createVariable('ny', 'f4', ('point',))
            ny[:] = ply_df['ny']
            ny.setncattr('units', '1')
            ny.setncattr('long_name', 'terrain normal vector, y channel')
            ny.setncattr('coverage_content_type', 'physicalMeasurement')
            if 'latitude' in ply_df.columns and 'longitude' in ply_df.columns:
                ny.setncattr('coordinates', 'latitude longitude')
        if 'nz' in ply_df.columns:
            nz = self.ncfile.createVariable('nz', 'f4', ('point',))
            nz[:] = ply_df['nz']
            nz.setncattr('units', '1')
            nz.setncattr('long_name', 'terrain normal vector, z channel')
            nz.setncattr('coverage_content_type', 'physicalMeasurement')
            if 'latitude' in ply_df.columns and 'longitude' in ply_df.columns:
                nz.setncattr('coordinates', 'latitude longitude') """

    def write_2d_data(self, wavelength_df):

        # Initialize the variable
        intensity = self.ncfile.createVariable('intensity', 'f4', ('point','band'))

        # Add values to the intensity variable
        intensity[:] = wavelength_df

        # Assign intensity variable attributes
        intensity.setncattr('units', 'W m-2 sr-1 m-1')
        intensity.setncattr('long_name', 'Spectral intensity')
        intensity.setncattr('standard_name', 'toa_outgoing_radiance_per_unit_wavelength')
        intensity.setncattr('coverage_content_type', 'physicalMeasurement')

        if 'latitude' in self.ncfile.variables and 'longitude' in self.ncfile.variables:
            intensity.setncattr('coordinates', 'latitude longitude')

    def assign_global_attributes_from_data_or_code(self,ply_df):

        altitude_values = self.ncfile.variables['altitude'][:]

        # Derive bounding box for coordinates based on data
        self.ncfile.setncattr('geospatial_lat_min', ply_df['latitude'].min())
        self.ncfile.setncattr('geospatial_lat_max', ply_df['latitude'].max())
        self.ncfile.setncattr('geospatial_lon_min', ply_df['longitude'].min())
        self.ncfile.setncattr('geospatial_lon_max', ply_df['longitude'].max())

        # Calculate vertical bounds
        vertical_min, vertical_max = self.calculate_vertical_bounds(altitude_values)
        self.ncfile.setncattr('geospatial_vertical_min', vertical_min)
        self.ncfile.setncattr('geospatial_vertical_max', vertical_max)

        # Get the current timestamp in ISO8601 format
        current_timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        self.ncfile.setncattr('date_created', current_timestamp)
        self.ncfile.setncattr('history', f'{current_timestamp}: File created using netCDF4 using Python.')

    def assign_global_attributes_from_user(self,global_attributes):
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


def create_netcdf(ply_df, wavelength_df, output_filepath, global_attributes, cf_crs):
    '''
    ply_df : pandas dataframe with columns including latitude, longitude, z
    wavelength_df: frequency bands and intensity values. None if not provided.
    global_attributes : python dictionary of global attributes
    output_filepath: where to write the netcdf file
    cf_crs: Python dictionary of the key value pairs for the variable attributes of the CRS variable.
    '''
    netcdf = NetCDF(output_filepath)
    netcdf.write_coordinate_variables(ply_df,wavelength_df)
    if cf_crs:
        netcdf.define_grid_mapping(cf_crs)
    netcdf.write_1d_data(ply_df)
    if wavelength_df:
        netcdf.write_2d_data(wavelength_df)
    netcdf.assign_global_attributes_from_data_or_code(ply_df)
    netcdf.assign_global_attributes_from_user(global_attributes)
    netcdf.close()
