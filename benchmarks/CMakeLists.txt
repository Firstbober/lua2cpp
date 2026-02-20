cmake_minimum_required(VERSION 3.14)
project(lua2c_benchmarks)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(PYTHON_VENV ${CMAKE_CURRENT_SOURCE_DIR}/../.venv/bin/python)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../tests/cpp/runtime)

add_library(lua2c_runtime STATIC
    ${CMAKE_CURRENT_SOURCE_DIR}/../tests/cpp/runtime/l2c_runtime_v2.cpp
)

function(add_benchmark NAME LUA_FILE)
    set(GEN_DIR ${CMAKE_CURRENT_SOURCE_DIR}/cpp)
    set(LUA_PATH ${CMAKE_CURRENT_SOURCE_DIR}/lua/${LUA_FILE})
    get_filename_component(LUA_STEM ${LUA_FILE} NAME_WE)

    add_custom_command(
        OUTPUT ${GEN_DIR}/${LUA_STEM}.cpp ${GEN_DIR}/${LUA_STEM}.hpp
        COMMAND ${PYTHON_VENV} -m lua2cpp.cli.main ${LUA_PATH} --lib --output-dir ${GEN_DIR}
        DEPENDS ${LUA_PATH}
        VERBATIM
        COMMENT "Transpiling ${LUA_FILE}"
    )

    configure_file(
        ${CMAKE_CURRENT_SOURCE_DIR}/benchmark_main.cpp.in
        ${CMAKE_CURRENT_BINARY_DIR}/${NAME}_main.cpp
        @ONLY
    )

    set(MODULE_FILE ${LUA_STEM})
    set(MODULE_INIT_FUNC ${LUA_STEM}_module_init)
    configure_file(
        ${CMAKE_CURRENT_SOURCE_DIR}/benchmark_main.cpp.in
        ${CMAKE_CURRENT_BINARY_DIR}/${NAME}_main.cpp
        @ONLY
    )

    add_executable(${NAME}
        ${CMAKE_CURRENT_BINARY_DIR}/${NAME}_main.cpp
        ${GEN_DIR}/${LUA_STEM}.hpp
    )
    set_source_files_properties(
        ${CMAKE_CURRENT_BINARY_DIR}/${NAME}_main.cpp
        PROPERTIES OBJECT_DEPENDS "${GEN_DIR}/${LUA_STEM}.cpp"
    )
    target_include_directories(${NAME} PRIVATE ${GEN_DIR})
    target_link_libraries(${NAME} lua2c_runtime)
endfunction()

add_benchmark(bench_dense_array dense_array.lua)
add_benchmark(bench_mixed_ops mixed_ops.lua)
