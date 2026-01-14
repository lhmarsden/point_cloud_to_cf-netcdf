{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    # System Tools
    pkgs.git

    # Python Environment
    pkgs.python3
    pkgs.python3Packages.pip
    pkgs.python3Packages.virtualenv

    # --- HARMONIZED DEPENDENCIES ---
    # These match requirements.txt
    pkgs.python3Packages.netcdf4
    pkgs.python3Packages.pyyaml
    pkgs.python3Packages.pandas
    pkgs.python3Packages.flask
    pkgs.python3Packages.plyfile
    pkgs.python3Packages.xarray
    pkgs.python3Packages.laspy
    pkgs.python3Packages.lazrs # The optional compression engine for laspy
    pkgs.python3Packages.numpy
    
    # Editor
    pkgs.vscodium
  ];

  shellHook = ''
    if [ ! -d ".venv" ]; then
      echo "Creating new virtual environment..."
      # --system-site-packages allows the venv to use all the pkgs above
      python -m venv .venv --system-site-packages
    fi
    source .venv/bin/activate
    
    # We DO NOT run 'pip install -r requirements.txt' automatically here.
    # Why? Because Nix has already provided better versions of them.
    # Running pip might try to overwrite the Nix versions with PyPI versions,
    # which can cause binary incompatibility errors on NixOS.
  '';
}