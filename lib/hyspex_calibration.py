import os
import struct
import sys

import numpy as np


class HyspexRad:
    """
    Radiance calibration of Hyspex VNIR-1800 bil files.
    """

    def __init__(self, hyspex_path, dtype=np.float32):
        self.img_bil, self.hdr, self.bin_hdr = import_hyspex(hyspex_path)

        # prepare calibration variables
        self.Ns = int(self.hdr["samples"])
        self.Nl = int(self.hdr["lines"])
        self.Nb = int(self.hdr["bands"])

        self.dtype = dtype

        self._prepare_parameters()

    def calibrate_spectrum(self, line_index, sample_index):
        """
        Calibrate a set (given by indeces) of spectra.

        line_index and sample_index are iterables of indeces, such that
        len(line_index) == len(sample_index).

        E.g. if you want to calibrate the spectrum of the first two samples
        of line 0 and the first sample of line 3, you would use

        line_index = [0, 0, 3]
        sample_index = [0, 1, 0]
        """
        assert len(line_index) == len(sample_index)

        CN = self.img_bil[line_index, :, sample_index].T - self.BG[:, sample_index]
        CN /= self.RE[:, sample_index]
        CN /= self.denominator[:, sample_index]
        return CN.T

    def _prepare_parameters(self):
        # Extract data needed for the calibration
        # 1 if the data has been real time calibrated
        self.CALIBAVAILIBLE = bool(self.bin_hdr["CalibAvailible"])
        self.BG = self.bin_hdr["BGnp"].astype(self.dtype)  # Background
        self.RE = self.bin_hdr["REnp"].astype(self.dtype)  # Response matrix

        # Quantum efficiency of center pixel
        QE = np.array(self.bin_hdr["QE"])
        WL = np.array(self.bin_hdr["spectralCalib"])  # Wavelenght in nm
        BW = np.diff(WL)  # Bandwidth in nm

        # Make sure bandwidth vector is correct
        BW = np.r_[BW, [BW[-1]]]

        # Scaling factor expressing DN per photoelectron
        SF = self.bin_hdr["SF"]

        aperture_size = self.bin_hdr["aperture_size"]  # Aperture size

        # Field of view (radians) on one pixel
        pixelsizex = self.bin_hdr["pixelsize_x"]
        pixelsizey = self.bin_hdr["pixelsize_y"]

        # Integration time in seconds
        integrationtime_s = np.float32(self.bin_hdr["integration_time"] / 1e6)

        pixelarea = pixelsizex * pixelsizey
        aperture_area = np.pi * aperture_size * aperture_size

        # prepare calibration variables
        h = 6.62607004e-34  # Planck constant [W]
        c = 2.99792458e17  # Speed of light [nm/s]

        scalingfactor = (pixelarea * integrationtime_s * aperture_area * SF) / (h * c)

        self.denominator = QE * BW * WL * scalingfactor
        self.denominator = np.tile(self.denominator, [self.Ns, 1]).T.astype(self.dtype)


# -----------------------------------------------------------------------------
# Necessary utility functions
# -----------------------------------------------------------------------------
def import_hyspex(hyspex_file, mode="r", reshape2bip=False):
    """
    Import hyspex file
    """

    ss = os.path.splitext(hyspex_file)
    hyspex_hdr_file = ss[0] + ".hdr"

    # Get hdr
    hdr = read_envi_header(hyspex_hdr_file)
    dtype = np.dtype(envi_to_dtype[hdr["data type"]])
    offset = int(hdr["header offset"])
    Nl, Ns, Nb = (
        int(hdr["lines"]),
        int(hdr["samples"]),
        int(hdr["bands"]),
    )  # Cols, Rows, bands

    # Calculate estimated number of lines
    est_Nl = int((os.path.getsize(hyspex_file) - offset) / (Ns * Nb * dtype.itemsize))
    if est_Nl != Nl:
        print(
            "Number of lines doest not match file size: est_Nl = %d (Nl = %d)"
            % (est_Nl, Nl)
        )
        print("%s\n" % hyspex_file)
        Nl = est_Nl

    # parse the binary header
    bin_hdr = {}
    if offset > 0:
        with open(hyspex_file, "rb") as fd:
            data = fd.read(offset)
        bin_hdr = parse_hyspex_bin_header(data)
    # Get spectral data
    if hdr["interleave"].lower() == "bil":
        try:
            hyim = np.memmap(
                hyspex_file, dtype=dtype, mode=mode, offset=offset, shape=(Nl, Nb, Ns)
            )
        except Exception:
            import pdb

            pdb.set_trace()
        if reshape2bip:
            hyim = np.transpose(hyim, [0, 2, 1])

    elif hdr["interleave"].lower() == "bip":
        hyim = np.memmap(
            hyspex_file, dtype=dtype, mode=mode, offset=offset, shape=(Nl, Ns, Nb)
        )

    elif hdr["interleave"].lower() == "bsq":
        hyim = np.memmap(
            hyspex_file, dtype=dtype, mode=mode, offset=offset, shape=(Nb, Nl, Ns)
        )
        if reshape2bip:
            hyim = np.transpose(hyim, [1, 2, 0])
    else:
        raise IOError("Uknown interleave: %s" % hdr["interleave"])

    return hyim, hdr, bin_hdr


