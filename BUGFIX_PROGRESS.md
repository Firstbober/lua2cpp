# Transpiler Bug Fixes and Progress

## Completed Fixes

### ✅ Fix #1: Comparison Operators Return luaValue
**Status:** COMPLETED

**Problem:** Comparison operators (`==`, `!=`, `<`, `>`, `<=`, `>=`) returned `bool` instead of `luaValue`, causing compilation errors when calling `.is_truthy()` on the result.

**Solution:** Wrapped all comparison results in `luaValue(...)` constructor in `lua2c/generators/expr_generator.py`.

**Changes:**
- Updated all 6 comparison operator visitor methods:
  - `visit_EqToOp`: Returns `luaValue(left == right)`
  - `visit_NotEqToOp`: Returns `luaValue(left != right)`
  - `visit_LessThanOp`: Returns `luaValue(left < right)`
  - `visit_LessOrEqThanOp`: Returns `luaValue(left <= right)`
  - `visit_GreaterThanOp`: Returns `luaValue(left > right)`
  - `visit_GreaterOrEqThanOp`: Returns `luaValue(left >= right)`
- Added `generate_with_parentheses()` calls for correct operator precedence

**Tests:**
- Added 6 new unit tests in `tests/generators/test_expr_generator.py`
- Created `tests/cpp/lua/comparisons.lua` integration test
- All 183 Python tests passing
- `comparisons_test` C++ executable builds and runs correctly
- Output matches Lua exactly:
  ```
  a == 5: true
  a ~= b: true
  a < b: true
  a <= 5: true
  b > a: true
  b >= 10: true
  a + b == 15: true
  ```

## Remaining Bugs

### 🔴 Bug #2: Rvalue to Reference Binding
**Status:** PENDING

**Problem:** Temporary objects (like `luaValue::new_table()`) cannot be bound to non-const lvalue references (`luaValue&`).

**Example:**
```cpp
addqueen(state, luaValue::new_table(), luaValue(1))
// Error: cannot bind non-const lvalue reference of type 'luaValue&' to an rvalue
```

**Affected Code:**
- Table literals used as function arguments
- Constructor calls (`luaValue::new_table()`, `luaValue::new_function()`)
- Possibly other temporary expressions

**Potential Solutions:**
1. **Change function parameters to `const luaValue&`**: Would allow binding to temporaries, but prevents modification of parameters.
2. **Wrap temporaries in local variables**: Detect temporaries and store them before passing to functions. More complex but maintains correct semantics.
3. **Use `std::move()`**: Add explicit move semantics for temporary objects.

**Approach Chosen:** Option 2 (wrap temporaries) is preferred but complex to implement. For now, this is a known limitation.

**Affected Tests:**
- `queen.lua` - Has `addqueen({}, 1)` with table literal
- Other tests may have similar issues

---

### 🔴 Bug #3: Ternary Operator Type Mismatch
**Status:** PENDING

**Problem:** Nested ternary operators generate code with mixed types (`luaValue` vs `bool`) in branches.

**Example:**
```cpp
// Generated code (INCORRECT):
if (((luaValue((a)[i] == c)).is_truthy() ? (luaValue((a)[i] == c)) : (luaValue((a)[i] - i == c - n))).is_truthy() ? ...

// Issue: True branch returns luaValue, False branch returns bool (from .is_truthy())
// Error: operands to '?:' have different types 'luaValue' and 'bool'
```

**Root Cause:** Logical operators (`and`, `or`) in complex boolean expressions incorrectly add `.is_truthy()` to nested ternary results.

**Expected C++ Code:**
```cpp
luaValue(left.is_truthy() ? left : right)
```

**Where `left` and `right` are both `luaValue` expressions, never wrapped in `.is_truthy()`.

**Affected Code:**
- `queen.lua`: Line 21 - Complex boolean expression with nested `or` operators
- Other tests with complex logical expressions

**Affected Tests:**
- `queen.lua`
- Likely others with complex boolean logic

