import xarray as xr
import numpy as np
import os
import time
import sys
import argparse
import yaml
from plyfile import PlyData, PlyElement
import laspy

# --- 1. SETUP & CONFIG LOAD ---
def load_config(config_path):
    """Loads variables and settings from a YAML file."""
    if not os.path.exists(config_path):
        print(f"Error: Config file {config_path} not found.")
        sys.exit(1)
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if config is None:
        print(f"Error: Config file '{config_path}' appears to be empty.")
        sys.exit(1)
        
    return config

def parse_args():
    """Handles command line arguments."""
    parser = argparse.ArgumentParser(description="Convert CF-NetCDF to PLY or LAS point clouds.")
    
    parser.add_argument("input", help="Path to input NetCDF file or OPeNDAP URL")
    parser.add_argument("--format", choices=['ply', 'las', 'laz'], default='ply', help="Output format (default: ply)")
    parser.add_argument("--output", help="Path to output file. If omitted, defaults to input filename with new extension.")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML configuration file.")
    
    return parser.parse_args()

# --- 2. DATA EXTRACTION ---
def extract_data_from_nc(nc_path, config):
    """
    Opens NetCDF and extracts variables based on config mappings.
    Returns a dictionary of numpy arrays and a metadata dictionary.
    """
    print(f"Opening {nc_path}...")
    try:
        ds = xr.open_dataset(nc_path, chunks=None) 
    except Exception as e:
        print(f"Failed to open NetCDF: {e}")
        sys.exit(1)

    count = ds.sizes['point']
    print(f"Detected {count} points.")
    
    data = {}
    
    # Iterate through mappings
    for nc_var, out_var in config['mappings'].items():
        if nc_var in ds:
            print(f"  -> Mapping {nc_var} to {out_var}")
            values = ds[nc_var].values
            
            # --- FIX: DATA INTEGRITY ---
            
            # 1. Time: Convert datetime64 to float seconds (Unix Epoch)
            if out_var == 'epoch':
                if np.issubdtype(values.dtype, np.datetime64):
                    values = values.astype('datetime64[us]').astype('float64') / 1e6
            
            # 2. Coordinates: Ensure Double Precision
            elif out_var in ['x', 'y', 'z']:
                values = values.astype('float64')

            data[out_var] = values

    # Gather Metadata for Headers
    crs_string = "unknown_crs"
    if 'datum' in ds.attrs:
        crs_string = ds.attrs['datum']
    elif 'crs' in ds and 'crs_wkt' in ds['crs'].attrs:
        crs_string = "See_WKT_in_NetCDF"

    # Calculate bbox safely
    bbox = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    if 'x' in data and 'y' in data and 'z' in data:
        bbox = [
            float(data['x'].min()), float(data['x'].max()),
            float(data['y'].min()), float(data['y'].max()),
            float(data['z'].min()), float(data['z'].max())
        ]

    metadata = {
        'crs': crs_string,
        'source': os.path.basename(nc_path),
        'processing_time': time.time(),
        'bbox': bbox
    }
    
    # Clean up Xarray object
    ds.close()
    
    return data, metadata, count

# --- 3. WRITERS ---
def write_ply(data, metadata, output_path, count):
    """Writes data to a Binary PLY file."""
    print(f"Writing PLY to {output_path}...")
    
    dtype_list = []
    
    # Priority order for visualization
    priority_order = ['x', 'y', 'z', 'nx', 'ny', 'nz', 'red', 'green', 'blue']
    sorted_keys = sorted(data.keys(), key=lambda k: priority_order.index(k) if k in priority_order else 99)

    # Determine dtypes
    for key in sorted_keys:
        if key in ['red', 'green', 'blue']:
            dtype_list.append((key, 'uint8'))
        else:
            dtype_list.append((key, data[key].dtype))

    # Create structured array
    ply_struct = np.zeros(count, dtype=dtype_list)
    
    for key in sorted_keys:
        val = data[key]
        
        # Scale colors down for PLY (16-bit -> 8-bit)
        if key in ['red', 'green', 'blue']:
            if val.max() > 255:
                ply_struct[key] = (val / 65535.0 * 255).astype('uint8')
            else:
                ply_struct[key] = val.astype('uint8')
        else:
            ply_struct[key] = val
        
        del data[key]

    comment_str = (
        f"processing_time_epoch={metadata['processing_time']:.6f}; "
        f"crs_info={metadata['crs']}; "
        f"source_file={metadata['source']}; "
    )

    el = PlyElement.describe(ply_struct, 'vertex')
    PlyData([el], text=False, comments=[comment_str]).write(output_path)
    
    print("PLY Write Complete.")

