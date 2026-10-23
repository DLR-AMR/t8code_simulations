#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "\n##################################################"
log_msg "####### Running case: Christmas Card 2026 ##########"
log_msg "##################################################\n"

# Directory of a system HDF5 library built with the same MPI (see README.md)
: "${HDF5_LIBRARY_DIR:?Set HDF5_LIBRARY_DIR to the directory containing libhdf5 built with your MPI}"

# Export install directory
export CASE_INSTALL_DIR=$(pwd)/install

# Do not pull in the deprecated OpenMPI C++ bindings via mpi.h. Otherwise, C++ code
# including mpi.h has to be linked against libmpi_cxx, which only the mpicxx wrapper does.
# The define has no effect without MPI or with other MPI implementations.
export CXXFLAGS="${CXXFLAGS:+$CXXFLAGS }-DOMPI_SKIP_MPICXX"

# Keep all Julia packages, artifacts, and compile caches inside the case folder. The
# trailing colon appends Julia's bundled depots (stdlibs), but not the user depot ~/.julia.
export JULIA_DEPOT_PATH="$(pwd)/julia_depot:"
# Precompile only once, after the preferences for the local t8code have been set.
export JULIA_PKG_PRECOMPILE_AUTO=0

log_msg "\n##################################################"
log_msg "### Step 1: Build and install t8code"
log_msg "##################################################"
cd libs/t8code-build

log_msg "--------------------------------------------------"
log_msg "(1.a) Run cmake"
log_msg "--------------------------------------------------"
# T8code.jl loads t8code, libsc, and p4est at runtime, so they have to be built as shared
# libraries (the default). The preferences set in step 2 point Julia to them by their
# absolute paths. T8code.jl does not support custom t8code builds without MPI (MPI is on by default).
cmake ../t8code-src/ -GNinja -DCMAKE_INSTALL_PREFIX=$CASE_INSTALL_DIR

log_msg "--------------------------------------------------"
log_msg "(1.b) Run ninja"
log_msg "--------------------------------------------------"
ninja -j $(nproc)

log_msg "--------------------------------------------------"
log_msg "(1.c) Run ninja install"
log_msg "--------------------------------------------------"
ninja install

cd -

log_msg "\n##################################################"
log_msg "### Step 2: Set up Julia environment"
log_msg "##################################################"

log_msg "--------------------------------------------------"
log_msg "(2.a) Install Julia packages"
log_msg "--------------------------------------------------"
# Trixi.jl and T8code.jl are taken from libs/ (see [sources] in Project.toml).
julia --project=. -e 'using Pkg; Pkg.instantiate()'

log_msg "--------------------------------------------------"
log_msg "(2.b) Use system MPI, system HDF5, and the local t8code"
log_msg "--------------------------------------------------"
# Writes LocalPreferences.toml. MPI.jl has to use the MPI t8code was built with, P4est.jl
# has to use the libsc and p4est built along with t8code, and HDF5.jl has to use an HDF5
# built with that MPI as well (the MPI-enabled HDF5_jll does not work with system MPI).
julia --project=. -e '
    using MPIPreferences, Preferences
    MPIPreferences.use_system_binary(; force = true)
    lib(dir, name) = joinpath(dir, name * "." * Base.Libc.Libdl.dlext)
    t8lib(name) = lib(joinpath(ENV["CASE_INSTALL_DIR"], "lib"), name)
    h5lib(name) = lib(ENV["HDF5_LIBRARY_DIR"], name)
    set_preferences!(Base.identify_package("T8code").uuid,
                     "libt8" => t8lib("libt8"), "libp4est" => t8lib("libp4est"), "libsc" => t8lib("libsc"); force = true)
    set_preferences!(Base.identify_package("P4est").uuid,
                     "libp4est" => t8lib("libp4est"), "libsc" => t8lib("libsc"); force = true)
    set_preferences!(Base.identify_package("HDF5").uuid,
                     "libhdf5" => h5lib("libhdf5"), "libhdf5_hl" => h5lib("libhdf5_hl"); force = true)'

log_msg "--------------------------------------------------"
log_msg "(2.c) Precompile packages"
log_msg "--------------------------------------------------"
julia --project=. -e 'using Pkg; Pkg.precompile()'

log_msg "\n##################################################"
log_msg "### Step 3: Run Trixi.jl elixir"
log_msg "##################################################\n"

log_msg "--------------------------------------------------"
log_msg " Elixir: t8code_2d_dgsem/elixir_advection_basic.jl"
log_msg "--------------------------------------------------"

set -x
mpirun -np 2 julia --project=. libs/trixi_jl-src/examples/t8code_2d_dgsem/elixir_advection_basic.jl
set +x

log_msg "\n##################################################"
log_msg "############# Leaving without errors #############"
log_msg "##################################################\n"

# Exit without error
exit 0
