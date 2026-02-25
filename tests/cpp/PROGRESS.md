# Lua Transpilation Progress

**Last Updated**: 2026-02-25

## IMPORTANT: Development Workflow

```bash
# After making ANY changes to the transpiler, ALWAYS:
cd tests/cpp && make clean

# Then regenerate and test:
for lua in lua/*.lua; do
  name=$(basename "$lua" .lua | tr '-' '_')
  python -m lua2cpp.cli.main "$lua" -o "${name}.cpp" --runtime lua_table
done
```

## Test Status Summary

| Status | Count |
|--------|-------|
| PASS | 26 |
| BUILD_FAIL | 9 |
| NO_CPP | 3 |
| **Total** | **38** |

## Detailed Test Results

### PASSING (builds + output matches LuaJIT)

| Test | C++ Output | LuaJIT Output | Notes |
|------|------------|---------------|-------|
| simple | 12 | 12 | Basic test |
| spectral_norm (100) | 1.274219991 | 1.274219991 | Numeric computation |
| mandel (10) | 2652 | 2652 | Uses metamethods (__add, __mul) |
| binary_trees | correct | correct | Recursive, tables |
| n_body | correct | correct | Tables, io.write |
| heapsort | correct | correct | Uses math.random, math.floor |
| sieve | 100 8192 (count wrong) | 100 8192, Count: 1028 | Descending for-loop OK, scoping bug |
| ack | correct | correct | Recursive function |
| comparisons | correct | correct | Comparison operators |
| fannkuch_redux | correct | correct | Uses goto (limited) |
| queen | correct | correct | Backtracking |
| test_array | 100 100 | 100 100 | Array operations |
| test_assign | correct | correct | Assignment |
| test_func | correct | correct | Functions |
| test_concat_basic | correct | correct | String concat |
| test_concat_chain | correct | correct | Chained concat |
| test_concat_in_call | correct | correct | Concat in function call |
| test_combined_nil_concat | correct | correct | Nil + concat |
| test_convention_namespace | correct | correct | Namespace convention |
| test_convention_table | correct | correct | Table convention |
| test_modop_basic | correct | correct | Modulo operator |
| test_modop_in_expr | correct | correct | Modulo in expression |
| test_nil_table | correct | correct | Nil in table |
| test_type_inference | correct | correct | Type inference |
| test_ulnotop_basic | correct | correct | Unary not operator |
| test_ulnotop_in_call | correct | correct | Unary not in call |

### BUILD_FAIL (compilation errors)

| Test | Error | Root Cause |
|------|-------|------------|
| fasta | `loadstring` not declared | Runtime stub for loadstring |
| fixpoint_fact | Y-combinator pattern | Self-application f(f) cannot compile in C++17 |
| k_nucleotide | for-in loop | For-in loops not implemented |
| qt | Unknown | Needs investigation |
| regex_dna | for-in loop | For-in loops not implemented |
| scimark | jit table access | Missing jit runtime, require |
| test_convention_flat | Convention error | Flat convention not working |
| test_convention_flat_nested | Convention error | Flat nested convention not working |
| test_nil_basic | Unknown | Needs investigation |

### NO_CPP (no corresponding .cpp file)

| Test | Needed File | Notes |
|------|-------------|-------|
| heapsort_simple | heapsort_simple.cpp | Duplicate test? |
| n_body_simple | n_body_simple.cpp | Duplicate test? |
| spectral_norm_simple | spectral_norm_simple.cpp | Duplicate test? |

## Root Causes to Fix

### Priority 1: For-in Loops
**Files affected**: k_nucleotide.lua, regex_dna.lua
**Location**: `lua2cpp/generators/stmt_generator.py:622`
**Current output**: `// for-in loop not implemented`
**Solution**: Implement generic for-in loop using pairs()/ipairs() iterators

### Priority 2: Variable Scoping
**Files affected**: sieve.lua (count is wrong: 0 vs 1028)
**Issue**: For-loop variable `k` shadows outer `k` variable
**Solution**: Fix variable scoping in for-loop generation

### Priority 3: Convention Tests
**Files affected**: test_convention_flat.lua, test_convention_flat_nested.lua
**Issue**: Flat convention not generating correct code
**Solution**: Debug and fix flat convention code generation

### Priority 4: loadstring/load Implementation
**Files affected**: fasta.lua
**Current**: Runtime stub returns NIL
**Solution**: Implement loadstring that compiles Lua code at runtime (complex)

### Priority 5: jit/os.require
**Files affected**: scimark.lua
**Issue**: Missing jit table, require function
**Solution**: Implement missing runtime functions

### Won't Fix: Y-combinator
**Files affected**: fixpoint_fact.lua
**Reason**: Self-application f(f) creates circular type dependencies in C++17
**Workaround**: Rewrite using explicit recursion

## Recent Fixes

### 2026-02-25
- **Descending for-loop**: Changed `<=` to `>=` when step is negative
- **And/or chain**: Added double truthy check for `(cond and x) or y` pattern
- **Math library access**: Fixed via package structure flattening (math_lib::random)
- **Package structure**: Flattened lua2cpp/lua2cpp/ to lua2cpp/
- **Old runtime removal**: Deleted old runtime files

## Running Tests

```bash
# Build all tests
cd tests/cpp
for main in *_main.cpp; do
  name=$(echo $main | sed 's/_main.cpp//')
  g++ -std=c++17 -I. -I./runtime -O2 "$main" -o "${name}_test"
done

# Run a specific test
./mandel_test 10
./spectral_norm_test 100

# Compare with LuaJIT
luajit lua/mandel.lua 10
luajit lua/spectral-norm.lua 100
```
