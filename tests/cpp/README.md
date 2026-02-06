# Lua2C++ C++ Testing Project

This directory contains a CMake-based C++ project for testing the Lua2C++ transpiler with actual compiled code.

## Directory Structure

```
tests/cpp/
├── CMakeLists.txt          # CMake build configuration
├── main.cpp                # Test entry point
├── generated/              # Transpiled C++ files (auto-generated)
│   └── simple.cpp          # Generated from lua/simple.lua
├── lua/                    # Lua source files
│   ├── simple.lua          # Simple test file
│   └── spectral-norm.lua   # Benchmark test file (not yet enabled)
└── build/                  # CMake build directory (created during build)
```

## Building

```bash
cd tests/cpp
mkdir -p build
cd build
cmake ..
make
```

## Running Tests

```bash
# Run simple test
cd tests/cpp/build
./simple_test
```

## Expected Output

For the simple test:
```
Testing transpiled Lua code...

Running simple.lua...
12.000000

Test completed successfully!
```

## Adding New Tests

1. Add a new `.lua` file to the `lua/` directory
2. Add a custom command in `CMakeLists.txt` to transpile it
3. Create a new executable target in `CMakeLists.txt`
4. Add a forward declaration in `main.cpp` or a new test file

Example CMake addition:
```cmake
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/newtest.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/newtest.lua -o ${CMAKE_CURRENT_SOURCE_DIR}/generated/newtest.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/newtest.lua
    VERBATIM
)

add_executable(newtest main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/newtest.cpp)
target_link_libraries(newtest lua2c_runtime)
```

## Current Status

- ✅ Simple test works correctly
- ⏳ Spectral-norm benchmark (commented out, needs table indexing support)

## Known Issues

1. Table indexing not yet implemented (needed for spectral-norm.lua)
2. Function naming uses only filename (no directory path) - this is intentional
3. All generated module export functions return `luaValue()` (nil)

## Technical Notes

- Module export function names follow the pattern `_l2c__<filename>_export`
- Local functions are compiled to C++ functions with `luaState*` parameter
- Global functions are retrieved via `state->get_global("name")`
- The transpiler automatically adds `return luaValue();` at the end of module exports
