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

# Function to add a Lua test
# LUA_STEM is the filename without extension (e.g., "spectral-norm" from "spectral-norm.lua")
function(add_lua_test TEST_NAME LUA_FILE MODULE_INIT_FUNC)
    set(GEN_DIR ${CMAKE_CURRENT_SOURCE_DIR}/generated)
    set(LUA_PATH ${CMAKE_CURRENT_SOURCE_DIR}/lua/${LUA_FILE})
    
    # Get the stem (filename without extension) for generated files
    get_filename_component(LUA_STEM ${LUA_FILE} NAME_WE)

    # Generate C++ from Lua
    add_custom_command(
        OUTPUT ${GEN_DIR}/${LUA_STEM}.hpp ${GEN_DIR}/${LUA_STEM}.cpp
        COMMAND python -m lua2cpp.cli.main ${LUA_PATH} --lib --output-dir ${GEN_DIR}
        DEPENDS ${LUA_PATH}
        VERBATIM
        COMMENT "Transpiling ${LUA_FILE} to C++"
    )

    # Configure main.cpp from template
    set(MODULE_NAME ${TEST_NAME})
    set(MODULE_FILE ${LUA_STEM})
    set(MODULE_INIT_FUNC ${MODULE_INIT_FUNC})
    configure_file(
        ${CMAKE_CURRENT_SOURCE_DIR}/templates/test_main.cpp.in
        ${CMAKE_CURRENT_BINARY_DIR}/${TEST_NAME}_main.cpp
        @ONLY
    )

    # Build executable (main.cpp includes the generated .cpp directly)
    add_executable(${TEST_NAME}_test
        ${CMAKE_CURRENT_BINARY_DIR}/${TEST_NAME}_main.cpp
    )
    target_include_directories(${TEST_NAME}_test PRIVATE
        ${CMAKE_SOURCE_DIR}/..
        ${GEN_DIR}
    )
    target_link_libraries(${TEST_NAME}_test lua2c_runtime)
endfunction()

# Add tests for key benchmarks
add_lua_test(spectral_norm spectral-norm.lua spectral_norm_module_init)
add_lua_test(n_body n-body.lua n_body_module_init)
add_lua_test(sieve sieve.lua sieve_module_init)
add_lua_test(heapsort heapsort.lua heapsort_module_init)
add_lua_test(simple simple.lua simple_module_init)
add_lua_test(binary_trees binary-trees.lua binary_trees_module_init)
add_lua_test(comparisons comparisons.lua comparisons_module_init)
