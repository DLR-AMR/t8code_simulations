#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "--------------------------------------------------"
log_msg "-       Clean Up: Removing downloaded data        "
log_msg "--------------------------------------------------"

# Get script path to reduce risk of unintentional deletion
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd $SCRIPT_DIR

set -x

# Remove data folder
rm -rf data

set +x

log_msg "Leaving script."

