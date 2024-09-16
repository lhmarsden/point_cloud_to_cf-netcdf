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
2. Create multiple CF-NetCDF file for multiple point clouds

### Create a CF-NetCDF file for 1 point cloud

### Create multiple CF-NetCDF file for multiple point clouds


1. Make a copy of `config/global_attributes.yml`. Edit your copied file to include the global attributes to be written to the
1.
1. Edit the global attributes in `config/global_attributes.yml`. Descriptions for each term can be found at https://adc.met.no/node/4.
1. Example of how to run the code

```
python3 pc_to_netcdf.py -hdr /path/to/your/input_data.hdr -ply /path/to/your/input_data.ply
```

The following arguments are required:
* **-hdr** filepath to the hdr file to read
* **-ply** filepath to the PLY file to read

The following arguments are optional:
* **-crs** filepath to a config file that contains the variable attributes to be written for the CRS variable. See `config/cf_crs.yml`for an example
* **-o** output filepath where the CF-NetCDF file will be written
* **-attr** filepath to a config file containing global attributes to be written to the file. If not provided, `config/global_attributes_copy.csv` will be used by default. Note that the geospatial limits, date_created and history attributes are written automatically.