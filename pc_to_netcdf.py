import os
from lib.read_data import read_hyspex, ply_to_df, las_to_df, get_cf_crs, list_variables_in_ply
from lib.create_netcdf import create_netcdf
from lib.global_attributes import GlobalAttributes
from lib.variable_mapping import VariableMapping
from lib.utils import define_chunk_size
import argparse
import yaml
import toml
import json
import sys
import logging

logger = logging.getLogger(__name__)

def is_valid_json(json_string):
    """Check if the string is a valid JSON."""
    try:
        json.loads(json_string)
        return True
    except json.JSONDecodeError:
        return False

def is_valid_yaml(file_path):
    """Check if the file is a valid YAML file."""
    if os.path.isfile(file_path) and (file_path.endswith('.yaml') or file_path.endswith('.yml')):
        try:
            with open(file_path, 'r') as f:
                yaml.safe_load(f)
            return True
        except yaml.YAMLError:
            return False
    return False

def is_valid_toml(file_path):
    """Check if the file is a valid TOML file."""
    if os.path.isfile(file_path) and file_path.endswith('.toml'):
        try:
            with open(file_path, 'r') as f:
                toml.load(f)
            return True
        except toml.TomlDecodeError:
            return False
    return False


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
    parser.add_argument(
        '-hyspex_cal',
        '--need_to_calibrate_hyspex',
        type=str,
        default='n',
        choices=['y', 'n'],
        help='Does the hyspex data need to be calibrated? Enter y or n.'
    )
    parser.add_argument('-ga', '--global_attributes', type=str, required=True, help='Should be either 1) a JSON string with key/value pairs for global attributes, 2) a yaml file including this information 3) A toml file including this information')
    parser.add_argument('-vm', '--variable_mapping', type=str, required=True, help='Should be filepath to a yaml file including this information')

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
    parser.add_argument('-proj4', '--proj4str', type=str, default=None, help='proj4str use to create the attributes for the CRS variable.')

    # Output filepath
    parser.add_argument('-o', '--output_filepath', type=str, default=None, help='Path to the output NetCDF file. If not provided, defaults to a subfolder "output" in the git repo with the same name as the input CSV file but with .nc extension.')

    args = parser.parse_args()

    if args.crs_config and args.proj4str:
        parser.error("You cannot specify both --crs_config and --proj4str. Please provide only one or neither if the proj4 string is in the comment in the header of the PLY file.")

    # Check conditions for X, Y, Z group
    if args.xcoord or args.ycoord or args.zcoord:
        # If any of X, Y, Z are present, all must be present
        if not (args.xcoord and args.ycoord and args.zcoord):
            parser.error('If any of X, Y, or Z is specified, all must be present.')
        # Check if any of the values are repeated (latitude, longitude, altitude must all be unique)
        xyz_coords = [args.xcoord, args.ycoord, args.zcoord]
        if len(set(xyz_coords)) != 3:
            parser.error('X, Y, and Z must each be unique (latitude, longitude, altitude cannot be repeated).')

    # Check if the global attributes argument is a valid JSON string, YAML file, or TOML file
    if is_valid_json(args.global_attributes):
        logger.info("Global attribute provided in JSON string.")
    elif is_valid_yaml(args.global_attributes):
        logger.info("Global attribute provided in YAML file.")
    elif is_valid_toml(args.global_attributes):
        logger.info("Global attribute provided in TOML file.")
    else:
        logger.error("Global attributes must be provided in a JSON string or TOML or YAML file.")

    # Load in the grid mapping config file if it exists and not None
    if args.crs_config:
        try:
            logger.info(f"Loading grid mapping from config file")
            if not os.path.exists(args.crs_config):
                logger.error(f"Error: The grid mapping configuration file '{args.crs_config}' could not be found.")
                logger.error("Check that the filepath is correct")
                sys.exit(1)
            with open(args.crs_config, "r") as file:
                cf_crs = yaml.safe_load(file)
            logger.info("CF grid mapping configuration file loaded successfully")
        except:
            crs_errors, crs_warnings = [f'Unable to load CRS from {args.crs_config}']
    elif args.proj4str:
        # Check if valid proj4 string and convert that
        logger.info("Trying to calculate a CF grid mapping from the PROJ.4 string")
        cf_crs, crs_errors, crs_warnings = get_cf_crs(proj4str=args.proj4str)
    elif args.ply_filepath:
        logger.info("Trying to calculate a CF grid mapping from the PROJ.4 string in the PLY header comment")
        cf_crs, crs_errors, crs_warnings = get_cf_crs(ply_filepath=args.ply_filepath)

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
    # elif args.las_filepath:
    #     logger.info("Checking what variables are in the LAS file")
    #     variable_names = list_variables_in_las()

    if args.hdr_filepath:
        variable_names = variable_names + ['intensity']

    vm_errors, vm_warnings = variable_mapping.check(variable_names)
    #vm_errors, vm_warnings = [], [] # Use this line to bypass checking of variables

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

    chunk_size, chunk_errors = define_chunk_size(pc_df,args.hdr_filepath)

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
    # TODO: Comment out line below when ready to check global attributes
    ga_errors, ga_warnings = [], [] # Use this line to bypass check of global attributes

    errors = data_errors + ga_errors + reformatting_errors + vm_errors + crs_errors + chunk_errors
    warnings = data_warnings + ga_warnings + reformatting_warnings + vm_warnings + crs_warnings

    if len(warnings) > 0:
        logger.warning('\nWarnings\nWe recommend that these are fixed, but you can choose to ignore them:\n')
        for warning in warnings:
            logger.warning(warning)
    if len(errors) > 0:
        logger.error('\n\nThe following errors were found:\n')
        for error in errors:
            logger.error(error)
        logger.error('No NetCDF file has been created. Please correct the errors and try again.\n\n')
    else:
        logger.info("Point cloud data and metadata read in a processed without error")
        if args.hdr_filepath:
            if args.need_to_calibrate_hyspex == 'y':
                calibrate = True
            else:
                calibrate = False
            logger.info("Trying to load the data from the hyspex file and write them to a pandas dataframe")
            wavelength_df = read_hyspex(args.hdr_filepath, need_to_calibrate=calibrate)
            logger.info(f"Data from {args.hdr_filepath} loaded in successfully")
        else:
            wavelength_df = None

        logger.info("Trying to create CF-NetCDF file")
        # Convert the DataFrame to a NetCDF file
        create_netcdf(pc_df, wavelength_df, variable_mapping.dict, args.output_filepath, global_attributes.dict, cf_crs, chunk_size)
        logger.info(f'File created: {args.output_filepath}')

if __name__ == '__main__':
    main()

