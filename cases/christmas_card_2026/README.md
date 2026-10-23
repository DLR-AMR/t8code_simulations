# Case README: Christmas Card 2026

## Case description

Trixi.jl simulation for the Christmas card 2026. Trixi.jl uses a local installation of t8code (via T8code.jl) instead of the binaries provided by `t8code_jll`. For now, the case runs the Trixi.jl elixir `examples/t8code_2d_dgsem/elixir_advection_basic.jl`.

## Workflow

The `run.sh` script executes the following main steps:
* Configure, build, and install t8code as shared libraries with MPI.
* Set up the Julia environment in the case folder:
  * Install the Julia packages into the case-local depot `julia_depot`. Trixi.jl and T8code.jl are used from `libs/` (see `[sources]` in `Project.toml`).
  * Configure MPI.jl to use the system MPI, HDF5.jl to use the system HDF5, and T8code.jl and P4est.jl to use the local t8code, libsc, and p4est libraries (written to `LocalPreferences.toml`).
  * Precompile the packages.
* Run the elixir on 2 MPI ranks.

## Dependencies

### Fetched repositories

* `t8code` from `https://github.com/DLR-AMR/t8code`, tag `v4.0.0-26.10`.
* `T8code.jl` from `https://github.com/DLR-AMR/T8code.jl`, tag `v0.10.2` (bindings generated for t8code `v4.0.0-26.10`).
* `Trixi.jl` from `https://github.com/trixi-framework/Trixi.jl`, tag `v0.17.16`.

### Teamsverver modules

`t8code/t8code-development-gcc13-mpich`

### Other dependencies

* Julia, version 1.13.2 (has to be in `PATH`)
* MPI version 3.0 or higher (the same MPI is used to build t8code and by MPI.jl)
* HDF5 library built with the same MPI. Set `HDF5_LIBRARY_DIR` to the directory containing `libhdf5` and `libhdf5_hl`, e.g., `/usr/lib/x86_64-linux-gnu/hdf5/openmpi` for the Ubuntu package `libhdf5-openmpi-dev`.
* C++ compiler supporting C++20

## Contact person:

sandro.elsweijer@dlr.de
