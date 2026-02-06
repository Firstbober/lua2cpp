# Lua2C++ Migration Plan - COMPLETED ✅

## Overview

**Status: COMPLETED** - All Phase 1 (Transpiler Modifications) tasks completed successfully.

### What Was Done:
- ✅ Updated `expr_generator.py` to generate C++ operators instead of L2C_* macros
- ✅ Updated `stmt_generator.py` for C++ syntax (is_truthy, etc.)
- ✅ Updated `decl_generator.py` to generate C++ includes and declarations
- ✅ Renamed `c_emitter.py` → `cpp_emitter.py` and updated for C++ generation
- ✅ Updated `cli/main.py` to use CppEmitter
- ✅ Updated all tests for C++ output expectations
- ✅ All 172 tests passing (100%)
- ✅ Updated README.md and documentation

### Test Results:
```
============================= 172 passed in 0.28s ==============================
```

### Example Generated C++ Code:

**Input Lua:**
```lua
local x = 42
print(x)
```

**Output C++:**
```cpp
// Auto-generated from test.lua
// Lua2C Transpiler

#include "lua_value.hpp"
#include "lua_state.hpp"
#include "lua_table.hpp"
#include <vector>
#include <string>

// String pool
static const char* string_pool[] = {nullptr};

// Module export
luaValue _l2c__test_export(luaState* state) {
    luaValue x = luaValue(42);
    (state->get_global("print"))({x});
}
```

## Overview

Migrating the Lua2C transpiler from C to C++ output to leverage:
- Operator overloading for natural Lua syntax in generated code
- VTable-based runtime (virtual functions in C++)
- RAII for garbage collection
- Type safety
- C++ standard library for string handling

## Key Design Decisions

### Why C++ (Not C)?

1. **Operator Overloading** - Enables natural syntax:
   ```cpp
   // Instead of: L2C_BINOP(a, L2C_OP_ADD, b)
   // We get:     a + b
   ```

2. **VTable-Based Runtime** - C++ virtual functions are perfect for:
   ```cpp
   class luaState {
       virtual luaValue get_global(const std::string& name) = 0;
       virtual void set_global(const std::string& name, const luaValue& value) = 0;
   };
   ```

3. **RAII Garbage Collection** - Automatic cleanup via destructors

4. **Custom Runtime** - No C ABI compatibility needed (full C++ freedom)

## Phase 1: Transpiler Modifications (Step 1)

### 1.1 Expression Generator Updates

**File:** `lua2c/generators/expr_generator.py`

#### Changes Required:

| Current C Output | New C++ Output | Method |
|------------------|----------------|--------|
| `L2C_NUMBER_INT(42)` | `luaValue(42)` | `visit_Number` |
| `L2C_STRING_LITERAL(idx)` | `luaValue(string_pool[idx])` | `visit_String` |
| `L2C_NIL` | `luaValue()` | `visit_Nil` |
| `L2C_TRUE` | `luaValue(true)` | `visit_TrueExpr` |
| `L2C_FALSE` | `luaValue(false)` | `visit_FalseExpr` |
| `L2C_BINOP(a, L2C_OP_ADD, b)` | `a + b` | `visit_AddOp`, `visit_SubOp`, etc. |
| `L2C_UNOP(L2C_OP_NEG, a)` | `-a` | `visit_UMinusOp` |
| `L2C_GET_GLOBAL("foo")` | `state->get_global("foo")` | `visit_Name` |
| `L2C_CALL(func, n, args)` | `func({args})` | `visit_Call` |
| `L2C_INVOKE(obj, method, n, args)` | `obj->method({args})` | `visit_Invoke` |
| `L2C_GET_TABLE(table, key)` | `table[key]` | `visit_Index`, `visit_Field` |
| `L2C_NEW_TABLE()` | `luaValue::new_table()` | `visit_Table` |
| `L2C_NEW_ANON_FUNCTION()` | `luaValue::new_closure(...)` | `visit_AnonymousFunction` |

#### Special Cases:

**Short-Circuit Operators:**
```lua
-- Lua
local x = a and b  -- Only evaluate b if a is truthy
local y = c or d   -- Only evaluate d if c is falsy
```

