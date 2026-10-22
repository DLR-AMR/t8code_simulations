# Case README: Tutorial Internal

## Case description

This simple example case uses the curved-mesh tutorial to demonstrate the usage of this repository and mimic the basic steps required to include a t8code-internal feature.

## Workflow

The `run.sh` script executes the following main steps:
* Move t8code from `libs` subfolder to the case folder because it is the main software packages for t8code-internal cases.
* Configure, build, and install t8code.
* Run the executable of the curved-mesh tutorial, using the geometry files `airfoil_windtunnel_hexahedra.msh` and `airfoil_windtunnel_hexahedra.msh`provided in the main case directory.

## Dependencies

### Fetched repositories

* `t8code` from `https://github.com/DLR-AMR/t8code`.

### Teamsverver modules

`t8code/t8code-development-gcc13-mpich-with-vtk-9.1-and-occ-7.6.0`

### Downloaded files

* airfoil_windtunnel_hexahedra.brep
* airfoil_windtunnel_hexahedra.msh

from [t8data repository](https://github.com/DLR-AMR/t8data/tree/9fcd9b9d5ac7e07e8a82cea28377e43fb2d1b90e/geometries/airfoil_windtunnel).

### Other dependencies

* OpenCASCADE, version 7.6.0
* VTK library, version 9.1
* MPI version 3.0 or higher
* C++ compiler supporting C++20
* ...

## Contact person:

thomas.spenke@dlr.de