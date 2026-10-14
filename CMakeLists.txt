cmake_minimum_required(VERSION 3.13)

project(t8code_simulations VERSION 0.0.1)

# RUN_CASE is the main argument of this CMake script. It specifies the case
# we want to run by giving its name (see below for the list of valid options).
set(RUN_CASE "UNSET" CACHE STRING "Example case to run")
set_property(CACHE RUN_CASE PROPERTY STRINGS
    HELLO_WORLD
    ANOTHER_EXAMPLE
)

# Interpret the read-in value of RUN_CASE:
# - If it is a valid case, set some case-dependent variables, like the case directory.
# - Else throw an error.
if(RUN_CASE STREQUAL "HELLO_WORLD")
    set(CASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/cases/hello_world")
elseif(RUN_CASE STREQUAL "ANOTHER_EXAMPLE")
    set(CASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/cases/another_example")
else()
    message(FATAL_ERROR "Invalid or missing RUN_CASE='${RUN_CASE}'. ")
endif()

# Echo info output.
message(STATUS "Selected case: ${RUN_CASE}")
message(STATUS "Case directory: ${CASE_DIR}")

# Fetch case dependencies, specififed in case directory.
set(FETCHCONTENT_BASE_DIR "${CASE_DIR}/libs")
message(STATUS "Fetching case dependencies speficied in '${CASE_DIR}'/dependencies.json ")
include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/FetchCaseDependencies.cmake")
fetch_case_dependencies(
    "${CASE_DIR}/dependencies.json"
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