# lua2cpp

A Lua 5.4 to C++ transpiler that converts Lua source code into compilable C++17.

## Installation

```bash
pip install -e ".[dev]"
```

Requirements:
- Python 3.10+
- luaparser >= 4.0.0 (installed automatically)

## Usage

### Basic Transpilation

```bash
lua2cpp input.lua                    # Outputs to input.cpp
lua2cpp input.lua -o output.cpp      # Specify output file
lua2cpp input.lua --output-dir out/  # Specify output directory
```

### CLI Options

| Option | Description |
|--------|-------------|
| `input` | Input Lua file to transpile (required) |
| `-o, --output` | Output C++ file name |
| `--output-dir` | Output directory (default: current directory) |
| `-v, --verbose` | Print verbose file generation details |
| `--lib` | Generate as library (outputs `.hpp` header with forward declarations) |
| `--header` | Generate `state.h` header with library API declarations |
| `--convention MODULE=STYLE` | Set call convention for a module |
| `--convention-file FILE` | Load call conventions from YAML config file |
| `--runtime {table,lua_table}` | Select runtime type (default: table) |

### Call Conventions

Control how library functions are invoked:

```bash
lua2cpp input.lua --convention love=flat_nested
lua2cpp input.lua --convention G=flat --convention math=namespace
```

Available styles:
- `namespace` - Use C++ namespaces
- `flat` - Flat function calls
- `flat_nested` - Nested flat calls
- `table` - Table-based dispatch (default)

### Runtime Selection

```bash
lua2cpp input.lua --runtime table       # Default TABLE struct
lua2cpp input.lua --runtime lua_table   # TValue/LuaTable runtime
```

## Project Structure

```
lua2cpp/
├── lua2cpp/
│   ├── cli/main.py              # CLI entry point
│   ├── core/                    # Core infrastructure
│   │   ├── ast_visitor.py       # AST visitor pattern
│   │   ├── scope.py             # Scope management
│   │   ├── symbol_table.py      # Symbol resolution
│   │   ├── types.py             # Type system
│   │   └── call_convention.py   # Call conventions
│   ├── analyzers/               # Static analysis
│   │   ├── type_resolver.py     # Type inference
│   │   ├── function_registry.py # Function tracking
│   │   └── y_combinator_detector.py
│   └── generators/              # Code generation
│       ├── cpp_emitter.py       # Main C++ emitter
│       ├── expr_generator.py    # Expression codegen
│       ├── stmt_generator.py    # Statement codegen
│       └── header_generator.py  # Header generation
├── tests/
│   ├── python/                  # Python unit tests
│   └── cpp/                     # C++ integration tests
└── benchmarks/                   # Benchmark Lua files
```

## Design Principles

- **Modular Output**: One C++ file per Lua module
- **Static Strings**: String pool with static C strings (no runtime allocation for literals)
- **Debug Info**: Full `#line` directives for source mapping
- **Error Handling**: Lua-compatible errors via setjmp/longjmp
- **Metamethod Dispatch**: Runtime dispatch for flexibility
- **C++17 Target**: Modern C++ with templates and auto

### Naming Conventions

- Modules: `_l2c__<dir>__<file>_export`
- Functions: `_l2c__<dir>__<file>_<method>`

## Development

### Running Tests

```bash
pytest                              # Run all tests with coverage
pytest tests/python/test_scope.py   # Run specific test file
pytest -v                           # Verbose output
```

### Code Quality

```bash
black .                 # Format code
black --check .         # Check formatting
mypy lua2cpp            # Type checking
```

## Examples

```lua
-- simple.lua
local function add(a, b)
    return a + b
end

print(add(5, 7))
```

```bash
lua2cpp simple.lua --lib --output-dir output/
```

Generates:
- `output/simple.cpp` - C++ implementation
- `output/simple.hpp` - Header with forward declarations

## C++ Integration

Generated C++ requires a runtime library. See `tests/cpp/` for integration examples using CMake.

Basic usage:

```cpp
#include "simple.hpp"
#include "runtime/l2c_runtime.hpp"

int main() {
    simple_lua_State state;
    state.print = &l2c::print;
    _l2c__simple_export(&state);
    return 0;
}
```

## Current Status

| Component | Status |
|-----------|--------|
| AST Visitor | Complete |
| Scope/Symbol Management | Complete |
| Expression Generation | In Progress |
| Statement Generation | In Progress |
| Runtime Library | Partial |
| Module System | Planned |

## License

MIT License

Uses [luaparser](https://github.com/andfoy/luaparser) for Lua AST parsing.

Developed by [@firstbober](https://github.com/firstbober)
