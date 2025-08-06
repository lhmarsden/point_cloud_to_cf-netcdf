#!/usr/bin/env python3
import netCDF4 as nc
import numpy as np
import logging
from lib.utils import scale_to_integers

logger = logging.getLogger(__name__)

class NetCDF:

    def __init__(self, output_filepath):
        self.output_filepath = output_filepath
        self.ncfile = nc.Dataset(self.output_filepath, mode='w', format='NETCDF4')

    # def calculate_vertical_bounds(self, altitude_values):
    #     return np.min(altitude_values), np.max(altitude_values)

    def define_grid_mapping(self, cf_crs):
        '''
        Write the CRS variable with the projection
        '''
        crs = self.ncfile.createVariable('crs', 'i4')

        for attr, value in cf_crs.items():
            crs.setncattr(attr, value)

    def write_coordinate_variables(self, pc_df, wavelength_df, variable_mapping):

        if wavelength_df is not None and not wavelength_df.empty:
            num_points, num_bands = wavelength_df.shape
            wavelengths = wavelength_df.columns
        else:
            num_points = len(pc_df)
            num_bands = None
            wavelengths = None

        # Define a dimension as an arbitrary counter for the points
        self.ncfile.createDimension('point', size=num_points)
        # Write coordinate variable
        point_var = self.ncfile.createVariable('point', 'f4', ('point',), zlib=True, complevel=1)
        point_var[:] = range(num_points)
        # Adding variable attributes
        point_var.setncattr('units', '1')
        point_var.setncattr('long_name', 'Arbitrary counter for number of points in the point cloud')
        point_var.setncattr('standard_name', 'number_of_observations')
        point_var.setncattr('coverage_content_type', 'coordinate')
        logger.info('Wrote a coordinate variable for each point')

        if num_bands:
            # Define a dimension and coordinate variable for the wavelength bands
            self.ncfile.createDimension('band', size=num_bands)
            wavelength_var = self.ncfile.createVariable('band', 'f4', ('band',), zlib=True, complevel=1)
            wavelength_var[:] = wavelengths

            wavelength_var.setncattr('units', 'nanometers')
            wavelength_var.setncattr('long_name', 'Spectral band')
            wavelength_var.setncattr('standard_name', 'radiation_wavelength')
            wavelength_var.setncattr('coverage_content_type', 'coordinate')
            logger.info('Wrote a coordinate variable for each wavelength band')

    def write_1d_data(self, pc_df, variable_mapping, chunk_size):

        # Loop through columns in input data
        for col in pc_df.columns:
            # Loop through variables in mapping configuration file
            for variable in variable_mapping.keys():
                if 'possible_names' in variable_mapping[variable].keys():
                    # Matching input data to variable in config file with metadata
                    if col in variable_mapping[variable]['possible_names']:
                        # Initialising variable
                        netcdf_variable = self.ncfile.createVariable(
                            variable,
                            variable_mapping[variable]['dtype'],
                            ('point',),
                            zlib=True,
                            complevel=1,
                            chunksizes=(chunk_size,)
                            )
                        # Writing data to variable
                        netcdf_variable[:] = pc_df[col]
                        # Writing variable attributes
                        for attribute, value in variable_mapping[variable]['attributes'].items():
                            netcdf_variable.setncattr(attribute, value)
                        logger.info(f'Data and metadata written to {variable} variable')

    def write_2d_data(self, wavelength_df, variable_mapping, chunk_size):

        num_points, num_bands = wavelength_df.shape

        # Initialize the variable
        intensity = self.ncfile.createVariable(
            'intensity',
            'i4',
            ('point','band'),
            zlib=True,
            complevel=9, #TODO: Test complevel on file size
            chunksizes=(chunk_size,num_bands)
            )

        # Add values to the intensity variable
        wavelength_array = wavelength_df.to_numpy()
        scale_factor = 1e-6
        intensity[:] = scale_to_integers(wavelength_array, scale_factor)

        # Assign intensity variable attributes
        for attribute, value in variable_mapping['intensity']['attributes'].items():
            intensity.setncattr(attribute, value)

        intensity.setncattr('scale_factor', scale_factor)

        logger.info('2D intensity data and metadata written to file')

    def assign_global_attributes(self,global_attributes):
        for attribute, value in global_attributes.items():
            if attribute not in self.ncfile.ncattrs() and value not in [np.nan, '', 'None', None, 'nan']:
                # if format == 'string':
                #     self.ncfile.setncattr_string(attribute, value)
                # elif format == 'number':
                #     value = float(value)
                #     self.ncfile.setncattr(attribute, value)
                # else:
                self.ncfile.setncattr(attribute, value)

    def close(self):
        # Close the file
        self.ncfile.close()


def create_netcdf(pc_df, wavelength_df, variable_mapping, output_filepath, global_attributes, cf_crs, chunk_size):
    '''
    pc_df : pandas dataframe with columns including latitude, longitude, z
    wavelength_df: frequency bands and intensity values. None if not provided.
    global_attributes : python dictionary of global attributes
    output_filepath: where to write the netcdf file
    cf_crs: Python dictionary of the key value pairs for the variable attributes of the CRS variable.
    variable_mapping: Python dictionary containing the variable names and attributes
    chunk_size: Chunk size to divide data into along the point dimension
    '''
    # TODO: Need to reduce file size (32 Gb). Compression didn't help. Precision of values, scale_factor could be useful. Then store data in int32 or int16.
    netcdf = NetCDF(output_filepath)
    netcdf.write_coordinate_variables(pc_df,wavelength_df,variable_mapping)
    if cf_crs:
        netcdf.define_grid_mapping(cf_crs)
    netcdf.write_1d_data(pc_df, variable_mapping, chunk_size)
    if wavelength_df is not None and not wavelength_df.empty:
        netcdf.write_2d_data(wavelength_df, variable_mapping, chunk_size)
    netcdf.assign_global_attributes(global_attributes)
    netcdf.close()
