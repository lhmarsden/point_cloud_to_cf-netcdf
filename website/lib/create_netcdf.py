#!/usr/bin/env python3
import netCDF4 as nc
from datetime import datetime


class NetCDF:

    def __init__(self, output_filepath):
        self.output_filepath = output_filepath
        self.ncfile = nc.Dataset(self.output_filepath, mode='w', format='NETCDF4')

    def write_data(self, df):
        num_points = len(df)
        # Define a single dimension as an arbtrary counter for the points
        self.ncfile.createDimension('point', size=num_points)

        # Initialise the variables
        longitude = self.ncfile.createVariable('longitude', 'f4', ('point',))
        latitude = self.ncfile.createVariable('latitude', 'f4', ('point',))
        altitude = self.ncfile.createVariable('altitude', 'f4', ('point',))

        # Add values to the variables
        longitude[:] = df['longitude']
        latitude[:] = df['latitude']
        altitude[:] = df['altitude']

        # Assign variable attributes
        longitude.setncattr('units', 'degrees_east')
        longitude.setncattr('long_name', 'longitude')
        longitude.setncattr('standard_name', 'longitude')

        latitude.setncattr('units', 'degrees_north')
        latitude.setncattr('long_name', 'latitude')
        latitude.setncattr('standard_name', 'latitude')

        altitude.setncattr('units', 'meters')
        altitude.setncattr('long_name', 'geometric height above geoid')
        altitude.setncattr('standard_name', 'altitude')
        altitude.setncattr('positive', 'up')

    def assign_global_attributes_from_data_or_code(self,df):

        # Derive bounding box for coordinates based on data
        self.ncfile.setncattr('geospatial_lat_min', df['latitude'].min(skipna=True))
        self.ncfile.setncattr('geospatial_lat_max', df['latitude'].max(skipna=True))
        self.ncfile.setncattr('geospatial_lon_min', df['longitude'].min(skipna=True))
        self.ncfile.setncattr('geospatial_lon_max', df['longitude'].max(skipna=True))
        self.ncfile.setncattr('geospatial_vertical_min', df['altitude'].min(skipna=True))
        self.ncfile.setncattr('geospatial_vertical_max', df['altitude'].max(skipna=True))

        # Get the current timestamp in ISO8601 format
        current_timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        self.ncfile.setncattr('date_created', current_timestamp)
        self.ncfile.setncattr('history', f'{current_timestamp}: File created using netCDF4 using Python.')

    def assign_global_attributes_from_user(self,global_attributes):
        for attribute, value in global_attributes.items():
            print(attribute, value)
            if attribute not in self.ncfile.ncattrs() and value:
                self.ncfile.setncattr(attribute, value)

    def close(self):
        # Close the file
        self.ncfile.close()


def df_to_netcdf(df, output_filepath, global_attributes):
    '''
    df : pandas dataframe with columns including latitude, longitude, z
    global_attributes : python dictionary of global attributes
    output_filepath: where to write the netcdf file
    '''
    netcdf = NetCDF(output_filepath)
    netcdf.write_data(df)
    netcdf.assign_global_attributes_from_data_or_code(df)
    netcdf.assign_global_attributes_from_user(global_attributes)
    netcdf.close()
