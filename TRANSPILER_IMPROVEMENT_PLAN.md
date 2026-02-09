# Transpiler Improvement Plan

## Current Status
- **Passing Tests (8/12)**: simple, ack, test_array, test_assign, test_func, comparisons, spectral-norm
- **Failing Tests (4/12)**: sieve, heapsort, fixpoint-fact, binary-trees

## Phase 1 Status: ✅ COMPLETED

### What Was Done
Changed from lambda capture approach to C++17 trailing return types for function definitions.

**Changes Made**:
1. Modified `lua2c/generators/stmt_generator.py::visit_Function`
   - Removed lambda capture syntax `[=](...)`
   - Changed from `auto func(state, auto&& p1, ...)` to `luaValue func(state, luaValue p1, ...) -> luaValue`
   - Added explicit `luaValue` types for all parameters
   - Fixed body_code to use `\n` instead of " " for proper line breaks

2. Modified `lua2c/generators/stmt_generator.py::visit_LocalFunction`
   - Same changes as `visit_Function` but for local functions

**Key Decision**: Use explicit `luaValue` types instead of type inference for now. This is simpler and ensures type safety.

**Verification**: ack.lua test still passes after reversion to regular functions.

---

## Remaining Issues to Fix

### 2. Math Library Support (HIGH PRIORITY)
**Problem**: State structure doesn't include math library functions

**Affected Tests**:
- heapsort.lua uses `math.random` and `math.floor`

**Solution**:
- Add math library to state structure in `lua2c/generators/project_state_generator.py`
- Implement math functions in `runtime/l2c_runtime.hpp`
- Add functions: `random`, `floor`, `sqrt`, `abs`, etc.

**Implementation**:
```cpp
// In state structure
struct _lua_State {
    struct {
        luaValue(*random)();
        luaValue(*floor)(const luaValue&);
        luaValue(*sqrt)(const luaValue&);
        // ... more math functions
    } math;
};

// In l2c_runtime.hpp
namespace l2c {
    luaValue math_random() { return luaValue(rand()); }
    luaValue math_floor(const luaValue& v) { return luaValue(std::floor(v.as_number())); }
    luaValue math_sqrt(const luaValue& v) { return luaValue(std::sqrt(v.as_number())); }
    // ... more math functions
}
```

---

### 3. Table Indexing for Complex Types (HIGH PRIORITY)
**Problem**: Table indexing fails when table is a `luaValue` type (not `luaArray<T>`)

**Affected Tests**:
- binary-trees.lua - `(tree)[luaValue(2)]` errors because `tree` is typed as `double`

**Root Cause**:
- Type inference incorrectly identifies tables as primitive types
- When tree should be `luaValue` (a table), it's typed as `double`

**Solution**:
1. Improve type inference for table operations
   - Detect when a variable holds table operations (indexing, new_table())
   - Mark variable as table type instead of primitive

2. Generate proper indexing code
   - `luaValue t; t[1]` should use `t.as_table().get(1)`
   - Or use `t[1]` operator if `luaValue` has `operator[]` for integer keys

**Implementation**:
- Modify `lua2c/analyzers/type_inference.py` to track table operations
- Update `lua2c/generators/expr_generator.py::visit_Index` to handle table indexing

---

### 4. Function Name Conflicts (MEDIUM PRIORITY)
**Problem**: Function names can conflict with C++ keywords or special names

**Affected Tests**:
- sieve.lua - Function named `main` conflicts with C++ `main()`

**Solution**:
- Rename conflicting function names during transpilation
- Add a name mangling function: `_l2c_mangle_name()`
- Use prefix or suffix for conflicts

**Implementation**:
```python
def _mangle_name(name: str) -> str:
    """Mangle function names that conflict with C++ keywords or special names"""
    cxx_keywords = {'main', 'if', 'for', 'while', 'return', ...}
    if name.lower() in cxx_keywords:
        return f"_l2c_{name}"
    return name
```

---

### 5. Lambda Call Syntax (LOW PRIORITY)
**Problem**: Lambda calls need proper syntax in C++ (can't call lambda with multiple arguments directly)

**Affected Tests**:
- fixpoint-fact.lua - `state->le({...})` where `le` is a lambda

**Solution**:
- When calling lambdas stored as `luaValue`, convert to callable
- Use `as_function()` or similar to extract callable

**Implementation**:
- Modify `lua2c/generators/expr_generator.py::visit_Call`
- Detect when calling a lambda stored in variable
- Generate proper conversion code

---

## Priority Order

### High Priority (enables multiple tests)
1. ~~**Lambda Parameter Type Declaration** - COMPLETED ✅~~
2. **Math Library Support** - blocks heapsort
3. **Table Indexing for Complex Types** - blocks binary-trees

### Medium Priority (enables specific tests)
4. **Function Name Conflicts** - blocks sieve

### Low Priority (edge cases)
5. **Lambda Call Syntax** - blocks fixpoint-fact

---

## Implementation Approach

### Phase 1: Lambda Parameters ✅ COMPLETED
- ✅ Modified `visit_AnonymousFunction` in `expr_generator.py`
- ✅ Modified `visit_Function` and `visit_LocalFunction` in `stmt_generator.py`
- ✅ All parameters now have explicit types (defaulting to `luaValue`)
- ⚠️ Introduced new issues with lambda capture and operator overloading

### Phase 2: Math Library (PENDING)
- Add math library to state structure
- Implement functions in runtime

### Phase 3: Table Indexing (PENDING)
- Update type inference to track table operations
- Fix `visit_Index` to handle table indexing

### Phase 4: Function Name Conflicts (PENDING)
- Implement name mangling
- Apply to function definitions and calls

### Phase 5: Lambda Calls (PENDING)
- Fix lambda call syntax
- Handle conversion from `luaValue` to callable

---

## Testing Plan

After each phase, run tests to verify:
```bash
python -m pytest tests/integration/test_lua_cpp_comparison.py -v
```

Target: All 12 tests passing after all phases

---

## Notes

- Type inference system needs to be more robust for lambda capture semantics
- Consider using `std::function` with explicit signatures instead of generic lambdas
- Runtime may need additional helper functions for `luaValue` operators
- Some tests may need Lua source code adjustments if patterns are incompatible
- **Recommendation**: Reconsider lambda-style function definitions and use regular C++ functions with proper scoping

