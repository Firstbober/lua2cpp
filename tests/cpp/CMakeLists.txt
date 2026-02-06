cmake_minimum_required(VERSION 3.14)
project(lua2c_tests)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Runtime library files
set(RUNTIME_SOURCES
    ${CMAKE_SOURCE_DIR}/../../runtime/lua_value.cpp
    ${CMAKE_SOURCE_DIR}/../../runtime/lua_state.cpp
    ${CMAKE_SOURCE_DIR}/../../runtime/lua_table.cpp
    ${CMAKE_SOURCE_DIR}/../../runtime/lua_array.cpp
)

# Include directories
include_directories(
    ${CMAKE_SOURCE_DIR}/../../runtime
)

# Add runtime as a library
add_library(lua2c_runtime ${RUNTIME_SOURCES})

# Auto-generated test targets

# Test for ack.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/ack.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/ack.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/ack.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/ack.lua
    VERBATIM
)

add_executable(ack_test ack_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/ack.cpp)
target_link_libraries(ack_test lua2c_runtime)

# Test for binary-trees.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/binary_trees.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/binary-trees.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/binary_trees.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/binary-trees.lua
    VERBATIM
)

add_executable(binary_trees_test binary_trees_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/binary_trees.cpp)
target_link_libraries(binary_trees_test lua2c_runtime)

# Test for comparisons.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/comparisons.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/comparisons.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/comparisons.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/comparisons.lua
    VERBATIM
)

add_executable(comparisons_test comparisons_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/comparisons.cpp)
target_link_libraries(comparisons_test lua2c_runtime)

# Test for fannkuch-redux.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/fannkuch_redux.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/fannkuch-redux.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/fannkuch_redux.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/fannkuch-redux.lua
    VERBATIM
)

add_executable(fannkuch_redux_test fannkuch_redux_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/fannkuch_redux.cpp)
target_link_libraries(fannkuch_redux_test lua2c_runtime)

# Test for fasta.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/fasta.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/fasta.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/fasta.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/fasta.lua
    VERBATIM
)

add_executable(fasta_test fasta_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/fasta.cpp)
target_link_libraries(fasta_test lua2c_runtime)

# Test for fixpoint-fact.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/fixpoint_fact.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/fixpoint-fact.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/fixpoint_fact.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/fixpoint-fact.lua
    VERBATIM
)

add_executable(fixpoint_fact_test fixpoint_fact_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/fixpoint_fact.cpp)
target_link_libraries(fixpoint_fact_test lua2c_runtime)

# Test for heapsort.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/heapsort.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/heapsort.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/heapsort.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/heapsort.lua
    VERBATIM
)

add_executable(heapsort_test heapsort_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/heapsort.cpp)
target_link_libraries(heapsort_test lua2c_runtime)

# Test for k-nucleotide.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/k_nucleotide.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/k-nucleotide.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/k_nucleotide.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/k-nucleotide.lua
    VERBATIM
)

add_executable(k_nucleotide_test k_nucleotide_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/k_nucleotide.cpp)
target_link_libraries(k_nucleotide_test lua2c_runtime)

# Test for mandel.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/mandel.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/mandel.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/mandel.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/mandel.lua
    VERBATIM
)

add_executable(mandel_test mandel_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/mandel.cpp)
target_link_libraries(mandel_test lua2c_runtime)

# Test for n-body.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/n_body.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/n-body.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/n_body.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/n-body.lua
    VERBATIM
)

add_executable(n_body_test n_body_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/n_body.cpp)
target_link_libraries(n_body_test lua2c_runtime)

# Test for qt.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/qt.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/qt.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/qt.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/qt.lua
    VERBATIM
)

add_executable(qt_test qt_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/qt.cpp)
target_link_libraries(qt_test lua2c_runtime)

# Test for queen.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/queen.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/queen.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/queen.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/queen.lua
    VERBATIM
)

add_executable(queen_test queen_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/queen.cpp)
target_link_libraries(queen_test lua2c_runtime)

# Test for regex-dna.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/regex_dna.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/regex-dna.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/regex_dna.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/regex-dna.lua
    VERBATIM
)

add_executable(regex_dna_test regex_dna_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/regex_dna.cpp)
target_link_libraries(regex_dna_test lua2c_runtime)

# Test for scimark.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/scimark.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/scimark.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/scimark.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/scimark.lua
    VERBATIM
)

add_executable(scimark_test scimark_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/scimark.cpp)
target_link_libraries(scimark_test lua2c_runtime)

# Test for sieve.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/sieve.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/sieve.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/sieve.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/sieve.lua
    VERBATIM
)

add_executable(sieve_test sieve_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/sieve.cpp)
target_link_libraries(sieve_test lua2c_runtime)

# Test for simple.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/simple.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/simple.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/simple.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/simple.lua
    VERBATIM
)

add_executable(simple_test simple_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/simple.cpp)
target_link_libraries(simple_test lua2c_runtime)

# Test for spectral-norm.lua
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/spectral_norm.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/spectral-norm.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/spectral_norm.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/spectral-norm.lua
    VERBATIM
)

add_executable(spectral_norm_test spectral_norm_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/spectral_norm.cpp)
target_link_libraries(spectral_norm_test lua2c_runtime)
