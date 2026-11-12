#!/usr/bin/env bash

# Get root directory of git repository
REPO_ROOT="$(git rev-parse --show-toplevel)"
source $REPO_ROOT/scripts/helpers.sh

log_msg "\n##################################################"
log_msg "####### Running case: Christmas Card 2026 ##########"
log_msg "##################################################\n"

# Directory of a system HDF5 library built with the same MPI (see README.md)
: "${HDF5_LIBRARY_DIR:?Set HDF5_LIBRARY_DIR in system_hints.sh in the repository root}"

# Export install directory
export CASE_INSTALL_DIR=$(pwd)/install

# Do not pull in the deprecated OpenMPI C++ bindings via mpi.h. Otherwise, C++ code
# including mpi.h has to be linked against libmpi_cxx, which only the mpicxx wrapper does.
# The define has no effect without MPI or with other MPI implementations.
export CXXFLAGS="${CXXFLAGS:+$CXXFLAGS }-DOMPI_SKIP_MPICXX"

# Julia loads the shared t8code, libsc, and p4est libraries of the case. Their install rpath
# points to the case's install directory, but by default it is a RUNPATH, which is searched
# after LD_LIBRARY_PATH, so other installations of libsc or p4est in LD_LIBRARY_PATH would be
# loaded instead. An RPATH is searched before LD_LIBRARY_PATH.
export LDFLAGS="${LDFLAGS:+$LDFLAGS }-Wl,--disable-new-dtags"

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
# The mesh deformation to the .brep files needs OpenCASCADE and Eigen (downloaded by t8code).
cmake ../t8code-src/ -GNinja -DCMAKE_INSTALL_PREFIX=$CASE_INSTALL_DIR -DT8CODE_ENABLE_OCC=ON -DT8CODE_ENABLE_EIGEN=ON

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
# The MPI-enabled JLLs (HDF5_jll, t8code_jll) are still loaded and load the MPI JLL of the
# system MPI ABI (e.g. OpenMPI_jll), whose libraries can be of another version than the
# system MPI and then fail to load next to it. Hence, all its libraries are pointed to the
# system MPI library as well.
julia --project=. -e '
    using MPIPreferences, Preferences, Pkg
    using Base.Libc.Libdl: dlext, dlpath
    MPIPreferences.use_system_binary(; force = true)
    mpi_jll = load_preference(MPIPreferences, "abi") * "_jll"
    libmpi = dlpath(load_preference(MPIPreferences, "libmpi"))
    for (uuid, info) in Pkg.dependencies()
        info.name == mpi_jll || continue
        wrappers = joinpath(info.source, "src", "wrappers")
        products = unique(m[1] for file in readdir(wrappers; join = true)
                          for m in eachmatch(r"@declare_library_product\((\w+),", read(file, String)))
        set_preferences!((uuid, mpi_jll), (product * "_path" => libmpi for product in products)...;
                         force = true)
    end
    lib(dir, name) = joinpath(dir, name * "." * dlext)
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
log_msg "### Step 3: Run christmas card simulation"
log_msg "##################################################\n"

# The mesh has only a few thousand elements, so more MPI ranks or Julia threads do not pay off.
set -x
mpirun -np 4 julia --project=. christmas_card_simulation.jl
set +x

log_msg "\n##################################################"
log_msg "### Step 4: Convert the results to VTK"
log_msg "##################################################\n"

# Writes .vtu files next to the .h5 files in out/ for ParaView. Each solution file
# refers to the mesh file of its (deformed) mesh.
julia --project=. -e 'using Trixi2Vtk; trixi2vtk("out/solution_*.h5", output_directory = "out")'

log_msg "\n##################################################"
log_msg "############# Leaving without errors #############"
log_msg "##################################################\n"

# Exit without error
exit 0
