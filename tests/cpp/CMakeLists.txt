cmake_minimum_required(VERSION 3.14)
project(lua2c_tests)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Use venv Python for transpiler
set(PYTHON_VENV ${CMAKE_CURRENT_SOURCE_DIR}/../../.venv/bin/python)

# Include directories for new runtime (header-only)
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/runtime
)

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
        COMMAND ${PYTHON_VENV} -m lua2cpp.cli.main ${LUA_PATH} --lib --runtime=lua_table --output-dir ${GEN_DIR}
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

    # Build executable - main.cpp #includes the generated .cpp directly
    # Add .hpp as source to trigger generation (but .cpp is included, not compiled separately)
    add_executable(${TEST_NAME}_test
        ${CMAKE_CURRENT_BINARY_DIR}/${TEST_NAME}_main.cpp
        ${GEN_DIR}/${LUA_STEM}.hpp  # Triggers custom_command
    )
    # Ensure generated .cpp exists (dependency tracking)
    set_source_files_properties(
        ${CMAKE_CURRENT_BINARY_DIR}/${TEST_NAME}_main.cpp
        PROPERTIES OBJECT_DEPENDS "${GEN_DIR}/${LUA_STEM}.cpp"
    )
    target_include_directories(${TEST_NAME}_test PRIVATE
        ${CMAKE_SOURCE_DIR}/..
        ${GEN_DIR}
    )
    # New runtime is header-only, no linking needed
endfunction()

# Add tests for key benchmarks
add_lua_test(spectral_norm spectral-norm.lua spectral_norm_module_init)
add_lua_test(simple simple.lua simple_module_init)

# Benchmarks
add_lua_test(binary_trees binary-trees.lua binary_trees_module_init)
add_lua_test(n_body n-body.lua n_body_module_init)
add_lua_test(fasta fasta.lua fasta_module_init)
add_lua_test(mandel mandel.lua mandel_module_init)
add_lua_test(fannkuch_redux fannkuch-redux.lua fannkuch_redux_module_init)
add_lua_test(heapsort heapsort.lua heapsort_module_init)
add_lua_test(queen queen.lua queen_module_init)
add_lua_test(scimark scimark.lua scimark_module_init)
add_lua_test(regex_dna regex-dna.lua regex_dna_module_init)
add_lua_test(k_nucleotide k-nucleotide.lua k_nucleotide_module_init)
add_lua_test(ack ack.lua ack_module_init)
add_lua_test(sieve sieve.lua sieve_module_init)
add_lua_test(fixpoint_fact fixpoint-fact.lua fixpoint_fact_module_init)
add_lua_test(comparisons comparisons.lua comparisons_module_init)
add_lua_test(qt qt.lua qt_module_init)

# Simple tests
add_lua_test(test_array test_array.lua test_array_module_init)
add_lua_test(test_assign test_assign.lua test_assign_module_init)
add_lua_test(test_func test_func.lua test_func_module_init)
add_lua_test(test_combined_nil_concat test_combined_nil_concat.lua test_combined_nil_concat_module_init)
add_lua_test(test_concat_basic test_concat_basic.lua test_concat_basic_module_init)
add_lua_test(test_concat_chain test_concat_chain.lua test_concat_chain_module_init)
add_lua_test(test_concat_in_call test_concat_in_call.lua test_concat_in_call_module_init)
add_lua_test(test_convention_flat test_convention_flat.lua test_convention_flat_module_init)
add_lua_test(test_convention_flat_nested test_convention_flat_nested.lua test_convention_flat_nested_module_init)
add_lua_test(test_convention_namespace test_convention_namespace.lua test_convention_namespace_module_init)
add_lua_test(test_convention_table test_convention_table.lua test_convention_table_module_init)
add_lua_test(test_modop_basic test_modop_basic.lua test_modop_basic_module_init)
add_lua_test(test_modop_in_expr test_modop_in_expr.lua test_modop_in_expr_module_init)
add_lua_test(test_nil_basic test_nil_basic.lua test_nil_basic_module_init)
add_lua_test(test_nil_table test_nil_table.lua test_nil_table_module_init)
add_lua_test(test_type_inference test_type_inference.lua test_type_inference_module_init)
add_lua_test(test_ulnotop_basic test_ulnotop_basic.lua test_ulnotop_basic_module_init)
add_lua_test(test_ulnotop_in_call test_ulnotop_in_call.lua test_ulnotop_in_call_module_init)
