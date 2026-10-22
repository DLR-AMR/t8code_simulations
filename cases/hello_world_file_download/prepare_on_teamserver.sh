#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "--------------------------------------------------"
log_msg "---------- Preparing Teamserver settings ---------"
log_msg "--------------------------------------------------"

# Nothing to do

echo "Done preparing Teamserver"