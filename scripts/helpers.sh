#!/usr/bin/env bash

# Fail early
set -euo pipefail

# Hints where to find the pre-installed software on this system
source "$(dirname "${BASH_SOURCE[0]}")/../system_hints.sh"

# CMake's find_package(<PackageName>) searches the installation prefix <PackageName>_ROOT,
# but find modules do not look for the OpenCASCADE headers in its include/opencascade.
if [[ -n "$OpenCASCADE_ROOT" ]]; then
    export CMAKE_INCLUDE_PATH="$OpenCASCADE_ROOT/include/opencascade${CMAKE_INCLUDE_PATH:+:$CMAKE_INCLUDE_PATH}"
fi


# Helper function for colored log output.
log_msg() {
    printf '\033[1;33m%b\033[0m\n' "$1"
}