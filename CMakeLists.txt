cmake_minimum_required(VERSION 3.13)

project(t8code_simulations VERSION 0.0.1)

# This list contains all files required by a case folder to be run.
set(REQUIRED_FILES_PER_CASE
    "dependencies.json"
    "prepare_on_teamserver.sh"
    "run.sh"
)

# CASE_DIR is the main argument of this CMake script. It specifies the case
# we want to run by giving its case folder.
set(CASE_DIR "UNSET" CACHE STRING "Example case to run")

# Set ON_TEAMSERVER when running on the AMR Teamserver. Only then is the
# Teamserver-specific preparation (e.g., loading modules) run; on any other
# system the case's dependencies have to be provided by the user.
option(ON_TEAMSERVER "Run on the AMR Teamserver (sources the case's prepare_on_teamserver.sh)" OFF)

# Simple sanity checks for chosen CASE_DIR
if(CASE_DIR STREQUAL "UNSET")
  message(FATAL_ERROR "Missing -DCASE_DIR argument!")
endif()

# Interpret a relative CASE_DIR relative to the repository root, independent of the build directory.
get_filename_component(CASE_DIR "${CASE_DIR}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")

if(NOT EXISTS "${CASE_DIR}")
  message(FATAL_ERROR "The case directory CASE_DIR='${CASE_DIR}' does not exist!")
endif()

# Check whether all required files are present and throw a descriptive error if not.
set(MISSING_FILES "")
foreach(FILE IN LISTS REQUIRED_FILES_PER_CASE)
    if(NOT EXISTS "${CASE_DIR}/${FILE}")
        list(APPEND MISSING_FILES "${FILE}")
    endif()
endforeach()
if(MISSING_FILES)
    message(FATAL_ERROR
        "Missing required files in '${CASE_DIR}': ${MISSING_FILES}"
    )
endif()


# Echo info output.
# message(STATUS "Selected case: ${RUN_CASE}")
message(STATUS "Case directory: ${CASE_DIR}")

# Fetch case dependencies, specififed in case directory.
# Has to be a forced cache entry: FetchContent defines its own cached default
# (<build>/_deps), which would otherwise override a normal variable on the first configure.
set(FETCHCONTENT_BASE_DIR "${CASE_DIR}/libs" CACHE PATH "Directory into which the case dependencies are fetched" FORCE)
message(STATUS "Fetching case dependencies speficied in '${CASE_DIR}'/dependencies.json ")
include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/FetchCaseDependencies.cmake")
fetch_case_dependencies(
    "${CASE_DIR}/dependencies.json"
)

# Prepare the AMR-Teamserver-related settings like loading modules etc. and run
# the main script of the chosen folder. The preparation script is sourced in the
# same shell that starts run.sh, so the environment it sets up is passed on to run.sh;
# running it in a separate process would discard it. With 'bash -e', a failing
# command in the preparation script aborts the case.
if(ON_TEAMSERVER)
    set(CASE_COMMAND "source ./prepare_on_teamserver.sh && bash ./run.sh")
else()
    message(STATUS "Skipping prepare_on_teamserver.sh (ON_TEAMSERVER=OFF).")
    set(CASE_COMMAND "bash ./run.sh")
endif()
execute_process(
    COMMAND bash -e -c "${CASE_COMMAND}"
    WORKING_DIRECTORY "${CASE_DIR}"
    RESULT_VARIABLE result
)

# Check whether running the case was successful.
if(result EQUAL 0)
    message(STATUS "Successfully ran case '${CASE_DIR}'.")
elseif(ON_TEAMSERVER)
    message(FATAL_ERROR "Running '${CASE_DIR}' failed: ${result}")
else()
    message(FATAL_ERROR
        "Running '${CASE_DIR}' failed: ${result}\n"
        "Make sure the case's dependencies (see the case's README.md) are available, "
        "or pass -DON_TEAMSERVER=ON when running on the AMR Teamserver."
    )
endif()
