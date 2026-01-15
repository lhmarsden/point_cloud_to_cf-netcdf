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

- `-ga` / `--global_attributes` (str, required)
  - **Description:** Specifies global attributes for the NetCDF file. Can be provided either as:
    1. A JSON string containing key/value pairs for global attributes.
    2. A path to a YAML file that includes the global attributes.
  - **Example:** `--global_attributes '{"key1": "value1", "key2": "value2"}'` or `--global_attributes /path/to/global_attributes.yaml`
  > Note: the geospatial limits, date_created, history, featureType and Conventions attributes are computed within the script and written automatically to the CF-NetCDF file. Including these attributes with overwrite the values computed within the script.

### Optional Arguments:

- `-hdr` / `--hdr_filepath` (str, optional)
  - **Description:** Path to the input HDR file, which contains hyperspectral data. If omitted, the hyperspectral data won't be included.
  - **Default:** `None`
  - **Example:** `--hdr_filepath /path/to/your/file.hdr`

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



## Convert CF-NetCDF back to Point Cloud

Script: `netcdf_to_pc.py`

This script allows you to convert a CF-NetCDF file back into standard point cloud formats (PLY, LAS, or LAZ). It is designed to handle very large datasets efficiently by processing data in "chunks" to minimize RAM usage.

### Example usage:

**Basic conversion to PLY:**
```bash
python3 netcdf_to_pc.py /path/to/input.nc
```

**Convert to compressed LAZ with memory optimization:**
```bash
python3 netcdf_to_pc.py /path/to/input.nc --format laz --chunk-size 1000000
```

### Arguments:

- `input` (str, required)
  - **Description:** Path to the input NetCDF file.

- `--format` (str, optional)
  - **Description:** The output file format.
  - **Choices:** `ply`, `las`, `laz`
  - **Default:** `ply`

- `--output` (str, optional)
  - **Description:** Path to the output file. If omitted, the script saves the file in the same directory as the input with the new extension.
  - **Example:** `--output /tmp/my_cloud.laz`

- `--config` (str, optional)
  - **Description:** Path to the YAML configuration file defining variable mappings and LAS settings.
  - **Default:** `config/to_pc_config.yaml`

- `--chunk-size` (int, optional)
  - **Description:** Overrides the number of points processed per iteration. Lower this value if you are running out of RAM on large files.
  - **Default:** Pulled from config file (usually `5000000`).

### Configuration

The script relies on `config/to_pc_config.yaml` to map NetCDF variables (e.g., `gps_time`) back to specific Point Cloud dimensions (e.g., `epoch`). It also handles format-specific settings, such as LAS version and scale factors.

**Example Config:**
```yaml
las:
  version: "1.4"
  point_format: 7
  scales: [0.001, 0.001, 0.001] # mm precision

mappings:
  # NetCDF Variable : Output Dimension
  X: x
  Y: y
  Z: z
  red: red
  gps_time: epoch
```