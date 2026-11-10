#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "\n##################################################"
log_msg "#### Running case: GPU advection visualization ####"
log_msg "##################################################\n"

# Simulation parameters (run e8u3l2r5c01t1a10v50, see README.md).
NUM_PROCS=20
ADVECT_ARGS="-e 8 -u 3 -l 2 -r 5 -C 0.1 -T 1 -a 10 -v 50"

CASE_DIR=$(pwd)
# FetchContent lower-cases the dependency name in the folder names.
SRC_DIR=$CASE_DIR/libs/t8code_gpu_experiments-src
BUILD_DIR=$CASE_DIR/libs/t8code_gpu_experiments-build
SIM_DIR=$CASE_DIR/output/simulation
VIS_DIR=$CASE_DIR/output/visualization

log_msg "##################################################"
log_msg "### Step 0: Load modules"
log_msg "##################################################"

# prepare_on_teamserver.sh runs in its own process, so its modules are not loaded here.
# The module function is not exported to this script, so source it first.
# The module scripts use unset variables, so relax 'set -u' meanwhile.
set +u
if ! type module > /dev/null 2>&1; then
    source /etc/profile.d/modules.sh
fi
module purge
module load t8code/t8code-development-gcc13-mpich
set -u

log_msg "\n##################################################"
log_msg "### Step 1: Build t8code_GPU_experiments (CPU only)"
log_msg "##################################################"

log_msg "--------------------------------------------------"
log_msg "(1.a) Run cmake"
log_msg "--------------------------------------------------"
# OFFLOAD_ARCH=NONE: no GPU offloading, the element loop runs on the host with OpenMP.
# The project fetches its own t8code version (see cmake/thirdparty.json in the project).
cmake -S $SRC_DIR -B $BUILD_DIR -GNinja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=mpicc -DCMAKE_CXX_COMPILER=mpicxx -DOFFLOAD_ARCH=NONE

log_msg "--------------------------------------------------"
log_msg "(1.b) Run ninja"
log_msg "--------------------------------------------------"
ninja -C $BUILD_DIR -j 32 t8code_GPU_experiments_advect

log_msg "\n##################################################"
log_msg "### Step 2: Run the advection simulation"
log_msg "##################################################\n"

mkdir -p $SIM_DIR && cd $SIM_DIR
set -x
OMP_NUM_THREADS=1 mpirun -np $NUM_PROCS $BUILD_DIR/t8code_GPU_experiments_advect $ADVECT_ARGS > advect.log 2>&1
set +x
cd $CASE_DIR
log_msg "Wrote $(ls $SIM_DIR | grep -c -E '^advection_[0-9]+\.pvtu$') time steps to $SIM_DIR"

log_msg "\n##################################################"
log_msg "### Step 3: Visualization with ParaView"
log_msg "##################################################\n"

log_msg "--------------------------------------------------"
log_msg "(3.a) Render frames and encode video"
log_msg "--------------------------------------------------"
# 30 render processes, 6 time steps per second (60 steps -> 10 s video at 24 fps).
bash postprocessing/make_video.sh $SIM_DIR $VIS_DIR 30 6

log_msg "--------------------------------------------------"
log_msg "(3.b) Write ParaView state file"
log_msg "--------------------------------------------------"
env -u LD_LIBRARY_PATH -u PYTHONPATH /usr/bin/pvpython --force-offscreen-rendering \
    postprocessing/advect_scene.py state $SIM_DIR $VIS_DIR/advect_hybrid_cube.pvsm

log_msg "\n##################################################"
log_msg "### Step 4: Results"
log_msg "##################################################\n"

log_msg "Video:       $VIS_DIR/advect_hybrid_cube.mp4"
log_msg "Still image: $VIS_DIR/advect_hybrid_cube_still.png"
log_msg "State file:  $VIS_DIR/advect_hybrid_cube.pvsm"
du -sh $SIM_DIR $VIS_DIR

log_msg "\n##################################################"
log_msg "############# Leaving without errors #############"
log_msg "##################################################\n"

# Exit without error
exit 0
