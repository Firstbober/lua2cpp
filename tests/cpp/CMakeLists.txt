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

# Test for spectral-norm.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/spectral_norm_state.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/spectral_norm_module.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/spectral_norm_module.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/spectral-norm.lua --lib --output-dir ${CMAKE_CURRENT_SOURCE_DIR}/generated
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/spectral-norm.lua
    VERBATIM
)

add_executable(spectralnorm_test spectralnorm_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/spectral_norm_module.cpp)
target_include_directories(spectralnorm_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/generated)
target_link_libraries(spectralnorm_test lua2c_runtime)

# Test for ack.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/ack_module.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/ack_module.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/ack.lua --output-dir ${CMAKE_CURRENT_SOURCE_DIR}/generated
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/ack.lua
    VERBATIM
)

add_executable(ack_test ack_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/ack_module.cpp)
target_include_directories(ack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/generated)
target_link_libraries(ack_test lua2c_runtime)

# Test for test_array.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/test_array_state.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/test_array_module.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/test_array_module.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/test_array.lua --lib --output-dir ${CMAKE_CURRENT_SOURCE_DIR}/generated
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/test_array.lua
    VERBATIM
)

add_executable(test_array_test test_array_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/test_array_module.cpp)
target_include_directories(test_array_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/generated)
target_link_libraries(test_array_test lua2c_runtime)

# Test for test_assign.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/test_assign_state.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/test_assign_module.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/test_assign_module.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/test_assign.lua --lib --output-dir ${CMAKE_CURRENT_SOURCE_DIR}/generated
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/test_assign.lua
    VERBATIM
)

add_executable(test_assign_test test_assign_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/test_assign_module.cpp)
target_include_directories(test_assign_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/generated)
target_link_libraries(test_assign_test lua2c_runtime)

# Test for test_func.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/test_func_state.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/test_func_module.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/test_func_module.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/test_func.lua --lib --output-dir ${CMAKE_CURRENT_SOURCE_DIR}/generated
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/test_func.lua
    VERBATIM
)

add_executable(test_func_test test_func_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/test_func_module.cpp)
target_include_directories(test_func_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/generated)
target_link_libraries(test_func_test lua2c_runtime)

# Test for comparisons.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/comparisons_state.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/comparisons_module.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/comparisons_module.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/comparisons.lua --lib --output-dir ${CMAKE_CURRENT_SOURCE_DIR}/generated
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/comparisons.lua
    VERBATIM
)

add_executable(comparisons_test comparisons_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/comparisons_module.cpp)
target_include_directories(comparisons_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/generated)
target_link_libraries(comparisons_test lua2c_runtime)

# Test for sieve.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/sieve_state.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/sieve_module.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/sieve_module.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/sieve.lua --lib --output-dir ${CMAKE_CURRENT_SOURCE_DIR}/generated
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/sieve.lua
    VERBATIM
)

add_executable(sieve_test sieve_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/sieve_module.cpp)
target_include_directories(sieve_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/generated)
target_link_libraries(sieve_test lua2c_runtime)

# Test for heapsort.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/heapsort_state.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/heapsort_module.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/heapsort_module.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/heapsort.lua --lib --output-dir ${CMAKE_CURRENT_SOURCE_DIR}/generated
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/heapsort.lua
    VERBATIM
)

add_executable(heapsort_test heapsort_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/heapsort_module.cpp)
target_include_directories(heapsort_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/generated)
target_link_libraries(heapsort_test lua2c_runtime)

# Test for fixpoint-fact.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/fixpoint_fact_state.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/fixpoint_fact_module.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/fixpoint_fact_module.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/fixpoint-fact.lua --lib --output-dir ${CMAKE_CURRENT_SOURCE_DIR}/generated
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/fixpoint-fact.lua
    VERBATIM
)

add_executable(fixpoint_fact_test fixpoint_fact_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/fixpoint_fact_module.cpp)
target_include_directories(fixpoint_fact_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/generated)
target_link_libraries(fixpoint_fact_test lua2c_runtime)

# Test for binary-trees.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/binary_trees_state.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/binary_trees_module.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/binary_trees_module.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/binary-trees.lua --lib --output-dir ${CMAKE_CURRENT_SOURCE_DIR}/generated
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/binary-trees.lua
    VERBATIM
)

add_executable(binary_trees_test binary_trees_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/binary_trees_module.cpp)
target_include_directories(binary_trees_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/generated)
target_link_libraries(binary_trees_test lua2c_runtime)
