# Notes

## Variables

Data - RGB, Theta angle, Phi angle, range of point, amplitude, reflectance, deviations, timestamp

All with X Y Z

## File size

ASCII files smaller

LAS files larger. Includes all the variables.

## Resolutions people might want to publish

Varies depending on data. Can be 1 mm.

50 cm is coarse, 10 cm is good.

Resolution varies depending on distance from instrument.

Option to downscale? Maybe a bonus feature for afterwards.

## Possible data formats for point clouds

LAS -
ASCII
COPC

Less used
Bently Pointtools
Polygon file format (small objects)
Autocad

Could also be DEM but this is basically an ASCII file, right?

All include coordinates

Can include some software dependent information.

## CF-NetCDF - lat, lon, elevation or X, Y, Z with reference coordinate?

Different file structure depending on resolution?

2 options.
Lat, lon, elevation
X, Y, Z distance from instrument. (scanner coordinate system?)
Project coordinate system (e.g. scan object from different positions), global coordinate system, scanner coordinate system.


Get data out in either irrespective of data structure.

Options:
https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#_two_dimensional_latitude_longitude_coordinate_variables