```cpp
// Generated C++
luaValue x = a.is_truthy() ? b : a;
luaValue y = c.is_truthy() ? c : d;
```

**Method Calls (Colon Syntax):**
```lua
-- Lua
obj:method(arg1, arg2)
```

```cpp
// Generated C++
obj[L"method"]({obj, arg1, arg2})
```

### 1.2 Statement Generator Updates

**File:** `lua2c/generators/stmt_generator.py`

#### Changes Required:

| Statement Type | Current C Output | New C++ Output |
|----------------|------------------|----------------|
| Variable declaration | `luaValue x = value;` | Same |
| Assignment | `x = value;` | Same |
| Function signature | `luaValue func(luaState* L, luaValue a)` | Same |
| Return | `return value;` | Same |
| Return multiple | `return count, &((luaValue[]){...})` | `std::vector<luaValue>({...})` |
| If statement | `if (l2c_is_truthy(L, cond))` | `if (cond.is_truthy())` |
| While loop | `while (l2c_is_truthy(L, test))` | `while (test.is_truthy())` |
| For loop | `for (luaValue i = start; l2c_is_truthy(l2c_lt(i, stop)); ...)` | `for (luaValue i = start; (i < stop).is_truthy(); ...)` |

### 1.3 Declaration Generator Updates

**File:** `lua2c/generators/decl_generator.py`

#### Changes Required:

**Includes:**
```cpp
#include "lua_value.hpp"
#include "lua_state.hpp"
#include "lua_table.hpp"
#include <vector>
#include <string>
```

**String Pool:**
```cpp
static const char* string_pool[] = {
    "string1",  // 0
    "string2",  // 1
    NULL
};
```

**Forward Declarations:**
```cpp
static luaValue add(luaState* state, luaValue a, luaValue b);
```

### 1.4 C++ Emitter Creation

**File:** `lua2c/generators/cpp_emitter.py` (rename from `c_emitter.py`)

**New Features:**
- Generate `.cpp` extension for output files
- Include C++ standard library headers
- Use C++-specific macros and conventions

### 1.5 CLI Updates

**File:** `lua2c/cli/main.py`

#### Changes:
- Import `CppEmitter` instead of `CEmitter`
- Output files should use `.cpp` extension
- Update documentation to reflect C++ output

## Phase 2: Runtime C++ Library (Step 2 - Future)

### 2.1 luaValue Class

**File:** `runtime/lua_value.hpp`

```cpp
#pragma once
#include <string>
#include <vector>
#include <memory>

class luaState;
class luaTable;

enum class LuaType {
    NIL, BOOLEAN, NUMBER, STRING, TABLE, FUNCTION, USERDATA, THREAD
};

class luaValue {
public:
    // Constructors
    luaValue();
    luaValue(int v);
    luaValue(double v);
    luaValue(const std::string& s);
    luaValue(const char* s);
    luaValue(bool b);
    luaValue(std::shared_ptr<luaTable> t);
    
    // Type checking
    LuaType get_type() const;
    bool is_nil() const;
    bool is_truthy() const;
    
    // Operators (metamethod dispatch)
    luaValue operator+(const luaValue& other) const;
    luaValue operator-(const luaValue& other) const;
    luaValue operator*(const luaValue& other) const;
    luaValue operator/(const luaValue& other) const;
    luaValue operator==(const luaValue& other) const;
    luaValue operator!=(const luaValue& other) const;
    luaValue operator<(const luaValue& other) const;
    luaValue operator<=(const luaValue& other) const;
    luaValue operator>(const luaValue& other) const;
    luaValue operator>=(const luaValue& other) const;
    luaValue operator[](const luaValue& key) const;  // Table indexing
    luaValue operator()(const std::vector<luaValue>& args) const;  // Function call
    luaValue operator-() const;  // Unary minus
    luaValue operator!() const;  // Unary not
    
    // Helper methods
    static luaValue new_table();
    static luaValue new_closure(luaValue (*func)(luaState*, std::vector<luaValue>));
    
private:
    LuaType type;
    union {
        bool boolean;
        double number;
        std::string string;
        std::shared_ptr<luaTable> table;
        luaValue (*c_function)(luaState*, std::vector<luaValue>);
    } value;
};
```

### 2.2 luaState VTable Class

**File:** `runtime/lua_state.hpp`