# Envi data types
dtype_map = [
    ("1", np.uint8),  # unsigned byte
    ("2", np.int16),  # 16-bit int
    ("3", np.int32),  # 32-bit int
    ("4", np.float32),  # 32-bit float
    ("5", np.float64),  # 64-bit float
    ("6", np.complex64),  # 2x32-bit complex
    ("9", np.complex128),  # 2x64-bit complex
    ("12", np.uint16),  # 16-bit unsigned int
    ("13", np.uint32),  # 32-bit unsigned int
    ("14", np.int64),  # 64-bit int
    ("15", np.uint64),
]  # 64-bit unsigned int
envi_to_dtype = dict((k, np.dtype(v).char) for (k, v) in dtype_map)


class EnviException(Exception):
    """Base class for ENVI file-related exceptions."""

    pass


class FileNotAnEnviHeader(EnviException, IOError):
    """Raised when "ENVI" does not appear on the first line of the file."""

    def __init__(self, msg):
        super(FileNotAnEnviHeader, self).__init__(msg)


class EnviHeaderParsingError(EnviException, IOError):
    """Raised upon failure to parse parameter/value pairs from a file."""

    def __init__(self):
        msg = "Failed to parse ENVI header file."
        super(EnviHeaderParsingError, self).__init__(msg)


def read_envi_header(file, support_nonlowercase_params=True):
    """
    USAGE: hdr = read_envi_header(file)
    Reads an ENVI ".hdr" file header and returns the parameters in a
    dictionary as strings.  Header field names are treated as case
    insensitive and all keys in the dictionary are lowercase.
    """
    f = open(file, "r")
    try:
        starts_with_ENVI = f.readline().strip().startswith("ENVI")
    except UnicodeDecodeError:
        msg = (
            "File does not appear to be an ENVI header (appears to be a "
            "binary file)."
        )
        f.close()
        raise FileNotAnEnviHeader(msg)
    else:
        if not starts_with_ENVI:
            msg = 'File does not appear to be an ENVI header (missing "ENVI" \
              at beginning of first line).'
            f.close()
            raise FileNotAnEnviHeader(msg)
    lines = f.readlines()
    f.close()
    dict = {}
    try:
        while lines:
            line = lines.pop(0)
            if line.find("=") == -1:
                continue
            if line[0] == ";":
                continue

            (key, sep, val) = line.partition("=")
            key = key.strip()
            if not key.islower():
                if not support_nonlowercase_params:
                    key = key.lower()
            val = val.strip()
            if val and val[0] == "{":
                str = val.strip()
                while str[-1] != "}":
                    line = lines.pop(0)
                    if line[0] == ";":
                        continue

                    str += "\n" + line.strip()
                if key == "description":
                    dict[key] = str.strip("{}").strip()
                else:
                    vals = str[1:-1].split(",")
                    for j in range(len(vals)):
                        vals[j] = vals[j].strip()
                    dict[key] = vals
            else:
                dict[key] = val

        # Get the description and merge with dict
        if "description" in dict:
            desc_dict = {
                i.split("=")[0].strip(): (i.split("=")[1].strip())
                for i in dict["description"].split("\n")
            }
            dict.update(desc_dict)
        return dict
    except Exception:
        raise EnviHeaderParsingError()


def parse_bytearray(arr, fmt, bptr, special=None):
    """
    Parse a byte package.
    Support striping '\x00' from strings.
    """
    size = struct.Struct(fmt).size
    res = struct.unpack(fmt, arr[bptr : bptr + size])
    if len(res) == 1:
        res = res[0]
    bptr += size  # Increment the byte ptr
    if special:
        res = res.decode("latin1").rstrip("\x00")
    return res, bptr


