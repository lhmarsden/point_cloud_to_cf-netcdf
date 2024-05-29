import os
from lib.read_data import data_to_df
from lib.create_netcdf import df_to_netcdf
from lib.global_attributes import Global_attributes_df
import numpy as np
from datetime import datetime, timezone
import json
import argparse
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description='Convert a point cloud file to a NetCDF file.')
    parser.add_argument('input_filepath', type=str, help='Path to the input file.')
    parser.add_argument('--output_filepath', type=str, default=None, help='Path to the output NetCDF file. If not provided, defaults to a subfolder "output" in the git repo with the same name as the input CSV file but with .nc extension.')
    parser.add_argument('--attributes_filepath', type=str, help='Path to the CSV file containing global attributes.', default='config/global_attributes_copy.csv')
    args = parser.parse_args()

    # Determine the output filepath
    if args.output_filepath is None:

        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Create the "output" subfolder within the script directory
        output_dir = os.path.join(script_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)

        # Generate the output filename based on the input CSV filename
        input_filename = os.path.basename(args.input_filepath)
        output_filename = os.path.splitext(input_filename)[0] + '.nc'
        args.output_filepath = os.path.join(output_dir, output_filename)

    # TODO: if extension is PLY do this, if ascii or csv do that.
    # Read a CSV file into a pandas DataFrame

    # Read a PLY file into a pandas DataFrame
    df = data_to_df(args.input_filepath)

    # Read the global attributes from the specified CSV file
    global_attributes = Global_attributes_df(args.attributes_filepath)
    global_attributes.read_csv()
    errors, warnings = global_attributes.check()

    if len(warnings) > 0:
        print('\nWarnings\nWe recommend that these are fixed, but you can choose to ignore them:\n')
        for warning in warnings:
            print(warning)
    if len(errors) > 0:
        print('\nThe following errors were found:\n')
        for error in errors:
            print(error)
        print('\nNo NetCDF file has been created. Please correct the errors and try again.')
    else:
        # Convert the DataFrame to a NetCDF file
        df_to_netcdf(df, args.output_filepath, global_attributes)
        print(f'File created: {args.output_filepath}')
    print('\n')

if __name__ == '__main__':
    main()

