#!/usr/bin/env bash

# Fail early
set -euo pipefail


# Helper function for colored log output.
log_msg() {
    printf '\033[1;33m%b\033[0m\n' "$1"
}