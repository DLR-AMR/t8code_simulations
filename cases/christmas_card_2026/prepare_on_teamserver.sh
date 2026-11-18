#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "--------------------------------------------------"
log_msg "---------- Preparing Teamserver settings ---------"
log_msg "--------------------------------------------------"

# All dependencies come from the conda environment of environment.txt, which has to be active
# (see README.md). Loaded modules would shadow its compilers, MPI, and Python in PATH.
echo "Purge loaded modules"
module purge

echo "Done preparing Teamserver"
