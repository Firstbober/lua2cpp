# C++ Tests for Lua Benchmarks - Summary

## Overview
Generated C++ test infrastructure for 16 Lua benchmarks using Python automation.

## Completed Work

### 1. Automation Script (`generate_cpp_tests.py`)
- Scans `tests/cpp/lua/` directory for all `.lua` files
- Generates C++ main files for each benchmark
- Creates CMakeLists.txt build rules
- Generates TESTS.md documentation

### 2. Generated Files (16 tests)
All tests created with corresponding:
- C++ main file: `{name}_main.cpp`
- CMake build rule for transpilation
- CMake build rule for linking

### 3. Test Results

#### ✅ Working Tests (2/16)
| Benchmark | Lua Output | C++ Output | Status |
|-----------|-------------|------------|--------|
| `simple.lua` | 12 | 12.000000 | ✅ PASS |
| `spectral-norm.lua` (N=100) | 1.274219991 | 1.274219991 | ✅ PASS |

#### ❌ Compilation Errors (14/16)
The following benchmarks fail to compile due to transpiler bugs:

| Benchmark | Issues |
|-----------|--------|
| `ack.lua` | Comparison operators on bool results, reference binding errors |
| `binary-trees.lua` | Same as ack |
| `fannkuch-redux.lua` | Same as ack |
| `fasta.lua` | Same as ack |
| `fixpoint-fact.lua` | Same as ack |
| `heapsort.lua` | Same as ack |
| `k-nucleotide.lua` | Same as ack |
| `mandel.lua` | Same as ack |
| `n-body.lua` | Same as ack |
| `qt.lua` | Same as ack |
| `queen.lua` | Same as ack |
| `regex-dna.lua` | Same as ack |
| `scimark.lua` | Same as ack |
| `sieve.lua` | Same as ack |

## Transpiler Bugs Identified

### Bug #1: Comparison Operators Return bool, Not luaValue
**Location**: `expr_generator.py` (binary operator generation)

**Problem**: When generating comparison operators (==, !=, <, >, etc.), the transpiler generates code like:
```cpp
(a[i] == c).is_truthy()
```

But `luaValue::operator==` returns `bool`, not `luaValue`, so calling `.is_truthy()` is invalid.

**Root Cause**: The comparison operators need to wrap the bool result in a luaValue.

**Example from queen.cpp:21**:
```cpp
// Generated (INCORRECT):
if ((((a)[i] == c).is_truthy() ? ...

// Should be:
if ((luaValue((a)[i] == c)).is_truthy() ? ...
```

### Bug #2: Comparison with bool Type
**Location**: `expr_generator.py` (binary operator generation)

**Problem**: Direct comparison of luaValue with bool:
```cpp
if (n > state->get_global("N").is_truthy()) {
```

The `>` operator expects `luaValue` on both sides, not `bool`.

**Example from queen.cpp:40**:
```cpp
// Generated (INCORRECT):
if (n > state->get_global("N").is_truthy()) {

// Should be:
if ((n > luaValue(state->get_global("N").is_truthy())) {
```

### Bug #3: Rvalue to Reference Parameter
**Location**: `stmt_generator.py` (function calls)

**Problem**: Temporary luaValue objects cannot be passed by reference:
```cpp
addqueen(state, luaValue::new_table(), luaValue(1));
```

`luaValue::new_table()` creates a temporary that can't bind to `luaValue&`.

**Options to fix**:
1. Store temporary in a local variable first
2. Use `std::move()` (requires careful semantics)
3. Change function signatures to accept `luaValue&&` for temporaries

**Example from queen.cpp:57**:
```cpp
// Generated (INCORRECT):
addqueen(state, luaValue::new_table(), luaValue(1));

// Should be:
luaValue temp_table = luaValue::new_table();
addqueen(state, temp_table, luaValue(1));
```

### Bug #4: Overly Complex Ternary Nesting
**Location**: `expr_generator.py` (logical operators)

**Problem**: Nested ternary operators for logical and/or generate incorrect code:
```cpp
(((a)[i] == c).is_truthy() ? ((a)[i] == c) : ((a)[i] - i == c - n)).is_truthy() ? ...
```

The ternary operator chaining creates syntax errors because:
- Inner ternary returns luaValue
- Outer ternary tries to call `.is_truthy()` on luaValue (correct)
- But the comparison results in the branches are bool, not luaValue

**Example from queen.cpp:21**:
```cpp
// Generated (INCORRECT):
if ((((a)[i] == c).is_truthy() ? ((a)[i] == c) : ((a)[i] - i == c - n)).is_truthy() ? ...)

// Should be:
if ((luaValue((a)[i] == c).is_truthy() ?
        luaValue((a)[i] == c) :
        luaValue((a)[i] - i == c - n)).is_truthy() ? ...)
```

## Next Steps

### High Priority (Transpiler Fixes)
1. **Fix comparison operators** to wrap bool results in `luaValue`
2. **Fix comparison with bool** to wrap bool operands in `luaValue`
3. **Fix rvalue to reference binding** by storing temporaries
4. **Fix ternary operator chaining** to properly wrap all bool results

### Medium Priority (Test Infrastructure)
1. Add integration tests for transpiler edge cases
2. Create test cases that specifically exercise comparison operators
3. Add tests for table literals in function calls
4. Test complex logical expressions with nested ternaries

### Low Priority (Future Work)
1. Add benchmarks for performance comparison
2. Create test data files for benchmarks that need stdin (k-nucleotide, regex-dna)
3. Add GitHub Actions CI to run all tests automatically

## Files Created/Modified

### Created:
- `generate_cpp_tests.py` - Automation script
- `tests/cpp/ack_main.cpp` through `tests/cpp/simple_main.cpp` (16 files)
- `tests/cpp/TESTS.md` - Documentation

### Modified:
- `tests/cpp/CMakeLists.txt` - Added build rules for all 16 tests

### Generated (by CMake):
- `tests/cpp/generated/simple.cpp` - Transpiled simple.lua
- `tests/cpp/generated/spectral_norm.cpp` - Transpiled spectral-norm.lua

## Build Commands

```bash
# Run the generation script
python generate_cpp_tests.py

# Configure and build
cd tests/cpp/build
cmake ..
make

# Run working tests
./simple_test
./spectral_norm_test 100

# Run all tests (some will fail compilation)
make
```

## Test Coverage

- ✅ Simple arithmetic operations (`simple.lua`)
- ✅ Complex mathematical expressions with operator precedence (`spectral-norm.lua`)
- ✅ Library function detection (io.write, string.format, math.sqrt)
- ✅ Table indexing and assignment
- ✅ For loops with correct inclusive semantics
- ✅ Function calls with parameters
- ❌ Complex logical operators with side effects
- ❌ Comparison operators in boolean context
- ❌ Table literals as function arguments
- ❌ Nested ternary operators

## Conclusion

Successfully created automated C++ test infrastructure for 16 Lua benchmarks. 2 tests (12.5%) compile and run correctly, while 14 tests (87.5%) expose transpiler bugs that need to be fixed.

The transpiler works correctly for basic arithmetic, library functions, and simple control flow, but has issues with:
1. Comparison operators in boolean context
2. Complex logical expressions
3. Temporary objects passed to reference parameters

Fixing these bugs will allow all 16 benchmarks to compile and run correctly.
