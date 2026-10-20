cmake_minimum_required( VERSION 3.19 )

project( PNG2MESH_DEMO LANGUAGES C CXX )

# This case builds png2mesh from source and links it against t8code v4.0.0
# The actual build is handled by run.sh which:
# 1. Builds and installs t8code v4.0.0
# 2. Builds png2mesh with the installed t8code
# 3. Runs the png2mesh_demo executable

# If building manually outside of run.sh, you would need to:
# - First build and install t8code to CASE_INSTALL_DIR
# - Then configure png2mesh with -DCMAKE_PREFIX_PATH=$CASE_INSTALL_DIR
