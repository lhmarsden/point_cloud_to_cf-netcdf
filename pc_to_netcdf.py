import os
from lib.read_data import read_hyspex, ply_to_df, las_to_df, get_cf_crs, list_variables_in_ply
from lib.create_netcdf import create_netcdf
from lib.global_attributes import GlobalAttributes
from lib.variable_mapping import VariableMapping
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

    # Input files
    # Create a mutually exclusive group
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-ply', '--ply_filepath', type=str, help='Path to the input ply file.')
    group.add_argument('-las', '--las_filepath', type=str, help='Path to the input las file.')
    parser.add_argument('-hdr', '--hdr_filepath', type=str, default=None, help='Path to the input hdr file.')
    parser.add_argument('-ga', '--global_attributes', type=str, required=True, help='Should be either 1) a JSON string with key/value pairs for global attributes, or 2) a yaml file including this information')
    parser.add_argument('-vm', '--variable_mapping', type=str, required=True, help='Should be filepath to a yaml file including this information')
    #TODO: The global attributes will be in a TOML file, so need to rewrite this.

    # X, Y and Z must all be specified if one is present
    # Allowed values for X, Y, Z
    allowed_xyz_values = ['latitude', 'longitude', 'altitude']
    parser.add_argument(
        '-x',
        '--xcoord',
        choices=allowed_xyz_values,
        type=str,
        help='Use this to state whether X corresponds to "longitude", "latitude" or "altitude"',
        required=False,
        default=None
        )
    parser.add_argument(
        '-y',
        '--ycoord',
        choices=allowed_xyz_values,
        type=str,
        help='Use this to state whether Y corresponds to "longitude", "latitude" or "altitude"',
        required=False,
        default=None
        )
    parser.add_argument(
        '-z',
        '--zcoord',
        choices=allowed_xyz_values,
        type=str,
        help='Use this to state whether Z corresponds to "longitude", "latitude" or "altitude"',
        required=False,
        default=None
        )
    # If X, Y and Z aren't specified, some information on the grid mapping is required
    # This could be in the crs_config file (argument below) or as a comment in the PLY file or lat/lon in file as well as X/Y
    parser.add_argument('-crs', '--crs_config', type=str, default=None, help='Path to the config yaml file contain the attributes to be written to the CRS variable.')

    # Output filepath
    parser.add_argument('-o', '--output_filepath', type=str, default=None, help='Path to the output NetCDF file. If not provided, defaults to a subfolder "output" in the git repo with the same name as the input CSV file but with .nc extension.')

    args = parser.parse_args()

    # Check conditions for X, Y, Z group
    if args.xcoord or args.ycoord or args.zcoord:
        # If any of X, Y, Z are present, all must be present
        if not (args.xcoord and args.ycoord and args.zcoord):
            parser.error('If any of X, Y, or Z is specified, all must be present.')
        # Check if any of the values are repeated (latitude, longitude, altitude must all be unique)
        xyz_coords = [args.xcoord, args.ycoord, args.zcoord]
        if len(set(xyz_coords)) != 3:
            parser.error('X, Y, and Z must each be unique (latitude, longitude, altitude cannot be repeated).')

    # Load in the grid mapping config file if it exists and not None
    if args.crs_config:
        logger.info(f"Loading grid mapping from config file")
        if not os.path.exists(args.crs_config):
            logger.error(f"Error: The grid mapping configuration file '{args.crs_config}' could not be found.")
            logger.error("Check that the filepath is correct")
            sys.exit(1)
        with open(args.crs_config, "r") as file:
            cf_crs = yaml.safe_load(file)
        logger.info("CF grid mapping configuration file loaded successfully")
    else:
        logger.info("Trying to calculate a CF grid mapping from the PROJ.4 string in the PLY header comment")
        cf_crs = get_cf_crs(args.ply_filepath)

    # TODO: If LAS file, CRS must be provided separately
    # TODO: Extra variables. Consider requiring a mapping file for all variables with variable attributes
    # TODO: HDR only if PLY? Not LAS?

    # Determine the output filepath if not provided as an argument
    if args.output_filepath is None:
        logger.info("Determining output file path for NetCDF file")
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Create the "output" subfolder within the script directory
        output_dir = os.path.join(script_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)

        # Generate the output filename based on the input filename
        if args.ply_filepath:
            input_filepath = args.ply_filepath
        elif args.las_filepath:
            input_filepath = args.las_filepath
        else:
            logger.error("Error: No input file provided")
            sys.exit(1)

        ply_filename = os.path.basename(input_filepath)
        output_filename = os.path.splitext(ply_filename)[0] + '.nc'
        args.output_filepath = os.path.join(output_dir, output_filename)
        logger.info(f"NetCDF file will be written to {args.output_filepath}")

    # Read in variable attributes from mapping file
    logger.info("Reading in variable attributes")
    variable_mapping = VariableMapping()
    variable_mapping.read_variable_mapping(args.variable_mapping)
    if args.ply_filepath:
        logger.info("Checking what variables are in the PLY file")
        variable_names = list_variables_in_ply(args.ply_filepath)
        # TODO: This might have to be done after reading in HYSPEX and PLY
        # But this will require reconfiguring of processing dataframe.
    # elif args.las_filepath:
    #     logger.info("Checking what variables are in the LAS file")
    #     variable_names = list_variables_in_las()
    vm_errors, vm_warnings = variable_mapping.check(variable_names)

    # Read the PLY file into a pandas DataFrame
    data_errors = []
    data_warnings = []

    # Projection is extracted from the grid mapping config file if it exists.
    # Otherwise it is extracted from the PLY file
    if args.ply_filepath:
        logger.info(f"Trying to load the data from {args.ply_filepath} and write them to a pandas dataframe")
        pc_df = ply_to_df(args.ply_filepath, cf_crs, variable_mapping.dict, args.xcoord, args.ycoord, args.zcoord)
        logger.info(f"Data from {args.ply_filepath} loaded in successfully")
    elif args.las_filepath:
        logger.info(f"Trying to load the data from {args.las_filepath} and write them to a pandas dataframe")
        pc_df = las_to_df(args.las_filepath, cf_crs, variable_mapping.dict, args.xcoord, args.ycoord, args.zcoord)
        logger.info(f"Data from {args.las_filepath} loaded in successfully")
    else:
        logger.error("Error: No input file provided")
        sys.exit(1)

    #if args.hdr_filepath:
    if not args.hdr_filepath: # TODO: For testing purposes, ignoring hyspex file, remove this
        logger.info("Trying to load the data from the hyspex file and write them to a pandas dataframe")
        wavelength_df = read_hyspex(args.hdr_filepath)
        logger.info(f"Data from {args.hdr_filepath} loaded in successfully")
    else:
        wavelength_df = None

    if cf_crs is None:
        # Ensure the DataFrame has latitude and longitude columns
        logger.info("The CF CRS attributes could not be computed. Checking if the input data contains latitude and longitude columns")
        required_columns = {'latitude', 'longitude'}
        if not required_columns.issubset(pc_df.columns):
            data_errors.append("CF CRS attributes are not provided and the input file is missing latitude and longitude columns.")
            logger.error("Latitude and longitude columns could not be found/read")

    # Read the global attributes from the specified CSV file
    logger.info("Reading in global attributes")
    global_attributes = GlobalAttributes()
    global_attributes.read_global_attributes(args.global_attributes)
    reformatting_errors, reformatting_warnings = global_attributes.reformat_attributes()
    global_attributes.derive(pc_df)
    ga_errors, ga_warnings = global_attributes.check()

    errors = data_errors + ga_errors + reformatting_errors + vm_errors
    warnings = data_warnings + ga_warnings + reformatting_warnings + vm_warnings

    if len(warnings) > 0:
        # TODO: Consider adding a prompt to continue for warnings
        logger.warning('\nWarnings\nWe recommend that these are fixed, but you can choose to ignore them:\n')
        for warning in warnings:
            logger.warning(warning)
    if len(errors) > 0:
        logger.error('\n\nThe following errors were found:\n')
        for error in errors:
            logger.error(error)
        logger.error('No NetCDF file has been created. Please correct the errors and try again.\n\n')
    else:
        logger.info("Global attributes read in a processed without error")
        logger.info("Trying to create CF-NetCDF file")
        # Convert the DataFrame to a NetCDF file
        create_netcdf(pc_df, wavelength_df, variable_mapping.dict, args.output_filepath, global_attributes.dict, cf_crs)
        logger.info(f'File created: {args.output_filepath}')

if __name__ == '__main__':
    main()

