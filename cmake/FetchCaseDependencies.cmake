
include(FetchContent)

function(fetch_case_dependencies manifest)
    if(NOT EXISTS "${manifest}")
        message(FATAL_ERROR
            "Dependency manifest not found: ${manifest}")
    endif()

    file(READ "${manifest}" json)

    string(JSON dep_count LENGTH "${json}" dependencies)

    if(dep_count GREATER 0)
        math(EXPR last_dep "${dep_count} - 1")

        foreach(i RANGE 0 ${last_dep})
            string(JSON name GET "${json}" dependencies ${i} name)
            string(JSON url GET "${json}" dependencies ${i} url)
            string(JSON commit GET "${json}" dependencies ${i} commit)

            if(NOT name MATCHES "^[a-zA-Z0-9_]+$")
                message(FATAL_ERROR
                    "Invalid dependency name: '${name}'")
            endif()

            if(url STREQUAL "" OR commit STREQUAL "")
                message(FATAL_ERROR
                    "Dependency '${name}' needs a URL and commit")
            endif()

            message(STATUS
                "Fetching ${name} at ${commit}")

            FetchContent_Declare(
                ${name}
                GIT_REPOSITORY "${url}"
                GIT_TAG        "${commit}"
                GIT_SHALLOW    FALSE
                SOURCE_SUBDIR  __download_only__
            )

            FetchContent_MakeAvailable(${name})
            # FetchContent_GetProperties(${name})
        endforeach()
    endif()
endfunction()
