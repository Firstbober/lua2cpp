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
| sieve | 100 8192, Count: 1028 | 100 8192, Count: 1028 | Fixed: for-loop scoping + start value extraction |
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
| k_nucleotide | pairs() runtime bug | For-in implemented, but pairs() with string keys has runtime bug |
| qt | Unknown | Needs investigation |
| regex_dna | string_lib::find missing | For-in implemented, other issues remain |
| scimark | jit table access | Missing jit runtime, require |
| test_convention_flat | ✅ FIXED | G table access now generates G["key"] |
| test_convention_flat_nested | Lambda assignment | Function reference to lambda wrapper issue |
| test_nil_basic | Unknown | Needs investigation |

### NO_CPP (no corresponding .cpp file)

| Test | Needed File | Notes |
|------|-------------|-------|
| heapsort_simple | heapsort_simple.cpp | Duplicate test? |
| n_body_simple | n_body_simple.cpp | Duplicate test? |
| spectral_norm_simple | spectral_norm_simple.cpp | Duplicate test? |

## Root Causes to Fix

### Priority 1: For-in Loops ✅ IMPLEMENTED
**Files affected**: k_nucleotide.lua, regex_dna.lua
**Location**: `lua2cpp/generators/stmt_generator.py:632-732`
**Status**: IMPLEMENTED
- `ipairs()` works correctly
- `pairs()` with integer keys works
- `pairs()` with STRING keys has a runtime bug in `lua_table.hpp:next()` - returns key=0

### Priority 2: Variable Scoping ✅ FIXED
**Files affected**: sieve.lua
**Issue**: Two bugs:
1. For-loop body used module state variable instead of local loop variable
2. C++ shadowing: `for (double x = x; ...)` used uninitialized local
**Solution**: 
1. Add loop variable to `_function_locals` before generating body
2. Extract start value to temp variable before loop declaration

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

# Compare with LuaJIT
luajit lua/mandel.lua 10
luajit lua/spectral-norm.lua 100
```

---

## Investigation Results (2026-02-25 Session 2)

### Root Causes Identified

| Test | Root Cause | Fix Type | Effort |
|------|------------|----------|--------|
| **mandel** | Code ordering - tables used before declared | Transpiler | Medium |
| **qt** | Multi-target local variables not tracked in module state | Transpiler | Medium |
| **fasta** | Wrong namespaces (`loadstring` → `l2c::loadstring`) | Transpiler | Low |
| **k_nucleotide** | 5+ issues (function refs, types, namespaces) | Mixed | High |
| **test_nil_basic** | Type inference for nil-initialized vars | Transpiler | Low |
| **test_convention_flat_nested** | Lambda wrapper incompatible with TValue | Transpiler | Medium |
| **regex_dna** | ✅ Missing `string_lib::find` - FIXED | Runtime | Done |
| **scimark** | LuaJIT-specific features (jit, FFI, require) | Won't Fix | N/A |

### Fixes Applied This Session

1. **Added `string_lib::find`** - regex_dna now has the runtime function it needs
   - Location: `tests/cpp/runtime/l2c_runtime_lua_table.hpp` line 720

### Recommended Next Steps

1. **Easy wins** (transpiler, single location):
   - Fix test_nil_basic type inference
   - Fix fasta namespace generation
   
2. **Medium fixes**:
   - Fix mandel code ordering (forward-declare tables)
   - Fix qt multi-target tracking in `_collect_module_state()`

3. **Complex/Won't fix**:
   - k_nucleotide has 5+ interrelated issues
   - scimark requires LuaJIT FFI - recommend creating Lua 5.3 compatible version
