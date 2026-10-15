cmake_minimum_required( VERSION 3.19 )

project( HELLO_WORLD LANGUAGES C CXX )

find_package( T8CODE CONFIG REQUIRED )

add_executable( hello_world hello_world.cxx )
target_link_libraries( hello_world PRIVATE T8CODE::T8 )
