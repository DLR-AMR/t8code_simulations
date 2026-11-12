# Case README: Christmas Card 2026

## Case description

Trixi.jl simulation for the Christmas card 2026. Trixi.jl uses a local installation of t8code (via T8code.jl) instead of the binaries provided by `t8code_jll`. The simulation `christmas_card_simulation.jl` runs a 5 m/s wind around the 3 m high christmas tree of the mesh `christmas_tree_0000.msh`, with adaptive mesh refinement around the tree and in its wake. Once the flow has converged, the mesh is deformed to the geometries `christmas_tree_*.brep` one after another, so the tree rocks in the wind with 2 Hz for 1.5 periods. The air is modeled as weakly compressible (isothermal, with a speed of sound of 50 m/s), since sound waves do not matter for the wind but would limit the time step.

The geometry files were created with `christmas_tree_brep.py` (gmsh 4.15.2):
```
python christmas_tree_brep.py --frames 256 --periods 1.5 --height 3 --tunnel -2 3 4 --mesh-size-tree 0.11
```

## Workflow

The `run.sh` script executes the following main steps:
* Configure, build, and install t8code as shared libraries with MPI, OpenCASCADE, and Eigen (downloaded by t8code).
* Set up the Julia environment in the case folder:
  * Install the Julia packages into the case-local depot `julia_depot`. Trixi.jl and T8code.jl are used from `libs/` (see `[sources]` in `Project.toml`).
  * Configure MPI.jl to use the system MPI, HDF5.jl to use the system HDF5, and T8code.jl and P4est.jl to use the local t8code, libsc, and p4est libraries (written to `LocalPreferences.toml`).
  * Precompile the packages.
* Run `christmas_card_simulation.jl` on 4 MPI ranks; the results are written to `out/`.
* Convert the results to VTK files (`out/*.vtu`) with Trixi2Vtk.jl for ParaView.

## Dependencies

### Fetched repositories

* `t8code` from `https://github.com/DLR-AMR/t8code`, branch `christmas_card_2026`.
* `T8code.jl` from `https://github.com/DLR-AMR/T8code.jl`, branch `se-post_update_26.10`.
* `Trixi.jl` from `https://github.com/sandro-elsweijer/Trixi.jl` (fork), branch `feature-mesh_deformation`.

### Teamsverver modules

`t8code/t8code-development-gcc13-mpich-with-vtk-9.1-and-occ-7.6.0`

### Other dependencies

* Julia, version 1.13.2 (has to be in `PATH`)
* MPI version 3.0 or higher (the same MPI is used to build t8code and by MPI.jl)
* HDF5 library built with the same MPI. Set `HDF5_LIBRARY_DIR` in `system_hints.sh` in the repository root to the directory containing `libhdf5` and `libhdf5_hl`, e.g., `/usr/lib/x86_64-linux-gnu/hdf5/openmpi` for the Ubuntu package `libhdf5-openmpi-dev`.
* OpenCASCADE, version 7.6.0
* C++ compiler supporting C++20

## Contact person:

sandro.elsweijer@dlr.de