def parse_hyspex_bin_header(data):
    """
    Parse the hyspex binary header.
    """
    bptr = 0
    hyspex_word, bptr = parse_bytearray(data, "<8s", bptr, special="strip_string")
    if hyspex_word != "HYSPEX":
        raise IOError("Uknown binary file format")
        sys.exit(0)
    bin_hdr = {}
    bin_hdr["size"], bptr = parse_bytearray(data, "<i", bptr)
    bin_hdr["serial_number"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["configfile"], bptr = parse_bytearray(
        data, "<200s", bptr, special="strip_string"
    )
    bin_hdr["settingfile"], bptr = parse_bytearray(
        data, "<120s", bptr, special="strip_string"
    )
    bin_hdr["scaling_factor"], bptr = parse_bytearray(data, "<d", bptr)
    bin_hdr["electronics"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["comsettings_electronics"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["comport_electronics"], bptr = parse_bytearray(
        data, "<56s", bptr, special="strip_string"
    )
    bin_hdr["fanspeed"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["backtemperature"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["comport"], bptr = parse_bytearray(
        data, "<64s", bptr, special="strip_string"
    )
    bin_hdr["detectstring"], bptr = parse_bytearray(
        data, "<200s", bptr, special="strip_string"
    )
    bin_hdr["sensor"], bptr = parse_bytearray(
        data, "<200s", bptr, special="strip_string"
    )
    bin_hdr["framegrabber"], bptr = parse_bytearray(
        data, "<200s", bptr, special="strip_string"
    )
    bin_hdr["ID"], bptr = parse_bytearray(data, "<200s", bptr, special="strip_string")
    bin_hdr["supplier"], bptr = parse_bytearray(
        data, "<200s", bptr, special="strip_string"
    )
    bin_hdr["left_gain"], bptr = parse_bytearray(
        data, "<32s", bptr, special="strip_string"
    )
    bin_hdr["right_gain"], bptr = parse_bytearray(
        data, "<32s", bptr, special="strip_string"
    )
    bin_hdr["comment"], bptr = parse_bytearray(
        data, "<200s", bptr, special="strip_string"
    )
    bin_hdr["backgroundfile"], bptr = parse_bytearray(
        data, "<200s", bptr, special="strip_string"
    )
    bin_hdr["RecordHD"], bptr = parse_bytearray(
        data, "<c", bptr, special="strip_string"
    )
    bin_hdr["UknownPtr1"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["serverindex"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["comsettings"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["number_of_background"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["spectral_size"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["spatial_size"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["binning"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["detected"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["integration_time"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["frame_period"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["default_R"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["default_G"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["default_B"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["bitshift"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["temperature_offset"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["shutter"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["background_present"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["power"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["current"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["bias"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["bandwidth"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["vin"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["vref"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["sensor_vin"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["sensor_vref"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["cooling_temperature"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["window_start"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["window_stop"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["readout_time"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["p"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["i"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["d"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["numberofframes"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["nobp"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["dw"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["EQ"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["lens"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["FOVexp"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["ScanningMode"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["CalibAvailible"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["NumberOfAvg"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["SF"], bptr = parse_bytearray(data, "<d", bptr)
    bin_hdr["aperture_size"], bptr = parse_bytearray(data, "<d", bptr)
    bin_hdr["pixelsize_x"], bptr = parse_bytearray(data, "<d", bptr)
    bin_hdr["pixelsize_y"], bptr = parse_bytearray(data, "<d", bptr)
    bin_hdr["temperature"], bptr = parse_bytearray(data, "<d", bptr)
    bin_hdr["max_framerate"], bptr = parse_bytearray(data, "<d", bptr)
    bin_hdr["spectralCalibPOINTER"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["REPOINTER"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["QEPOINTER"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["backgroundPOINTER"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["badPixelsPOINTER"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["imageFormat"], bptr = parse_bytearray(data, "<I", bptr)
    bin_hdr["spectralCalib"], bptr = parse_bytearray(
        data, "<%dd" % bin_hdr["spectral_size"], bptr
    )
    bin_hdr["QE"], bptr = parse_bytearray(data, "<%dd" % bin_hdr["spectral_size"], bptr)
    bin_hdr["RE"], bptr = parse_bytearray(
        data, "<%dd" % (bin_hdr["spectral_size"] * bin_hdr["spatial_size"]), bptr
    )
    bin_hdr["backgroundBefore"], bptr = parse_bytearray(
        data, "<%dd" % (bin_hdr["spectral_size"] * bin_hdr["spatial_size"]), bptr
    )
    bin_hdr["badPixels"], bptr = parse_bytearray(data, "<%dI" % bin_hdr["nobp"], bptr)
    bin_hdr["wlnp"] = np.array(bin_hdr["spectralCalib"]).reshape(
        bin_hdr["spectral_size"]
    )
    bin_hdr["QEnp"] = np.array(bin_hdr["QE"]).reshape(bin_hdr["spectral_size"])
    bin_hdr["REnp"] = np.array(bin_hdr["RE"]).reshape(
        bin_hdr["spectral_size"], bin_hdr["spatial_size"]
    )
    bin_hdr["BGnp"] = np.array(bin_hdr["backgroundBefore"]).reshape(
        bin_hdr["spectral_size"], bin_hdr["spatial_size"]
    )
    return bin_hdr


# ----------------------------------------------------------------------------
# Usage
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    # Calibrate three pixels:
    # Sample (0, 0), (0, 1) and (3, 0)
    line_index = [0, 0, 3]
    sample_index = [0, 1, 0]

    hyspex_file = "/home/lukem/Documents/SIOS/Data/point_clouds_agnar/hyspex_test_luke/Hyspex/2024-08-19-16-06-04-GMT/2024-08-19-16-06-04-GMT_02_VNIR_1800_SN00845_FOVx2_raw.hyspex"

    hrad = HyspexRad(hyspex_file)
    calibrated = hrad.calibrate_spectrum(line_index, sample_index)

    # Shape: (3, 186)
    print(calibrated.shape)
    print(calibrated)