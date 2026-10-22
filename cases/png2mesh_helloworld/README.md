# Case README: PNG2Mesh Demo

## Case description

This case demonstrates the usage of png2mesh (https://github.com/dlr-amr/png2mesh), a tool for converting PNG images to meshes. It is built and linked against t8code v4.0.0.-26.10

The case fetches both t8code v4.0.0.-26.10 and png2mesh, builds png2mesh with t8code support, and runs the png2mesh_demo executable on the provided example image.
The example image is downloaded from t8data.

## Workflow

The `run.sh` script executes the following main steps:
* Configure, build, and install t8code v4.0.0.-26.10
* Configure and build png2mesh, linking it against the installed t8code.
* Download the t8code_simulations.png image from t8data.
* Run the png2mesh_demo executable on the PNG image and write the output *vtu files into ./output.
* Display the output log.

## Dependencies

### Fetched repositories

* `t8code` v4.0.0-26.10, commit e90aa8f from `https://github.com/DLR-AMR/t8code.git`
* `png2mesh` from `https://github.com/dlr-amr/png2mesh.git`

### Files

* `t8code_simulations.png` from `https://github.com/dlr-amr/t8data.git`

### Teamserver modules

`t8code/t8code-development-gcc13-mpich`

### Other dependencies

* MPI version 3.0 or higher
* C++ compiler supporting C++20
* Ninja build system
* PNG library development files

## Usage

To run this case:
```bash
cmake . -DCMAKE_PREFIX_PATH=<path_to_t8code_install> -DCASE_DIR=cases/png2mesh_helloworld
```

## Command executed

The demo is run with the following command:
```bash
cd output
mpirun -np 4 ../libs/png2mesh-build/png2mesh_demo -f ../input/t8code_simulations.png -m9
```

Where:
- `-f ../input/t8code_simulations.png`: Input PNG file
- `-m9`: Mesh refinement level

## Contact person:

johannes.holke@dlr.de
