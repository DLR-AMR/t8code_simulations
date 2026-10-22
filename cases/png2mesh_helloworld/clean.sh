#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "--------------------------------------------------"
log_msg "---------- Cleaning png2mesh case ---------"
log_msg "--------------------------------------------------"

# Remove build directories
rm -rf libs/
rm -rf install
rm -rf output/
rm -rf input/

# Remove local build directory
rm -rf build

# Remove log file
rm -f log

log_msg "Cleaning complete"