```cpp
#pragma once
#include <string>
#include <memory>

class luaValue;
class luaTable;

// Abstract VTable interface
class luaState {
public:
    virtual ~luaState() = default;
    
    // Global table access
    virtual luaValue get_global(const std::string& name) = 0;
    virtual void set_global(const std::string& name, const luaValue& value) = 0;
    
    // Metatable operations
    virtual luaValue getmetatable(const luaValue& obj) = 0;
    virtual void setmetatable(const luaValue& obj, const luaValue& mt) = 0;
    
    // Registry
    virtual luaValue get_registry(const std::string& key) = 0;
    virtual void set_registry(const std::string& key, const luaValue& value) = 0;
    
    // Error handling
    virtual void error(const std::string& message) = 0;
    
    // Garbage collection
    virtual void collectgarbage(const std::string& option, const luaValue& arg) = 0;
    
protected:
    luaState() = default;
};
```

### 2.3 luaTable Class with Metamethods

**File:** `runtime/lua_table.hpp`

```cpp
#pragma once
#include <unordered_map>
#include <vector>
#include <memory>
#include "lua_value.hpp"

class luaTable {
public:
    luaTable();
    ~luaTable();
    
    // Array part (integer keys 1..n)
    luaValue get_array(int index);
    void set_array(int index, const luaValue& value);
    
    // Hash part (other keys)
    luaValue get_hash(const luaValue& key);
    void set_hash(const luaValue& key, const luaValue& value);
    
    // Combined access with metamethod dispatch
    luaValue get(const luaValue& key) const;
    void set(const luaValue& key, const luaValue& value);
    
    // Length operator
    int length() const;
    
    // Metatable
    std::shared_ptr<luaTable> getmetatable() const;
    void setmetatable(std::shared_ptr<luaTable> mt);
    
private:
    std::vector<luaValue> array_part;
    std::unordered_map<int, luaValue> hash_part_int;
    std::unordered_map<std::string, luaValue> hash_part_str;
    std::shared_ptr<luaTable> metatable;
};
```

## File Modifications Summary

### Files to Modify (5 core files):
1. ✅ Update `.opencode/plans/lua2c_transpiler.md` - Add C++ migration plan
2. ⏳ `lua2c/generators/expr_generator.py` - Replace L2C_* macros with C++ operators
3. ⏳ `lua2c/generators/stmt_generator.py` - Update for C++ syntax
4. ⏳ `lua2c/generators/decl_generator.py` - Change includes, type declarations
5. ⏳ `lua2c/generators/c_emitter.py` → `lua2c/generators/cpp_emitter.py` - Rename and update
6. ⏳ `lua2c/cli/main.py` - Use CppEmitter instead of CEmitter

### Files to Create (7 runtime files - Step 2):
1. `runtime/lua_value.hpp` - luaValue class with operator overloading
2. `runtime/lua_value.cpp` - Implement luaValue methods
3. `runtime/lua_state.hpp` - VTable-based luaState interface
4. `runtime/lua_state.cpp` - Implement default luaState
5. `runtime/lua_table.hpp` - Table class with metamethod dispatch
6. `runtime/lua_table.cpp` - Implement luaTable methods
7. `runtime/closure.hpp/cpp` - Closure support
8. `runtime/gc.hpp/cpp` - Garbage collector (RAII-based)
9. `runtime/error.hpp/cpp` - Exception-based error handling
10. `runtime/module_loader.hpp/cpp` - Module registry

## Testing Strategy

### 1. Update Existing Tests
All existing tests in `tests/generators/` must be updated to expect C++ output instead of C.

### 2. Add C++-Specific Tests
New tests for:
- Operator overloading syntax
- Short-circuit evaluation
- Method call syntax
- String pool usage with C++ strings

### 3. Integration Tests
Test with actual Lua files to ensure generated C++ code is syntactically correct.

## Implementation Order

### Step 1 (Current Phase):
1. ✅ Update plan documentation
2. ⏳ Modify `expr_generator.py`
3. ⏳ Modify `stmt_generator.py`
4. ⏳ Modify `decl_generator.py`
5. ⏳ Rename and update `c_emitter.py` → `cpp_emitter.py`
6. ⏳ Update `cli/main.py`
7. ⏳ Update all tests
8. ⏳ Run tests to verify C++ generation

