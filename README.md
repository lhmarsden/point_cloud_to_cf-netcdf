# Point cloud to CF-NetCDF

Python program to convert point cloud data from a txt or csv file to a CF-NetCDF file.

## Setup

Install the required libraries

```
pip install -r requirements.txt
```

## Running the program

The program can be run in 2 ways:
1. Create a CF-NetCDF file for 1 point cloud
2. Create multiple CF-NetCDF file for multiple point clouds listed in a CSV file

## Create a CF-NetCDF file for 1 point cloud

### Example usage:
```
python3 pc_to_netcdf.py -hdr /path/to/file.hdr -ply /path/to/file.ply
```

### Required Arguments:
- `-ply` / `--ply_filepath` (str, required)
  - **Description:** Path to the input PLY file.
  - **Example:** `--ply_filepath /path/to/your/file.ply`

### Optional Arguments:

- `-hdr` / `--hdr_filepath` (str, optional)
  - **Description:** Path to the input HDR file, which contains hyperspectral data. If omitted, the hyperspectral data won't be included.
  - **Default:** `None`
  - **Example:** `--hdr_filepath /path/to/your/file.hdr`

- `-ga` / `--global_attributes` (str, optional)
  - **Description:** Specifies global attributes for the NetCDF file. Can be provided either as:
    1. A JSON string containing key/value pairs for global attributes.
    2. A path to a YAML file that includes the global attributes.
  - **Example:** `--global_attributes '{"key1": "value1", "key2": "value2"}'` or `--global_attributes /path/to/global_attributes.yaml`Note that the geospatial limits, date_created and history attributes are written automatically.
  > Note: the geospatial limits, date_created and history attributes are computed within the script and written automatically to the CF-NetCDF file.

### Coordinate Arguments:

> **Warning:** Use these arguments only when the `X`, `Y`, and `Z` values in the PLY file represent `latitude`, `longitude`, and `altitude`, and you need to explicitly define which axis corresponds to each.

When specifying any of the following coordinate options (`X`, `Y`, `Z`), **all three must be provided**, and their values must be unique.

- `-x` / `--xcoord` (str, optional)
  - **Description:** Specifies what the `X` coordinate represents. Must be one of `latitude`, `longitude`, or `altitude`.
  - **Default:** `None`
  - **Example:** `--xcoord longitude`

- `-y` / `--ycoord` (str, optional)
  - **Description:** Specifies what the `Y` coordinate represents. Must be one of `latitude`, `longitude`, or `altitude`.
  - **Default:** `None`
  - **Example:** `--ycoord latitude`

- `-z` / `--zcoord` (str, optional)
  - **Description:** Specifies what the `Z` coordinate represents. Must be one of `latitude`, `longitude`, or `altitude`.
  - **Default:** `None`
  - **Example:** `--zcoord altitude`

> **Note:** If any of `X`, `Y`, or `Z` is provided, all three must be specified, and their values must be unique (i.e., each of them must correspond to a different dimension: latitude, longitude, or altitude). If these coordinates are not provided, the script attempts to derive this information from the PLY file or from a Coordinate Reference System (CRS) configuration file.

### CRS Argument:

- `-crs` / `--crs_config` (str, optional)
  - **Description:** Path to a YAML configuration file containing attributes for a CRS (Coordinate Reference System) variable to be written to the NetCDF file. This is not required if `latitude` and `longitude` are provided in the PLY file. If not provided, the script attempts to derive the CRS from the comment line in the header of the PLY file.
  - **Default:** `None`
  - **Example:** `--crs_config /path/to/crs_config.yaml`

### Output Argument:

- `-o` / `--output_filepath` (str, optional)
  - **Description:** Path to the output NetCDF file. If not specified, the output file is automatically saved to an `output` folder in the current directory, with the same name as the input PLY file but with a `.nc` extension.
  - **Default:** `None`
  - **Example:** `--output_filepath /path/to/output_file.nc`

## Create multiple CF-NetCDF file for multiple point clouds

Use this option to parse multiple PLY files in a single execution. The `convert_multiple_files.py` script processes each row of a CSV file and runs the `pc_to_netcdf.py` script for each row. The CSV file should contain columns corresponding to the required and optional arguments for the `pc_to_netcdf.py` script. The CSV should also include one column for every global attribute to be written for each file. An example of the CSV can be found here:
`config/config_bulk_conversion.csv`

### Example usage:

```
python3 convert_multiple_files.py /path/to/file.csv
```

### Required Argument:

- `csv_filepath` (str, required)
  - **Description:** Path to the input CSV file. Each row in this CSV represents a unique set of arguments passed to the `pc_to_netcdf.py` script.
  - **Example:** `input.csv`

