import os
from lib.read_data import read_hyspex, ply_to_df, get_cf_grid_mapping
from lib.create_netcdf import create_netcdf
from lib.global_attributes import Global_attributes_df
import argparse
import yaml
import sys
import logging
logger = logging.getLogger(__name__)

def main():

    # Log to console
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    log_info = logging.StreamHandler(sys.stdout)
    log_info.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(log_info)

    logger.info("Parsing arguments")
    parser = argparse.ArgumentParser(description='Convert a point cloud file to a NetCDF file.')
    parser.add_argument('-hdr', '--hdr_filepath', type=str, help='Path to the input hdr file.')
    parser.add_argument('-ply', '--ply_filepath', type=str, help='Path to the input ply file.')
    parser.add_argument('-grd', '--grid_mapping_config', type=str, default=None, help='Path to the grid mapping configuration yaml file.')
    parser.add_argument('--output_filepath', type=str, default=None, help='Path to the output NetCDF file. If not provided, defaults to a subfolder "output" in the git repo with the same name as the input CSV file but with .nc extension.')
    parser.add_argument('--attributes_filepath', type=str, help='Path to the CSV file containing global attributes.', default='config/global_attributes_copy.csv')
    args = parser.parse_args()

    # Determine the output filepath
    if args.output_filepath is None:
        logger.info("Determining output file path for NetCDF file")
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Create the "output" subfolder within the script directory
        output_dir = os.path.join(script_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)

        # Generate the output filename based on the input CSV filename
        ply_filename = os.path.basename(args.ply_filepath)
        output_filename = os.path.splitext(ply_filename)[0] + '.nc'
        args.output_filepath = os.path.join(output_dir, output_filename)
        logger.info(f"NetCDF file will be written to {args.output_filepath}")

    # Load in the grid mapping config file if it exists and not None
    if args.grid_mapping_config:
        logger.info(f"Loading grid mapping from config file")
        if not os.path.exists(args.grid_mapping_config):
            logger.error(f"Error: The grid mapping configuration file '{args.grid_mapping_config}' does not exist.")
            sys.exit(1)
        with open(args.grid_mapping_config, "r") as file:
            cf_grid_mapping = yaml.safe_load(file)
        logger.info("CF grid mapping configuration file loaded successfully")
    else:
        logger.info("Trying to calculate a CF grid mapping from the PROJ.4 string in the PLY header comment")
        cf_grid_mapping = get_cf_grid_mapping(args.ply_filepath)

    # Read the PLY file into a pandas DataFrame
    data_errors = []
    data_warnings = []

    # Projection is extracted from the grid mapping config file if it exists.
    # Otherwise it is extracted from the PLY file
    logger.info("Trying to load the data from the PLY file and write them to a pandas dataframe")
    ply_df = ply_to_df(args.ply_filepath, cf_grid_mapping)
    logger.info("Trying to load the data from the hyspex file and write them to a pandas dataframe")
    wavelength_df = read_hyspex(args.hdr_filepath)

    if cf_grid_mapping is None:
        # Ensure the PLY DataFrame has latitude and longitude columns
        logger.info("The CF grid mapping could not be computed. Checking if the PLY file contains a latitude and longitude columns")
        required_columns = {'latitude', 'longitude'}
        if not required_columns.issubset(ply_df.columns):
            data_errors.append("CF grid mapping is not provided and the PLY file is missing latitude and longitude columns.")
            logger.error("Latitude and longitude columns could not be found/read")
            #TODO: Currently can't read latitude and longitude columns from PLY file without plyfile library

    # Read the global attributes from the specified CSV file
    logger.info("Reading in global attributes from a separate configuration file")
    global_attributes = Global_attributes_df(args.attributes_filepath)
    global_attributes.read_csv()
    ga_errors, ga_warnings = global_attributes.check()

    errors = data_errors + ga_errors
    warnings = data_warnings + ga_warnings

    if len(warnings) > 0:
        logger.warning('\nWarnings\nWe recommend that these are fixed, but you can choose to ignore them:\n')
        for warning in warnings:
            logger.warning(warning)
    if len(errors) > 0:
        logger.error('\nThe following errors were found:\n')
        for error in errors:
            logger.error(error)
        logger.error('\nNo NetCDF file has been created. Please correct the errors and try again.')
    else:
        # Convert the DataFrame to a NetCDF file
        create_netcdf(ply_df, wavelength_df, args.output_filepath, global_attributes, cf_grid_mapping)
        logger.info(f'File created: {args.output_filepath}')

if __name__ == '__main__':
    main()