### Step 2 (Future):
1. Create `runtime/lua_value.hpp`
2. Create `runtime/lua_state.hpp`
3. Create `runtime/lua_table.hpp`
4. Implement runtime classes
5. Test with real Lua code

## Generated Code Examples

### Example 1: Simple Addition

**Input Lua:**
```lua
local function add(a, b)
  return a + b
end
print(add(5, 7))
```

**Old C Output:**
```c
luaValue add(luaState* state, luaValue a, luaValue b) {
    return 1, &((luaValue[]){L2C_BINOP(a, L2C_OP_ADD, b)});
}
luaValue _l2c__test_file_export(luaState* state) {
    L2C_CALL(L2C_GET_GLOBAL("print"), 1, &((luaValue[]){L2C_CALL(L2C_GET_GLOBAL("add"), 2, &((luaValue[]){L2C_NUMBER_INT(5), L2C_NUMBER_INT(7)}))}));
}
```

**New C++ Output:**
```cpp
luaValue add(luaState* state, luaValue a, luaValue b) {
    return a + b;
}
luaValue _l2c__test_file_export(luaState* state) {
    state->get_global("print")({add(state, luaValue(5), luaValue(7))});
}
```

### Example 2: Table Operations

**Input Lua:**
```lua
local t = {x = 10, y = 20}
print(t.x, t.y)
```

**Old C Output:**
```c
luaValue t = L2C_NEW_TABLE();
L2C_SET_TABLE(state, t, L2C_STRING_LITERAL(0), L2C_NUMBER_INT(10));
L2C_SET_TABLE(state, t, L2C_STRING_LITERAL(1), L2C_NUMBER_INT(20));
L2C_CALL(L2C_GET_GLOBAL("print"), 2, &((luaValue[]){L2C_GET_TABLE(t, L2C_STRING_LITERAL(0)), L2C_GET_TABLE(t, L2C_STRING_LITERAL(1))}));
```

**New C++ Output:**
```cpp
luaValue t = luaValue::new_table();
t["x"] = luaValue(10);
t["y"] = luaValue(20);
state->get_global("print")({t["x"], t["y"]});
}
```

### Example 3: Short-Circuit Operators

**Input Lua:**
```lua
local a = false
local b = 42
local x = a and b
local c = "hello"
local d = nil
local y = c or d
```

**Old C Output:**
```c
luaValue a = L2C_FALSE;
luaValue b = L2C_NUMBER_INT(42);
luaValue x = L2C_BINOP(a, L2C_OP_AND, b);
luaValue c = L2C_STRING_LITERAL(0);
luaValue d = L2C_NIL;
luaValue y = L2C_BINOP(c, L2C_OP_OR, d);
```

**New C++ Output:**
```cpp
luaValue a = luaValue(false);
luaValue b = luaValue(42);
luaValue x = a.is_truthy() ? b : a;
luaValue c = luaValue("hello");
luaValue d = luaValue();
luaValue y = c.is_truthy() ? c : d;
```

## Benefits Summary

| Aspect | C Approach | C++ Approach |
|--------|------------|--------------|
| Readability | Verbose macros | Natural operators |
| Maintainability | Hard to debug | Standard C++ |
| Runtime Design | Manual VTables | Virtual functions |
| Memory Management | Manual tracking | RAII |
| Type Safety | void* everywhere | Strong typing |
| Performance | Fast | Fast (with -O3) |
| Compilation | Faster | Slightly slower |

## Notes

- **No C ABI Compatibility**: We don't need extern "C" since we're doing a full custom runtime
- **Exceptions**: Can use `-fno-exceptions` for performance if needed
- **RTTI**: Can use `-fno-rtti` to disable runtime type information
- **Precompiled Headers**: Use to speed up compilation of runtime headers
- **Naming Convention**: Keep the same `_l2c__<dir>__<file>_<method>` pattern for C++ functions

## Next Steps

1. ✅ Update plan documentation (DONE)
2. ⏳ Start modifying `expr_generator.py` to generate C++ operators
3. ⏳ Run tests after each file modification to catch issues early
4. ⏳ Create runtime C++ headers after transpiler is fully updated
