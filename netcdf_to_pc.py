import xarray as xr
import numpy as np
import os
import time
import sys
import argparse
import yaml
from plyfile import PlyData, PlyElement
import laspy
import copy

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
    parser = argparse.ArgumentParser(description="Convert CF-NetCDF to PLY or LAS point clouds (Chunked).")
    
    parser.add_argument("input", help="Path to input NetCDF file")
    parser.add_argument("--format", choices=['ply', 'las', 'laz'], default='ply', help="Output format (default: ply)")
    parser.add_argument("--output", help="Path to output file. If omitted, defaults to input filename with new extension.")
    
    parser.add_argument("--config", default="config/to_pc_config.yaml", help="Path to YAML configuration file.")
    
    # CLI Override for chunk size
    parser.add_argument("--chunk-size", type=int, help="Override config chunk size (number of points per iteration)")
    
    return parser.parse_args()

def get_metadata_safely(ds, config):
    """
    Extracts CRS and Bounding Box without loading the entire dataset into RAM.
    Uses xarray's lazy loading capabilities.
    """
    crs_string = "unknown_crs"
    if 'datum' in ds.attrs:
        crs_string = ds.attrs['datum']
    elif 'crs' in ds and 'crs_wkt' in ds['crs'].attrs:
        crs_string = "See_WKT_in_NetCDF"

    print("Calculating Bounding Box (Lazy)...")
    
    # Map config names to netcdf names to find spatial extents
    nc_map = {v: k for k, v in config['mappings'].items()} # Reverse map for lookup
    
    bbox = [0.0] * 6
    # Check for X
    if 'x' in nc_map and nc_map['x'] in ds:
        bbox[0] = float(ds[nc_map['x']].min())
        bbox[1] = float(ds[nc_map['x']].max())
    # Check for Y
    if 'y' in nc_map and nc_map['y'] in ds:
        bbox[2] = float(ds[nc_map['y']].min())
        bbox[3] = float(ds[nc_map['y']].max())
    # Check for Z
    if 'z' in nc_map and nc_map['z'] in ds:
        bbox[4] = float(ds[nc_map['z']].min())
        bbox[5] = float(ds[nc_map['z']].max())
        
    return {
        'crs': crs_string,
        'source': "NetCDF",
        'processing_time': time.time(),
        'bbox': bbox
    }

def get_chunk(ds, config, start, end):
    """
    Reads a specific slice [start:end] of the NetCDF variables into memory.
    This is the only time significant RAM is consumed.
    """
    data = {}
    
    for nc_var, out_var in config['mappings'].items():
        if nc_var in ds:
            # Slice the data: this triggers the actual read from disk
            values = ds[nc_var][start:end].values
            
            # 1. Time Conversion (datetime64 -> float seconds)
            if out_var == 'epoch':
                if np.issubdtype(values.dtype, np.datetime64):
                    values = values.astype('datetime64[us]').astype('float64') / 1e6
            
            # 2. Coordinate Precision (Force doubles for coordinates)
            elif out_var in ['x', 'y', 'z']:
                values = values.astype('float64')

            data[out_var] = values
            
    return data

