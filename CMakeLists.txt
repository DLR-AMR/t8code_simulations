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

# Simple sanity checks for chosen CASE_DIR
if(CASE_DIR STREQUAL "UNSET")
  message(FATAL_ERROR "Missing -DCASE_DIR argument!")
elseif(NOT EXISTS "${CASE_DIR}")
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
set(FETCHCONTENT_BASE_DIR "${CASE_DIR}/libs")
message(STATUS "Fetching case dependencies speficied in '${CASE_DIR}'/dependencies.json ")
include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/FetchCaseDependencies.cmake")
fetch_case_dependencies(
    "${CASE_DIR}/dependencies.json"
)

# Prepare the AMR-Teamserver-related settings like loading modules etc.
execute_process(
    COMMAND bash prepare_on_teamserver.sh
    WORKING_DIRECTORY "${CASE_DIR}"
    RESULT_VARIABLE result
)

# Run the main script of the chosen folder.
execute_process(
    COMMAND bash run.sh
    WORKING_DIRECTORY "${CASE_DIR}"
    RESULT_VARIABLE result
)

# Check whether running the case was successful.
if(result EQUAL 0)
    message(STATUS "Successully ran case '${RUN_CASE}'.")
else()
    message(FATAL_ERROR "Running '${RUN_CASE}' failed: ${result}")
endif()