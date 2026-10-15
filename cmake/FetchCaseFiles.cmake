
include(FetchContent)

function(fetch_case_files manifest)
    if(NOT EXISTS "${manifest}")
        message(STATUS "File manifest not found: ${manifest}")
        return()
    endif()

    # Extract case directory from manifest path
    get_filename_component(CASE_DIR "${manifest}" DIRECTORY)

    file(READ "${manifest}" json)

    string(JSON file_count LENGTH "${json}" files)

    if(file_count GREATER 0)
        math(EXPR last_file "${file_count} - 1")

        foreach(i RANGE 0 ${last_file})
            string(JSON url GET "${json}" files ${i} url)
            string(JSON filename GET "${json}" files ${i} filename)
            string(JSON target_path GET "${json}" files ${i} target_path)

            if(url STREQUAL "")
                message(FATAL_ERROR
                    "File entry ${i} needs a URL")
            endif()

            if(filename STREQUAL "")
                message(FATAL_ERROR
                    "File entry ${i} needs a filename")
            endif()

            # Determine the target directory
            if(target_path STREQUAL "")
                # Default to the case directory
                set(target_dir "${CASE_DIR}")
            else()
                # Use the specified target_path (relative to case directory)
                if(IS_ABSOLUTE "${target_path}")
                    set(target_dir "${target_path}")
                else()
                    set(target_dir "${CASE_DIR}/${target_path}")
                endif()
            endif()

            # Ensure target directory exists
            file(MAKE_DIRECTORY "${target_dir}")

            message(STATUS
                "Downloading file: ${filename} from ${url} to ${target_dir}")

            # Use file(DOWNLOAD) to fetch the file
            file(DOWNLOAD
                "${url}"
                "${target_dir}/${filename}"
                SHOW_PROGRESS
                TIMEOUT 300
                STATUS download_status
            )

            # Check if download was successful
            list(GET download_status 0 download_result)
            if(NOT download_result EQUAL 0)
                message(FATAL_ERROR
                    "Failed to download file: ${filename} from ${url}")
            endif()

            message(STATUS "Successfully downloaded: ${filename}")
        endforeach()
    endif()
endfunction()