def process_and_write_las_chunked(ds, config, output_path, total_points, chunk_size):
    """
    Opens LAS file for writing, loops through NetCDF in chunks, 
    processes data, writes to disk, and clears RAM.
    """
    metadata = get_metadata_safely(ds, config)
    las_conf = config['las']
    
    # 1. Setup Base Header (Template)
    header = laspy.LasHeader(point_format=las_conf['point_format'], version=las_conf['version'])
    header.scales = np.array(las_conf['scales'])
    header.offsets = np.array([metadata['bbox'][0], metadata['bbox'][2], metadata['bbox'][4]])
    
    # LAS 1.4 Global Encoding for WKT/Time
    if las_conf['version'] == "1.4":
        header.global_encoding.gps_time_type = laspy.header.GpsTimeType.STANDARD

    # 2. Define Extra Bytes
    # We define attributes that are NOT standard LAS fields here
    standard_fields = ['x', 'y', 'z', 'intensity', 'red', 'green', 'blue', 'epoch', 'scan_angle']
    extra_bytes = []
    
    for nc_var, out_var in config['mappings'].items():
        if nc_var in ds and out_var not in standard_fields:
            dtype = ds[nc_var].dtype
            extra_bytes.append(laspy.ExtraBytesParams(name=out_var, type=dtype))

    if extra_bytes:
        header.add_extra_dims(extra_bytes)

    # 3. Create Writer Header
    # The writer needs the TOTAL point count to write a valid file header
    writer_header = copy.copy(header)
    writer_header.point_count = total_points

    print(f"Starting Chunked Write to {output_path} (Chunk Size: {chunk_size})...")
    
    # Open LAS file in write mode
    with laspy.open(output_path, mode="w", header=writer_header) as writer:
        
        # Loop through the dataset
        for start in range(0, total_points, chunk_size):
            end = min(start + chunk_size, total_points)
            print(f"  Processing points {start} to {end} ({(start/total_points)*100:.1f}%)...")
            
            # A. Extract Chunk from NetCDF
            data = get_chunk(ds, config, start, end)
            chunk_count = len(data['x'])
            
            # B. Prepare Temporary LasData container
            # Update header point_count to match THIS chunk, or LasData will allocate wrong memory size
            header.point_count = chunk_count
            chunk_las = laspy.LasData(header)
            
            # Assign Coordinates
            chunk_las.x = data['x']
            chunk_las.y = data['y']
            chunk_las.z = data['z']
            
            # Handle Colors (Upscaling 8-bit to 16-bit for LAS compliance)
            if 'red' in data:
                if data['red'].max() <= 255:
                    chunk_las.red = data['red'].astype('uint16') * 256
                    chunk_las.green = data['green'].astype('uint16') * 256
                    chunk_las.blue = data['blue'].astype('uint16') * 256
                else:
                    chunk_las.red = data['red'].astype('uint16')
                    chunk_las.green = data['green'].astype('uint16')
                    chunk_las.blue = data['blue'].astype('uint16')

            # Handle Time
            if 'epoch' in data:
                chunk_las.gps_time = data['epoch'].astype('float64')

            # Handle Intensity
            if 'intensity' in data:
                chunk_las.intensity = data['intensity'].astype('uint16')

            # Handle Scan Angle
            # LAS 1.4 (Format 6+) uses 0.006 degree resolution. 
            # We clip values to avoid integer overflow crashes.
            if 'scan_angle' in data:
                if header.point_format.id >= 6:
                    val = data['scan_angle'] / 0.006
                    val = np.clip(val, -32768, 32767) # Safety clip for 16-bit signed
                    chunk_las.scan_angle = val.astype('int16')
                else:
                    chunk_las.scan_angle_rank = data['scan_angle'].astype('int8')

            # Handle Extra Bytes
            for key in data.keys():
                if key not in standard_fields:
                    setattr(chunk_las, key, data[key])
            
            # C. Write Chunk to Disk
            # We must pass the raw .points object to support lazrs (Rust backend) acceleration
            writer.write_points(chunk_las.points)
            
            # D. Cleanup to free RAM
            del data
            del chunk_las
            
    print("LAS Chunked Write Complete.")

def write_ply_standard(ds, config, output_path, count):
    """Legacy full-load writer for PLY. Not optimized for large files."""
    print("Warning: PLY writing is not chunked. High RAM usage expected.")
    print("PLY support skipped in this memory-optimized version.")
    print("Please use --format las or laz.")

def main():
    args = parse_args()
    config = load_config(args.config)
    
    # Determine Output Path
    if args.output:
        out_path = args.output
    else:
        base = os.path.splitext(args.input)[0]
        ext = 'laz' if args.format == 'laz' else args.format
        out_path = f"{base}.{ext}"

    print(f"Opening {args.input}...")
    # chunks=None ensures we don't load data until requested (Lazy Loading)
    ds = xr.open_dataset(args.input, chunks=None)
    count = ds.sizes['point']
    print(f"Total points: {count}")

    # --- DETERMINE CHUNK SIZE ---
    # Priority: 1. CLI Argument, 2. Config File, 3. Hardcoded Default
    default_chunk = 5_000_000
    config_chunk = config.get('processing', {}).get('chunk_size', default_chunk)
    
    if args.chunk_size:
        final_chunk_size = args.chunk_size
        print(f"Using chunk size: {final_chunk_size} (CLI Override)")
    else:
        final_chunk_size = config_chunk
        print(f"Using chunk size: {final_chunk_size} (Config)")

    # Execute Writer
    if args.format in ['las', 'laz']:
        process_and_write_las_chunked(ds, config, out_path, count, final_chunk_size)
    else:
        write_ply_standard(ds, config, out_path, count)
    
    ds.close()

if __name__ == "__main__":
    main()