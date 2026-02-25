# Not Fixable Tests

This document describes tests that cannot be fixed due to fundamental limitations.

---

## 1. fixpoint_fact.lua - Y-Combinator Pattern

### Error
```
error: no match for 'operator=' (operand types are 'TABLE' and '<lambda>')
```

### Root Cause
The test uses a Y-combinator pattern for anonymous recursion:
```lua
local Y = function(f)
    return function(...)
        return f(Y(f))(...)
    end
end
```

This requires self-application `f(f)` which creates circular type dependencies that cannot be resolved in C++17's static type system.

### Why It Can't Be Fixed
- C++ requires all types to be known at compile time
- The Y-combinator creates a function that returns itself, creating infinite type recursion
- Even with `std::function`, the circular dependency cannot be expressed

### Possible Workarounds
1. Rewrite the algorithm without Y-combinator (uses explicit named recursion)
2. Use a different benchmark that doesn't require anonymous recursion

---

## 2. scimark.lua - LuaJIT-Specific Features

### Error
```
error: 'jit' was not declared in this scope
error: 'require' was not declared in this scope
```

### Root Cause
The test is designed specifically for LuaJIT and uses:
- `jit.status()` - LuaJIT JIT compiler status
- `require("ffi")` - LuaJIT Foreign Function Interface
- `require("bit")` - LuaJIT bit operations library

### Why It Can't Be Fixed
- LuaJIT FFI provides low-level memory manipulation impossible in standard C++
- The JIT compiler status is specific to LuaJIT's runtime
- `require()` with dynamic module loading would need a complex module system

### Possible Workarounds
1. Create a Lua 5.3 compatible version of scimark
2. Skip this test for lua2c transpilation

---

## 3. Duplicate Tests (NO_CPP)

These tests have no `_main.cpp` file and appear to be duplicates:

| Test | Duplicate Of |
|------|--------------|
| heapsort_simple | heapsort |
| n_body_simple | n_body |
| spectral_norm_simple | spectral_norm |

### Why They Can't Be Fixed
These are not transpiler issues - the test infrastructure doesn't exist for them.

### Possible Workarounds
Create the missing `_main.cpp` files if these tests are needed.

---

## Summary

| Test | Category | Can Fix? |
|------|----------|----------|
| fixpoint_fact | C++ type system limitation | No |
| scimark | LuaJIT dependency | No |
| heapsort_simple | Missing test infrastructure | Yes (add main file) |
| n_body_simple | Missing test infrastructure | Yes (add main file) |
| spectral_norm_simple | Missing test infrastructure | Yes (add main file) |
