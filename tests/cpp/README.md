# Lua2C++ C++ Testing Project

This directory contains a CMake-based C++ project for testing Lua2C++ transpiler with actual compiled code.

## Status

The C++ testing infrastructure has been updated to match the new transpiler architecture.

### Current State
- ✅ **Simple test works** (simple.lua) - Library mode, no command-line arguments
- ⏸️ **Complex tests** have code generation bugs that need to be fixed in the transpiler before they can be enabled
- 📦 **17 Lua test files** available in `lua/` directory for future use

## Current Working Test

### simple.lua
- **Test executable**: `simple_test`
- **Lua source**: `lua/simple.lua`
- **Usage**:
```bash
cd tests/cpp/build
./simple_test
```
- **Expected Output**:
```
Testing transpiled simple.lua...

Running simple.lua...
12.000000

Test completed successfully!
```

## Building

```bash
cd tests/cpp
mkdir -p build
cd build
cmake ..
make
```

## Architecture

The testing infrastructure uses:
- **Custom state types**: Each module gets its own state struct (e.g., `simple_lua_State`)
- **Library mode (--lib)**: For simple tests without command-line arguments
- **Standalone mode (no --lib)**: For tests needing `arg` member
- **Runtime library**: Consolidated in `runtime/l2c_runtime.hpp`

### Generation Example

```bash
# Library mode (simple tests)
python -m lua2c.cli.main lua/simple.lua --lib --output-dir build/
# Generates: simple_state.hpp, simple_module.hpp, simple_module.cpp
```

## Directory Structure

```
tests/cpp/
├── CMakeLists.txt          # CMake build configuration (updated for new architecture)
├── README.md               # This file
├── .gitignore             # Git ignore patterns
├── simple_main_new.cpp     # Main file for simple test (uses simple_lua_State)
├── lua/                   # Lua test source files (17 files)
│   ├── simple.lua          # Currently working
│   ├── spectral-norm.lua   # Benchmark (needs transpiler fixes)
│   └── ...                # Other benchmarks (need transpiler fixes)
├── generated/             # Auto-generated C++ files
│   ├── simple_state.hpp
│   ├── simple_module.hpp
│   └── simple_module.cpp
└── build/                # CMake build directory (created during build)
```

## Adding New Tests

1. Add a new `.lua` file to the `lua/` directory
2. Add to `CMakeLists.txt`:
```cmake
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/generated/mytest_state.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/mytest_module.hpp
           ${CMAKE_CURRENT_SOURCE_DIR}/generated/mytest_module.cpp
    COMMAND python -m lua2c.cli.main ${CMAKE_CURRENT_SOURCE_DIR}/lua/mytest.lua --lib --output-dir ${CMAKE_CURRENT_SOURCE_DIR}/generated
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/lua/mytest.lua
    VERBATIM
)

add_executable(mytest_test mytest_main.cpp ${CMAKE_CURRENT_SOURCE_DIR}/generated/mytest_module.cpp)
target_include_directories(mytest_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/generated)
target_link_libraries(mytest_test lua2c_runtime)
```

3. Create `mytest_main.cpp`:
```cpp
#include "l2c_runtime.hpp"
#include "mytest_state.hpp"
#include "mytest_module.hpp"
#include <iostream>

int main() {
    std::cout << "Testing transpiled mytest.lua..." << std::endl;

    mytest_lua_State state;

    // Initialize library function pointers
    state.print = &l2c::print;
    state.tonumber = &l2c::tonumber;

    // Call the transpiled module
    luaValue result = _l2c__mytest_export(&state);

    std::cout << "\nTest completed successfully!" << std::endl;
    return 0;
}
```

## Known Issues

Several Lua constructs generate incorrect C++ code that needs to be fixed in the transpiler before more tests can be enabled:

1. **Function pointer calls** use brace initialization instead of proper vector creation
2. **Local function calls** are incorrectly generated as state member calls
3. **Local variable assignments** incorrectly assigned to state members
4. **Library function calls** need proper vector initialization for functions like `print()` and `io.write()`

## Future Work

1. Fix code generation bugs in transpiler
2. Enable more tests from the 17 available Lua files
3. Add comprehensive test coverage for various Lua constructs
4. Benchmark transpiled code against native Lua execution
