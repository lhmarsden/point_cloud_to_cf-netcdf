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
    
    # Safety check for empty config files
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
        ds = xr.open_dataset(nc_path, chunks=None) # Load into memory
    except Exception as e:
        print(f"Failed to open NetCDF: {e}")
        sys.exit(1)

    count = ds.sizes['point']
    print(f"Detected {count} points.")
    
    data = {}
    
    # Iterate through mappings in config to see what exists in this file
    for nc_var, out_var in config['mappings'].items():
        if nc_var in ds:
            print(f"  -> Mapping {nc_var} to {out_var}")
            values = ds[nc_var].values
            
            # --- SPECIAL HANDLING ---
            
            # 1. Colors: Handle 16-bit to 8-bit scaling if needed
            if out_var in ['red', 'green', 'blue']:
                if values.max() > 255:
                    values = (values / 256).astype('uint8')
                else:
                    values = values.astype('uint8')

            # 2. Time: Convert datetime64 to float seconds
            elif out_var == 'epoch':
                if np.issubdtype(values.dtype, np.datetime64):
                    values = values.astype('datetime64[us]').astype('float64') / 1e6
                values = values.astype('float32') # Standardize time to float

            # 3. Coordinates: Force Double Precision (f8)
            elif out_var in ['x', 'y', 'z']:
                values = values.astype('float64')

            # Default: Cast everything else to float32 or uint32 as appropriate
            elif np.issubdtype(values.dtype, np.floating):
                values = values.astype('float32')
            elif np.issubdtype(values.dtype, np.integer):
                values = values.astype('uint32')
                
            data[out_var] = values

    # Gather Metadata for Headers
    crs_string = "unknown_crs"
    if 'datum' in ds.attrs:
        crs_string = ds.attrs['datum']
    elif 'crs' in ds and 'crs_wkt' in ds['crs'].attrs:
        crs_string = "See_WKT_in_NetCDF"

    metadata = {
        'crs': crs_string,
        'source': os.path.basename(nc_path), # Use basename for cleaner headers
        'processing_time': time.time(),
        'bbox': [
            float(data['x'].min()), float(data['x'].max()),
            float(data['y'].min()), float(data['y'].max())
        ]
    }
    
    return data, metadata, count

# --- 3. WRITERS ---
def write_ply(data, metadata, output_path, count):
    """Writes data to a Binary PLY file using standard plyfile library."""
    print(f"Writing PLY to {output_path}...")
    
    # 1. Construct dtype list for numpy structure
    dtype_list = []
    
    # Order matters slightly for readability in 3D viewers, specifically x,y,z first
    priority_order = ['x', 'y', 'z', 'nx', 'ny', 'nz', 'red', 'green', 'blue']
    sorted_keys = sorted(data.keys(), key=lambda k: priority_order.index(k) if k in priority_order else 99)

    for key in sorted_keys:
        # We assume the data types in 'data' dictionary are already correct (handled in extract step)
        dtype_list.append((key, data[key].dtype))

    # 2. Create structured array (Required by PlyElement.describe)
    ply_struct = np.zeros(count, dtype=dtype_list)
    for key in sorted_keys:
        ply_struct[key] = data[key]

    # 3. Construct Comment
    comment_str = (
        f"processing_time_epoch={metadata['processing_time']:.6f}; "
        f"crs_info={metadata['crs']}; "
        f"source_file={metadata['source']}; "
        f"BBox = [{metadata['bbox'][0]:.4f}, {metadata['bbox'][1]:.4f}, ...]"
    )

    # 4. Write using standard PlyData (No manual binary writing)
    # text=False ensures binary format (standard for large clouds)
    el = PlyElement.describe(ply_struct, 'vertex')
    PlyData([el], text=False, comments=[comment_str]).write(output_path)
    
    print("PLY Write Complete.")

def write_las(data, metadata, output_path, config, count):
    """Writes data to LAS/LAZ using config settings."""
    print(f"Writing LAS/LAZ to {output_path}...")
    
    # Setup Header
    las_conf = config['las']
    header = laspy.LasHeader(point_format=las_conf['point_format'], version=las_conf['version'])
    header.scales = np.array(las_conf['scales'])
    header.offsets = np.array([metadata['bbox'][0], metadata['bbox'][2], 0]) # Min x, Min y, 0

    # Register Extra Bytes (Anything that isn't standard LAS)
    # Standard LAS 1.4 fields: x, y, z, intensity, return_number, ... red, green, blue, gps_time
    standard_fields = ['x', 'y', 'z', 'intensity', 'red', 'green', 'blue', 'epoch']
    
    extra_bytes = []
    for key, arr in data.items():
        if key not in standard_fields:
            extra_bytes.append(laspy.ExtraBytesParams(name=key, type=arr.dtype))
    
    if extra_bytes:
        header.add_extra_dims(extra_bytes)

    # Create Data Object
    las = laspy.LasData(header)
    
    # Assign Data
    las.x = data['x']
    las.y = data['y']
    las.z = data['z']
    
    if 'red' in data:
        # LAS expects 16-bit color. Check if we extracted 8-bit.
        if data['red'].max() <= 255:
            las.red = data['red'].astype('uint16') * 256
            las.green = data['green'].astype('uint16') * 256
            las.blue = data['blue'].astype('uint16') * 256
        else:
            las.red = data['red']
            las.green = data['green']
            las.blue = data['blue']

    if 'epoch' in data:
        las.gps_time = data['epoch'].astype('float64')

    if 'intensity' in data:
        las.intensity = data['intensity']

    # Assign Extra Bytes
    for key in data.keys():
        if key not in standard_fields:
            setattr(las, key, data[key])

    # Write
    las.write(output_path)
    print("LAS/LAZ Write Complete.")

# --- 4. MAIN EXECUTION ---
def main():
    args = parse_args()
    config = load_config(args.config)
    
    # Determine Output Path
    if args.output:
        out_path = args.output
    else:
        # Default: input.nc -> input.ply
        base = os.path.splitext(args.input)[0]
        ext = 'laz' if args.format == 'laz' else args.format
        out_path = f"{base}.{ext}"

    # Execution Flow
    data, metadata, count = extract_data_from_nc(args.input, config)
    
    if args.format == 'ply':
        write_ply(data, metadata, out_path, count)
    elif args.format in ['las', 'laz']:
        write_las(data, metadata, out_path, config, count)

if __name__ == "__main__":
    main()