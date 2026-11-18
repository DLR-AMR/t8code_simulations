#!/usr/bin/env bash

# Hints where to find the pre-installed software on this system, for all cases.
#
# This file is sourced by scripts/helpers.sh, i.e., by every case script. Fill in a hint
# only if the software is not found on its own, e.g., because it is not installed in a
# default location or loaded as a module (on the AMR Teamserver, all hints stay empty).
# Fill in the value after ':-', e.g.,
#   export OpenCASCADE_ROOT="${OpenCASCADE_ROOT:-$HOME/install/opencascade-7.7.0}"
# A hint that is already set in the environment takes precedence over the value here.

# Installation prefixes of OpenCASCADE and VTK, searched by CMake's find_package()
export OpenCASCADE_ROOT="${OpenCASCADE_ROOT:-}"
export VTK_ROOT="${VTK_ROOT:-}"

# Directory containing the HDF5 libraries (libhdf5, libhdf5_hl) built with the MPI used by
# the cases, e.g., /usr/lib/x86_64-linux-gnu/hdf5/openmpi for the Ubuntu package
# libhdf5-openmpi-dev
export HDF5_LIBRARY_DIR="${HDF5_LIBRARY_DIR:-}"
