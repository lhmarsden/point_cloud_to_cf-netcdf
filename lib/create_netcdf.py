#!/usr/bin/env python3
import netCDF4 as nc
from datetime import datetime
import numpy as np
import pyproj


class NetCDF:

    def __init__(self, output_filepath):
        self.output_filepath = output_filepath
        self.ncfile = nc.Dataset(self.output_filepath, mode='w', format='NETCDF4')

    def transform_coordinates(self, x_values, y_values):
        # TODO: transformation of longitude values is incorrect. Latitudes look okay based on one example
        # TODO: could be an issue with the projection provided?
        # Extract projection parameters from the 'crs' variable
        projection_params = {
            'proj': 'tmerc',
            'lat_0': self.ncfile.variables['crs'].latitude_of_projection_origin,
            'lon_0': self.ncfile.variables['crs'].longitude_of_central_meridian,
            'k_0': self.ncfile.variables['crs'].scale_factor_at_central_meridian,
            'x_0': self.ncfile.variables['crs'].false_easting,
            'y_0': self.ncfile.variables['crs'].false_northing,
            'ellps': 'WGS84'  # Assuming WGS84 ellipsoid, adjust if needed
        }

        # Define the projection using the extracted parameters
        proj = pyproj.Transformer.from_proj(
            pyproj.Proj(**projection_params),
            pyproj.Proj(proj='latlong'),
        )

        # Transform coordinates
        lon, lat = proj.transform(x_values, y_values)
        return lon, lat

    def calculate_vertical_bounds(self, z_values):
        return np.min(z_values), np.max(z_values)

    def write_coordinate_variables(self, wavelength_df):

        num_points, num_bands = wavelength_df.shape
        wavelengths = wavelength_df.columns

        # Define a dimension as an arbitrary counter for the points
        self.ncfile.createDimension('point', size=num_points)
        # Define a dimension for the wavelength bands
        self.ncfile.createDimension('band', size=num_bands)

        # Write coordinate variables
        wavelength_var = self.ncfile.createVariable('band', 'f4', ('band',))
        wavelength_var[:] = wavelengths

        point_var = self.ncfile.createVariable('point', 'f4', ('point',))
        point_var[:] = range(num_points)

        # Adding variable attributes
        point_var.setncattr('units', '1')
        point_var.setncattr('long_name', 'Arbitrary counter for number of points in the point cloud')
        point_var.setncattr('standard_name', 'number_of_observations')
        point_var.setncattr('coverage_content_type', 'coordinate')

        wavelength_var.setncattr('units', 'nanometers')
        wavelength_var.setncattr('long_name', 'Spectral band')
        wavelength_var.setncattr('standard_name', 'radiation_wavelength')
        wavelength_var.setncattr('coverage_content_type', 'coordinate')

    def write_1d_data(self, ply_df):
        num_points = len(ply_df)

        # TODO: check whether length of ply_df matches number of points from hyspex file

        # Define grid mapping variable
        crs = self.ncfile.createVariable('crs', 'i4')
        crs.setncattr('grid_mapping_name', 'transverse_mercator')  # Example, adjust as needed
        crs.setncattr('longitude_of_prime_meridian', 0.0)
        crs.setncattr('semi_major_axis', 6378137.0)
        crs.setncattr('inverse_flattening', 298.257223563)
        crs.setncattr('latitude_of_projection_origin', 0.0)
        crs.setncattr('longitude_of_central_meridian', -111.0)
        crs.setncattr('false_easting', 500000.0)
        crs.setncattr('false_northing', 0.0)
        crs.setncattr('scale_factor_at_central_meridian', 0.9996)

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

        # Check and initialise the green variable
        if 'green' in ply_df.columns:
            green = self.ncfile.createVariable('green', 'f4', ('point',))
            # Add values to the green variable
            green[:] = ply_df['green']
            # Assign green variable attributes
            green.setncattr('units', '1')
            green.setncattr('long_name', 'green channel')
            green.setncattr('coverage_content_type', 'physicalMeasurement')

        # Check and initialise the blue variable
        if 'blue' in ply_df.columns:
            blue = self.ncfile.createVariable('blue', 'f4', ('point',))
            # Add values to the blue variable
            blue[:] = ply_df['blue']
            # Assign blue variable attributes
            blue.setncattr('units', '1')
            blue.setncattr('long_name', 'blue channel')
            blue.setncattr('coverage_content_type', 'physicalMeasurement')

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

    def assign_global_attributes_from_data_or_code(self,ply_df):

        x_values = self.ncfile.variables['X'][:]
        y_values = self.ncfile.variables['Y'][:]
        z_values = self.ncfile.variables['Z'][:]

        # Transform coordinates
        lon_values, lat_values = self.transform_coordinates(x_values, y_values)

        # Derive bounding box for coordinates based on data
        self.ncfile.setncattr('geospatial_lat_min', np.min(lat_values))
        self.ncfile.setncattr('geospatial_lat_max', np.max(lat_values))
        self.ncfile.setncattr('geospatial_lon_min', np.min(lon_values))
        self.ncfile.setncattr('geospatial_lon_max', np.max(lon_values))

        # Calculate vertical bounds
        vertical_min, vertical_max = self.calculate_vertical_bounds(z_values)
        self.ncfile.setncattr('geospatial_vertical_min', vertical_min)
        self.ncfile.setncattr('geospatial_vertical_max', vertical_max)

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


def create_netcdf(ply_df, wavelength_df, output_filepath, global_attributes):
    '''
    ply_df : pandas dataframe with columns including latitude, longitude, z
    global_attributes : python dictionary of global attributes
    output_filepath: where to write the netcdf file
    '''
    netcdf = NetCDF(output_filepath)
    netcdf.write_coordinate_variables(wavelength_df)
    netcdf.write_1d_data(ply_df)
    netcdf.write_2d_data(wavelength_df)
    netcdf.assign_global_attributes_from_data_or_code(ply_df)
    netcdf.assign_global_attributes_from_user(global_attributes)
    netcdf.close()
