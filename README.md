# Lua2C Transpiler

A maintainable, extensible transpiler from Lua 5.4 to C.

## Project Overview

Lua2C translates Lua 5.4 source code into C with the following key design principles:

- **Modular Output**: One C file per module (not monolithic)
- **Static Strings**: String pool approach with static C strings (no runtime allocation for literals)
- **Debug Info**: Full debug information with #line directives for source mapping
- **Error Handling**: Lua-compatible errors using setjmp/longjmp
- **External Libraries**: VTable-based approach for love.*, math.*, string.* (not implemented in runtime)
- **Metamethod Dispatch**: Always dispatch metamethods at runtime (no compile-time optimization for flexibility)
- **Closure Support**: Static closure header (runtime/closure.h is non-generated)

### Naming Conventions

- Modules: `_l2c__<dir>__<file>_export`
- Functions: `_l2c__<dir>__<file>_<method>`

## Current Status

**Phase 1: Core Infrastructure** ✅ Complete
- AST visitor with double-dispatch pattern
- Translation context for scope, symbols, string pool
- Scope management and symbol table
- 100% test coverage

**Phase 2: Code Generation** 🔄 In Progress
- Expression generators (76% coverage)
- Statement generators (88% coverage)
- CLI with basic transpile_file() function

**Phase 3-5**: Pending (runtime, module system, optimization)

## Development & Contributing

### Installation

```bash
# Install with development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/core/test_ast_visitor.py

# Run with verbose output
pytest -v
```

### Code Formatting

```bash
# Format code with Black
black .

# Check formatting without modifying
black --check .
```

### Type Checking

```bash
# Run MyPy type checker
mypy lua2c
```

### Test Coverage

Goal: 100% test coverage for all implemented features. Current overall coverage: 88%.

## License & Credits

MIT License

This project uses [luaparser](https://github.com/andfoy/luaparser) (>=4.0.0) for Lua AST parsing.

Developed by [@firstbober](https://github.com/firstbober)

## Technical Notes

- luaparser uses specific node types: AddOp, SubOp, MultOp (not wrapped in Binop class)
- Binary/unary operators are their own node classes
- String node .s attribute is bytes, decode via expr.s.decode()
- Block/If/While constructors require body=[] parameter
- Uses pytest with coverage reporting for testing
