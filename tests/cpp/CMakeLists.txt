cmake_minimum_required(VERSION 3.14)
project(lua2c_tests)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Runtime library files
set(RUNTIME_SOURCES
    ${CMAKE_SOURCE_DIR}/../../runtime/lua_value.cpp
    ${CMAKE_SOURCE_DIR}/../../runtime/lua_table.cpp
    ${CMAKE_SOURCE_DIR}/../../runtime/lua_array.cpp
)

# Include directories
include_directories(
    ${CMAKE_SOURCE_DIR}/../../runtime
)

# Add runtime as a library
add_library(lua2c_runtime ${RUNTIME_SOURCES})

# Test for simple.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/simple_state.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/simple_module.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/simple_module.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/simple.lua --lib --output-dir ${CMAKE_CURRENT_SOURCE_DIR}/generated
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/simple.lua
    VERBATIM
)

add_executable(simple_test simple_main_new.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/simple_module.cpp)
target_include_directories(simple_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/generated)
target_link_libraries(simple_test lua2c_runtime)
