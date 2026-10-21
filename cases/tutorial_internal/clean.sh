#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "--------------------------------------------------"
log_msg "- Clean Up: Removing  build, install, libs, t8code"
log_msg "--------------------------------------------------"

# Get script path to reduce risk of unintentional deletion
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd $SCRIPT_DIR

set -x

# Remove build, install, and libs folder
rm -rf build
rm -rf install
rm -rf libs
rm -rf t8code
rm airfoil_windtunnel_hexahedra.brep
rm airfoil_windtunnel_hexahedra.msh

set +x

log_msg "Leaving script."

