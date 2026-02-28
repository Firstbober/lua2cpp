# Lua Transpilation Progress

**Last Updated**: 2026-02-28

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
| PASS | 32 |
| BUILD_FAIL | 3 |
| **Total** | **35** |

## Detailed Test Results

### PASSING (builds + runs correctly)

| Test | Notes |
|------|-------|
| simple | Basic test |
| spectral_norm | Numeric computation |
| mandel | Uses metamethods (__add, __mul) |
| binary_trees | Recursive, tables |
| n_body | Tables, io.write |
| heapsort | Uses math.random, math.floor |
| sieve | For-loop scoping + start value extraction |
| ack | Recursive function |
| comparisons | Comparison operators |
| fannkuch_redux | Uses goto (limited) |
| queen | Backtracking |
| **qt** | **Multi-return 4 values - FIXED** |
| regex_dna | String operations |
| test_array | Array operations |
| test_assign | Assignment |
| test_func | Functions |
| test_concat_basic | String concat |
| test_concat_chain | Chained concat |
| test_concat_in_call | Concat in function call |
| test_combined_nil_concat | Nil + concat |
| test_convention_namespace | Namespace convention |
| test_convention_table | Table convention |
| test_convention_flat | Flat convention |
| test_convention_flat_nested | Flat nested convention |
| test_modop_basic | Modulo operator |
| test_modop_in_expr | Modulo in expression |
| test_nil_basic | Nil type inference |
| test_nil_table | Nil in table |
| test_type_inference | Type inference |
| test_ulnotop_basic | Unary not operator |
| test_ulnotop_in_call | Unary not in call |
| k_nucleotide | pairs()/ipairs() iteration |

### BUILD_FAIL (compilation errors)

| Test | Error | Root Cause | Status |
|------|-------|------------|--------|
| fasta | Type conversion | `string_lib::byte` expects `const char*`, gets `TableSlotProxy` | Medium |
| fixpoint_fact | Y-combinator | Self-application f(f) creates circular type dependencies | **Won't Fix** |
| scimark | LuaJIT-specific | Missing `os_lib::clock`, jit table, require | **Won't Fix** |

## Root Causes to Fix

### Priority 1: Multi-Return Support ✅ FIXED (2026-02-28)
**Files affected**: qt.lua (and any Lua code using 3+ return values)
**Location**: `lua2cpp/generators/stmt_generator.py`
**Status**: FIXED
- `has_multi_return` now detects 3+ return values
- `visit_Return` generates nested `multi_return()` for 3+ values
- `visit_LocalAssign` handles N-target multi-return unpacking
- `visit_Assign` handles multi-return unpacking in re-assignments
- Implicit `return NIL;` added for non-void functions (excluding auto)

### Priority 2: For-in Loops ✅ IMPLEMENTED
**Files affected**: k_nucleotide.lua, regex_dna.lua
**Location**: `lua2cpp/generators/stmt_generator.py:785-893`
**Status**: IMPLEMENTED
- `ipairs()` works correctly
- `pairs()` with integer keys works
- `pairs()` with STRING keys works

### Priority 3: Variable Scoping ✅ FIXED
**Files affected**: sieve.lua
**Issue**: Two bugs:
1. For-loop body used module state variable instead of local loop variable
2. C++ shadowing: `for (double x = x; ...)` used uninitialized local
**Solution**: 
1. Add loop variable to `_function_locals` before generating body
2. Extract start value to temp variable before loop declaration

### Won't Fix
- **fixpoint_fact**: Y-combinator pattern - self-application creates circular types in C++17
- **scimark**: LuaJIT-specific features (jit, FFI, require)

## Recent Fixes

### 2026-02-28
- **qt.lua multi-return**: Fixed 4-value return/assignment
  - `has_multi_return`: Changed `== 2` to `>= 2` (lines 488, 714)
  - `visit_Return`: Added nested `multi_return()` for 3+ values (lines 319-326)
  - `visit_LocalAssign`: Multi-return check moved to BEGINNING, handles N targets (lines 145-157)
  - `visit_Assign`: Multi-return unpacking for re-assignments (lines 259-271)
  - Implicit `return NIL;` for non-void, non-auto functions (lines 546, 762)
  - Commit: `2ce0bfa fix(transpiler): support multi-return with 3+ values`

### 2026-02-25 (Session 2)
- **For-in loops**: Implemented `visit_Forin()` with pairs()/ipairs() support
- **For-loop scoping**: Loop variable now properly scoped (added to _function_locals)
- **For-loop shadowing**: Start value extracted to temp variable to avoid C++ shadowing
- **G table access**: Fixed `_generate_g_table_access()` to generate `G["key"]` not `G"key"`
- **Runtime files**: Created `globals.hpp` and `love_mock.hpp` for convention tests
- **test_convention_flat**: Now builds successfully

### 2026-02-25 (Session 1)
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
./qt_test_bin

# Compare with LuaJIT
luajit lua/mandel.lua 10
luajit lua/spectral-norm.lua 100
```

---

## Key Commits

```
2ce0bfa fix(transpiler): support multi-return with 3+ values
3ea8931 fix(transpiler): multiple fixes for build failures
a58dd04 fix(transpiler): add l2c:: prefix for global Lua functions
```
