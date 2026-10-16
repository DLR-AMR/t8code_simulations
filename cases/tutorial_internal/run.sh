#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "\n##################################################"
log_msg "####### Running case: Internal tutorials ###########"
log_msg "##################################################\n"

# Export install directory
export CASE_INSTALL_DIR=$(pwd)/install

# Do not pull in the deprecated OpenMPI C++ bindings via mpi.h. Otherwise, C++ code
# including mpi.h has to be linked against libmpi_cxx, which only the mpicxx wrapper does.
# The define has no effect without MPI or with other MPI implementations.
export CXXFLAGS="${CXXFLAGS:+$CXXFLAGS }-DOMPI_SKIP_MPICXX"

log_msg "##################################################"
log_msg "### Step 0: Move t8code out of libs subfolder"
log_msg "##################################################"

# For a cleaner sparation of dependencies and project to build
if [ -d "libs/t8code-src" ] && [ ! -d "t8code" ]; then
    mv libs/t8code-src t8code
    rm -rf libs/t8code-build libs/t8code-subbuild
fi

log_msg "\n##################################################"
log_msg "### Step 1: Build and install t8code"
log_msg "##################################################"

# (create and) enter build folder
mkdir -p build && cd build

log_msg "--------------------------------------------------"
log_msg "(1.a) Run cmake"
log_msg "--------------------------------------------------"
cmake ../t8code/ -GNinja -DCMAKE_INSTALL_PREFIX=$CASE_INSTALL_DIR -DT8CODE_ENABLE_OCC=ON -DT8CODE_ENABLE_VTK=ON

log_msg "--------------------------------------------------"
log_msg "(1.b) Run ninja"
log_msg "--------------------------------------------------"
ninja -j 32

log_msg "--------------------------------------------------"
log_msg "(1.c) Run ninja install"
log_msg "--------------------------------------------------"
ninja install

log_msg "\n##################################################"
log_msg "### Step 2: Run t8code tutorials"
log_msg "##################################################\n"

cd tutorials/features/

log_msg "--------------------------------------------------"
log_msg " Tutorial: Curved Meshes"
log_msg "--------------------------------------------------"

set -x
mpirun -np 4 ./t8_features_curved_meshes --fileprefix ../../../airfoil_windtunnel_hexahedra --geometry
set +x

log_msg "\n##################################################"
log_msg "############# Leaving without errors #############"
log_msg "##################################################\n"

# Exit without error
exit 0
