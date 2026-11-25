#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "--------------------------------------------------"
log_msg "---------- Preparing Teamserver settings ---------"
log_msg "--------------------------------------------------"

# Without the module system (outside the Teamserver) there is nothing to prepare.
# run.sh then uses the tools from PATH (see README.md).
set +u
if ! type module > /dev/null 2>&1 && [ -f /etc/profile.d/modules.sh ]; then
    source /etc/profile.d/modules.sh
fi
if ! type module > /dev/null 2>&1; then
    echo "No module system found, nothing to prepare"
    exit 0
fi

# Purge currently loaded modules.
echo "Purge loaded modules"
module purge

# Load required modules.
echo "Load required modules"
module load t8code/t8code-development-gcc13-mpich
set -u

echo "Done preparing Teamserver"
