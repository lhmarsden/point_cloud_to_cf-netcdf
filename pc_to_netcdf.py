import os
from lib.read_data import read_hyspex, ply_to_df
from lib.create_netcdf import create_netcdf
from lib.global_attributes import Global_attributes_df
import argparse


def main():
    parser = argparse.ArgumentParser(description='Convert a point cloud file to a NetCDF file.')
    parser.add_argument('-hdr', '--hdr_filepath', type=str, help='Path to the input hdr file.')
    parser.add_argument('-ply', '--ply_filepath', type=str, help='Path to the input ply file.')
    parser.add_argument('-gm', '--grid_mapping_config', type=str, default=None, help='Path to the grid mapping configuration yaml file.')
    parser.add_argument('--output_filepath', type=str, default=None, help='Path to the output NetCDF file. If not provided, defaults to a subfolder "output" in the git repo with the same name as the input CSV file but with .nc extension.')
    parser.add_argument('--attributes_filepath', type=str, help='Path to the CSV file containing global attributes.', default='config/global_attributes_copy.csv')
    args = parser.parse_args()

    # TODO: Consider different setups for regular or irregular grid?
    # TODO: Consider different setup for georeferenced data (lat and lon instead of grid mapping)
    # If no grid mapping config provided, the ply needs to have lat and lon

    # Determine the output filepath
    if args.output_filepath is None:

        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Create the "output" subfolder within the script directory
        output_dir = os.path.join(script_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)

        # Generate the output filename based on the input CSV filename
        ply_filename = os.path.basename(args.ply_filepath)
        output_filename = os.path.splitext(ply_filename)[0] + '.nc'
        args.output_filepath = os.path.join(output_dir, output_filename)

    # TODO: if extension is PLY do this, if ascii or csv do that.
    # Read a CSV file into a pandas DataFrame

    # Read a PLY file into a pandas DataFrame
    #df, data_errors, data_warnings = data_to_df(args.input_filepath)
    # TODO: add errors to loading in data
    data_errors = data_warnings = []
    ply_df = ply_to_df(args.ply_filepath)
    wavelength_df = read_hyspex(args.hdr_filepath)

    # Read the global attributes from the specified CSV file
    global_attributes = Global_attributes_df(args.attributes_filepath)
    global_attributes.read_csv()
    ga_errors, ga_warnings = global_attributes.check()

    errors = data_errors + ga_errors
    warnings = data_warnings + ga_warnings

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
        create_netcdf(ply_df, wavelength_df, args.output_filepath, global_attributes, args.grid_mapping_config)
        print(f'File created: {args.output_filepath}')
    print('\n')

if __name__ == '__main__':
    main()

