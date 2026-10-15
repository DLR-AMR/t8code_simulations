#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "--------------------------------------------------"
log_msg "---------- Preparing Teamserver settings ---------"
log_msg "--------------------------------------------------"

# Purge currently loaded modules.
echo "Purge loaded modules"
module purge

# Load required modules.
echo "Load required modules"
module load t8code/t8code-development-gcc13-mpich-with-vtk-9.1-and-occ-7.6.0

echo "Done preparing Teamserver"