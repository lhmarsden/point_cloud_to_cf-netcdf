#!/usr/bin/env python3
import netCDF4 as nc
import pandas as pd
import os
import yaml
import argparse
from datetime import datetime

script_dir = os.path.dirname(os.path.realpath(__file__))

def get_config():
    config_path = os.path.join(script_dir, 'config', 'global_attributes.yml')

    with open(config_path, 'r') as file:
        cfg = yaml.safe_load(file)

    return cfg

def read_data(filepath):
    df = pd.read_csv(filepath, header=None, names=['longitude', 'latitude', 'altitude'])
    return df

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

    def assign_global_attributes_from_config(self,cfg):
        for attribute, value in cfg.items():
            print(attribute, value)
            if attribute not in self.ncfile.ncattrs() and value:
                self.ncfile.setncattr(attribute, value)

    def close(self):
        # Close the file
        self.ncfile.close()


def main(args):

    cfg = get_config()
    df = read_data(args.input)
    netcdf = NetCDF(args.output)
    netcdf.write_data(df)
    netcdf.assign_global_attributes_from_data_or_code(df)
    netcdf.assign_global_attributes_from_config(cfg)
    netcdf.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script to download SAFE files from Colhub Archive and convert them to NetCDF.")

    parser.add_argument("--input", type=str, required=True, help="Filepath to a csv file of your point cloud. .txt suffix is okay as long as your data contain 3 columns.")
    parser.add_argument("--output", type=str, required=True, help="Filepath to where to write your CF-NetCDF file.")

    args = parser.parse_args()
    main(args)