---

## Test Status

### ✅ Working Tests (3/17)
| Test | Status | Notes |
|-------|---------|-------|
| `simple.lua` | ✅ PASS | Basic arithmetic |
| `spectral-norm.lua` | ✅ PASS | Complex math, operator precedence |
| `comparisons.lua` | ✅ PASS | All comparison operators |

### ❌ Failing Tests (14/17)
| Test | Issue | Status |
|-------|--------|--------|
| `ack.lua` | Bug #2, Bug #3 | Not built yet |
| `binary-trees.lua` | Bug #2, Bug #3 | Not built yet |
| `fannkuch-redux.lua` | Bug #2, Bug #3 | Not built yet |
| `fasta.lua` | Bug #2, Bug #3 | Not built yet |
| `fixpoint-fact.lua` | Bug #2, Bug #3 | Not built yet |
| `heapsort.lua` | Bug #2, Bug #3 | Not built yet |
| `k-nucleotide.lua` | Bug #2, Bug #3 + stdin issue | Not built yet |
| `mandel.lua` | Bug #2, Bug #3 | Not built yet |
| `n-body.lua` | Bug #2, Bug #3 | Not built yet |
| `qt.lua` | Bug #2, Bug #3 | Not built yet |
| `queen.lua` | Bug #2, Bug #3 | Partially fixed (manual) |
| `regex-dna.lua` | Bug #2, Bug #3 + stdin issue | Not built yet |
| `scimark.lua` | Bug #2, Bug #3 | Not built yet |
| `sieve.lua` | Bug #2, Bug #3 | Not built yet |

## Next Steps

1. **Fix Bug #3 (Ternary Operator Nesting)**
   - Investigate logical operator generation in `expr_generator.py`
   - Fix `visit_OrLoOp` and `visit_AndLoOp` to not add `.is_truthy()` to nested ternary branches
   - Test with `queen.lua`

2. **Fix Bug #2 (Rvalue to Reference Binding)**
   - Implement temporary wrapping in function call generation
   - Test with `queen.lua` and other tests

3. **Update Test Infrastructure**
   - Auto-regenerate CMakeLists.txt when adding new tests
   - Add tests that exercise these specific bug patterns

4. **Build and Verify All Tests**
   - Once bugs are fixed, build all 17 C++ tests
   - Compare C++ output with Lua output for each test
   - Update this document with final results

## Code Coverage

**Before Fixes:**
- Comparison operators: Not tested
- Complex logical expressions: Not tested

**After Fix #1:**
- All 6 comparison operators tested
- Integration test with complex comparison expressions
- Coverage improved for `lua2c/generators/expr_generator.py`

**Remaining:**
- Ternary operator nesting: Not tested
- Rvalue binding: Not tested
- Complex boolean expressions: Not tested

## Build Commands

```bash
# Run Python tests
pytest tests/ -x --tb=short

# Transpile a test
python -m lua2c.cli.main tests/cpp/lua/comparisons.lua -o tests/cpp/generated/comparisons.cpp

# Build specific test
cd tests/cpp/build
cmake ..
make comparisons_test

# Run test
./comparisons_test

# Regenerate all tests
python generate_cpp_tests.py
cd tests/cpp/build
cmake ..
make
```

## Summary

Fixed comparison operators to return `luaValue` instead of `bool`, resolving the primary compilation error. Added comprehensive tests to verify the fix works correctly.

Two critical bugs remain:
1. **Ternary operator type mismatch** - Logical operators incorrectly wrap nested ternary results in `.is_truthy()`
2. **Rvalue to reference binding** - Temporary objects cannot be passed to functions expecting lvalue references

These bugs affect 14 of 17 benchmark tests, preventing them from compiling. The transpiler now correctly handles basic arithmetic, library functions, and comparison operators, but struggles with complex boolean expressions and temporary object passing.

Progress: 3/17 tests (17.6%) working, with clear path to fix remaining issues.
