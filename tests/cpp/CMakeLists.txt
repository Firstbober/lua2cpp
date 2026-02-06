cmake_minimum_required(VERSION 3.14)
project(lua2c_tests)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Runtime library files
set(RUNTIME_SOURCES
    ${CMAKE_SOURCE_DIR}/../../runtime/lua_value.cpp
    ${CMAKE_SOURCE_DIR}/../../runtime/lua_state.cpp
    ${CMAKE_SOURCE_DIR}/../../runtime/lua_table.cpp
)

# Include directories
include_directories(
    ${CMAKE_SOURCE_DIR}/../../runtime
)

# Add runtime as a library
add_library(lua2c_runtime ${RUNTIME_SOURCES})

# Custom command to transpile simple.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/simple.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/simple.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/simple.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/simple.lua
    VERBATIM
)

# Simple test executable
add_executable(simple_test main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/simple.cpp)
target_link_libraries(simple_test lua2c_runtime)

# Spectral-norm target
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/spectral-norm.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/spectral-norm.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/spectral-norm.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/spectral-norm.lua
    VERBATIM
)

# Spectral-norm test executable
add_executable(spectral_norm_test spectral_norm_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/spectral-norm.cpp)
target_link_libraries(spectral_norm_test lua2c_runtime)
