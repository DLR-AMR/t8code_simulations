#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "\n##################################################"
log_msg "######## Running case: png2mesh ############"
log_msg "##################################################\n"

# Export install directory
export CASE_INSTALL_DIR=$(pwd)/install

log_msg "\n##################################################"
log_msg "### Step 1: Build and install t8code v4.0.0"
log_msg "##################################################"
cd libs/t8code-build

log_msg "--------------------------------------------------"
log_msg "(1.a) Run cmake for t8code"
log_msg "--------------------------------------------------"
cmake ../t8code-src/ -GNinja -DCMAKE_INSTALL_PREFIX=$CASE_INSTALL_DIR

log_msg "--------------------------------------------------"
log_msg "(1.b) Run ninja for t8code"
log_msg "--------------------------------------------------"
ninja -j 32

log_msg "--------------------------------------------------"
log_msg "(1.c) Run ninja install for t8code"
log_msg "--------------------------------------------------"
ninja install

cd - 

log_msg "\n##################################################"
log_msg "### Step 2: Build png2mesh with t8code v4.0.0"
log_msg "##################################################\n"

# Enter png2mesh build folder
mkdir -p libs/png2mesh-build && cd libs/png2mesh-build

log_msg "--------------------------------------------------"
log_msg "(2.a) Run cmake for png2mesh"
log_msg "--------------------------------------------------"
cmake ../png2mesh-src -GNinja \
  -DCMAKE_PREFIX_PATH=$CASE_INSTALL_DIR \
  -DT8CODE_DIR=$CASE_INSTALL_DIR/lib/cmake/t8code \
  -DP4EST_DIR=$CASE_INSTALL_DIR/lib/cmake/p4est \
  -DSC_DIR=$CASE_INSTALL_DIR/lib/cmake/sc

log_msg "--------------------------------------------------"
log_msg "(2.b) Run ninja for png2mesh"
log_msg "--------------------------------------------------"
ninja -j 32

cd - 

log_msg "\n##################################################"
log_msg "### Step 3: Run png2mesh_demo"
log_msg "##################################################\n"

# Run the case and pipe into log
mkdir -p output
cd output
mpirun -np 4 ../libs/png2mesh-build/png2mesh_demo -f ../input/t8code_simulations.png -m9 > log

log_msg "\n##################################################"
log_msg "### Step 4: (Pseudo-)Post-Processing"
log_msg "##################################################\n"

log_msg "The program produced the following output:"
echo -e "\033[35m$(cat log)\033[0m\n"

log_msg ""
log_msg "On success, the program wrote *vtu file in the /output folder."

log_msg "\n##################################################"
log_msg "############# Leaving without errors #############"
log_msg "##################################################\n"

# Exit without error
exit 0