def write_las(data, metadata, output_path, config, count):
    """Writes data to LAS/LAZ using config settings."""
    print(f"Writing LAS/LAZ to {output_path}...")
    
    las_conf = config['las']
    
    # Setup Header
    header = laspy.LasHeader(point_format=las_conf['point_format'], version=las_conf['version'])
    
    header.scales = np.array(las_conf['scales'])
    header.offsets = np.array([metadata['bbox'][0], metadata['bbox'][2], metadata['bbox'][4]])

    if las_conf['version'] == "1.4":
        header.global_encoding.gps_time_type = laspy.header.GpsTimeType.STANDARD

    # Register Extra Bytes
    # Note: 'scan_angle' is standard, so we exclude it from extra bytes
    standard_fields = ['x', 'y', 'z', 'intensity', 'red', 'green', 'blue', 'epoch', 'scan_angle']
    
    extra_bytes = []
    for key, arr in data.items():
        if key not in standard_fields:
            extra_bytes.append(laspy.ExtraBytesParams(name=key, type=arr.dtype))
    
    if extra_bytes:
        header.add_extra_dims(extra_bytes)

    # Create Data Object
    las = laspy.LasData(header)
    
    las.x = data['x']
    las.y = data['y']
    las.z = data['z']
    
    del data['x'], data['y'], data['z']
    
    # Scale colors up for LAS (8-bit -> 16-bit if needed)
    if 'red' in data:
        if data['red'].max() <= 255:
            print("  -> Upscaling 8-bit color to 16-bit for LAS...")
            las.red = data['red'].astype('uint16') * 256
            las.green = data['green'].astype('uint16') * 256
            las.blue = data['blue'].astype('uint16') * 256
        else:
            las.red = data['red'].astype('uint16')
            las.green = data['green'].astype('uint16')
            las.blue = data['blue'].astype('uint16')
        
        del data['red'], data['green'], data['blue']

    if 'epoch' in data:
        las.gps_time = data['epoch'].astype('float64')
        del data['epoch']

    if 'intensity' in data:
        las.intensity = data['intensity'].astype('uint16')
        del data['intensity']

    # --- FIX: Handle Scan Angle for LAS 1.4 (Format 6+) vs Legacy ---
    if 'scan_angle' in data:
        # Formats 6+ (like Format 7) use a high-precision 'scan_angle'
        if header.point_format.id >= 6:
            # New Format: 16-bit, step size 0.006 degrees
            # We must divide input degrees by 0.006 to get the integer storage value
            # e.g. 90 degrees / 0.006 = 15,000
            las.scan_angle = (data['scan_angle'] / 0.006).astype('int16')
        else:
            # Old Format (0-5): 8-bit 'rank', integer degrees
            las.scan_angle_rank = data['scan_angle'].astype('int8')
            
        del data['scan_angle']

    # Assign Extra Bytes
    for key in list(data.keys()):
        setattr(las, key, data[key])
        del data[key]

    las.write(output_path)
    print("LAS/LAZ Write Complete.")

# --- 4. MAIN EXECUTION ---
def main():
    args = parse_args()
    config = load_config(args.config)
    
    if args.output:
        out_path = args.output
    else:
        base = os.path.splitext(args.input)[0]
        ext = 'laz' if args.format == 'laz' else args.format
        out_path = f"{base}.{ext}"

    data, metadata, count = extract_data_from_nc(args.input, config)
    
    if args.format == 'ply':
        write_ply(data, metadata, out_path, count)
    elif args.format in ['las', 'laz']:
        write_las(data, metadata, out_path, config, count)

if __name__ == "__main__":
    main()