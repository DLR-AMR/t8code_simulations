#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "\n#################################################"
log_msg "#### Running case: Hello World File Download ####"
log_msg "#################################################\n"

FILE="t8data_helloworld.txt"

if [ -f $FILE ]
    echo $FILE
else
    echo "Error: Could not find file ${FILE}."
    exit 1
fi

# Exit without error
exit 0
