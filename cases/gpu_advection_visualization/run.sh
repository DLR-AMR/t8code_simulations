#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "\n##################################################"
log_msg "#### Running case: GPU advection visualization ####"
log_msg "##################################################\n"

# Simulation parameters (run e8u3l4r4c01b15t1a10v100, see README.md).
# NUM_PROCS and NUM_JOBS can be set from outside, e.g. NUM_PROCS=4 bash run.sh.
NUM_PROCS=${NUM_PROCS:-10}
ADVECT_ARGS="-e 8 -u 3 -l 4 -r 4 -C 0.1 -b 1.5 -T 1 -a 10 -v 100"
# The video shows the first half of the run: output steps 0 ... 29 of 0 ... 58.
LAST_STEP=29
# Parallel build jobs and render processes.
NUM_JOBS=${NUM_JOBS:-$(nproc)}
NUM_RENDER=${NUM_RENDER:-30}
# pvpython of ParaView 5.11 (see README.md). Default: /usr/bin/pvpython if it exists, else pvpython from PATH.
if [ -z "${PVPYTHON:-}" ]; then
    if [ -x /usr/bin/pvpython ]; then PVPYTHON=/usr/bin/pvpython; else PVPYTHON=pvpython; fi
fi
export PVPYTHON

CASE_DIR=$(pwd)
# FetchContent lower-cases the dependency name in the folder names.
SRC_DIR=$CASE_DIR/libs/t8code_gpu_advect_experiments-src
BUILD_DIR=$CASE_DIR/libs/t8code_gpu_advect_experiments-build
SIM_DIR=$CASE_DIR/output/simulation
VIS_DIR=$CASE_DIR/output/visualization

log_msg "##################################################"
log_msg "### Step 0: Load modules (Teamserver only)"
log_msg "##################################################"

# prepare_on_teamserver.sh runs in its own process, so its modules are not loaded here.
# The module function is not exported to this script, so source it first.
# The module scripts use unset variables, so relax 'set -u' meanwhile.
# Without the module system (or without the module), the tools from PATH are used:
# cmake, ninja or make, mpicc/mpicxx, mpirun, ffmpeg (see README.md).
set +u
if ! type module > /dev/null 2>&1 && [ -f /etc/profile.d/modules.sh ]; then
    source /etc/profile.d/modules.sh
fi
if type module > /dev/null 2>&1 && module is-avail t8code/t8code-development-gcc13-mpich > /dev/null 2>&1; then
    module purge
    module load t8code/t8code-development-gcc13-mpich
    log_msg "Loaded module t8code/t8code-development-gcc13-mpich"
else
    log_msg "No Teamserver module, using the tools from PATH"
fi
set -u
for tool in cmake mpicc mpicxx mpirun ffmpeg; do
    command -v $tool > /dev/null || { log_msg "Missing tool: $tool"; exit 1; }
done
command -v $PVPYTHON > /dev/null || { log_msg "Missing pvpython ($PVPYTHON), set PVPYTHON"; exit 1; }
if command -v ninja > /dev/null; then GENERATOR=Ninja; else GENERATOR="Unix Makefiles"; fi

log_msg "\n##################################################"
log_msg "### Step 1: Build t8code_GPU_advect_experiments (CPU only)"
log_msg "##################################################"

log_msg "--------------------------------------------------"
log_msg "(1.a) Run cmake"
log_msg "--------------------------------------------------"
# OFFLOAD_ARCH=NONE: no GPU offloading, the element loop runs on the host with OpenMP.
# The project fetches its own t8code version (see cmake/thirdparty.json in the project).
cmake -S $SRC_DIR -B $BUILD_DIR -G "$GENERATOR" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=mpicc -DCMAKE_CXX_COMPILER=mpicxx -DOFFLOAD_ARCH=NONE

log_msg "--------------------------------------------------"
log_msg "(1.b) Build"
log_msg "--------------------------------------------------"
cmake --build $BUILD_DIR -j $NUM_JOBS --target t8code_GPU_experiments_advect

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
# Output steps 0 ... LAST_STEP (first half of the run), 6 steps per second (30 steps -> 5 s video at 24 fps),
# with the zoom into the refinement band (--inset) and the text overlays (--labels).
bash postprocessing/make_video.sh $SIM_DIR $VIS_DIR $NUM_RENDER 6 1 --inset --labels --last=$LAST_STEP

log_msg "--------------------------------------------------"
log_msg "(3.b) Write ParaView state file"
log_msg "--------------------------------------------------"
env -u LD_LIBRARY_PATH -u PYTHONPATH $PVPYTHON --force-offscreen-rendering \
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
