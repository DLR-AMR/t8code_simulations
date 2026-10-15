#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "\n##################################################"
log_msg "######### Running case: Hello World ##############"
log_msg "##################################################\n"

# Export install directory
export CASE_INSTALL_DIR=$(pwd)/install

log_msg "\n##################################################"
log_msg "### Step 1: Build and install t8code"
log_msg "##################################################"
cd libs/t8code-build

log_msg "--------------------------------------------------"
log_msg "(1.a) Run cmake"
log_msg "--------------------------------------------------"
cmake ../t8code-src/ -GNinja -DCMAKE_INSTALL_PREFIX=$CASE_INSTALL_DIR

log_msg "--------------------------------------------------"
log_msg "(1.b) Run ninja"
log_msg "--------------------------------------------------"
ninja -j 32

log_msg "--------------------------------------------------"
log_msg "(1.c) Run ninja install"
log_msg "--------------------------------------------------"
ninja install

cd -

log_msg "\n##################################################"
log_msg "### Step 2: Build project hello_world"
log_msg "##################################################\n"

# Enter folder
mkdir -p build && cd build

log_msg "--------------------------------------------------"
log_msg "(1.a) Run cmake"
log_msg "--------------------------------------------------"
cmake .. -GNinja -DCMAKE_PREFIX_PATH=$CASE_INSTALL_DIR

log_msg "--------------------------------------------------"
log_msg "(1.b) Run ninja"
log_msg "--------------------------------------------------"
ninja -j 32

log_msg "\n##################################################"
log_msg "### Step 3: Run executable hello_world"
log_msg "##################################################\n"

# Run the case and pipe into log
mpirun -np 4 ./hello_world > log

log_msg "\n##################################################"
log_msg "### Step 4: (Pseudo-)Post-Processing"
log_msg "##################################################\n"

log_msg "The program produced the following output:"
echo -e "\033[35m$(cat log)\033[0m\n"

log_msg "\n##################################################"
log_msg "############# Leaving without errors #############"
log_msg "##################################################\n"

# Exit without error
exit 0
