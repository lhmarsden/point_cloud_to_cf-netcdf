# Point cloud to CF-NetCDF

Python program to convert point cloud data from a txt or csv file to a CF-NetCDF file.

## Setup

Install the required libraries

```
pip install -r requirements.txt
```

## Preparing your data

Your data can be in a CSV file or a txt file with 3 columns, longitude, latitude, and altitude. It should not have column headers. For an example, see `tests/data/example_data.csv`.

## Testing example

Check your program works by running the `test_execute.sh` program that works with included dummy data.

## Running the program

1. Edit the global attributes in `config/global_attributes.yml`. Descriptions for each term can be found at https://adc.met.no/node/4.
2. Run the code `python3 main --input /path/to/your/input_data.txt --output /path/to/write/netcdf_file.nc`
