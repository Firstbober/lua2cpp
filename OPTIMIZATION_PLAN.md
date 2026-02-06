# Optimization Pipeline Implementation Plan

## Overview
Transform generated C++ code to minimize `luaValue` usage by:
1. Inferring types and using concrete types when possible
2. Using `std::variant` only for truly dynamic variables
3. Using `std::deque<T>` for arrays, `std::unordered_map<K,V>` for tables
4. Using `auto` for all parameters

## Architecture

### Phase 1: Type System Design

#### 1.1 Type Representation
**New file:** `lua2c/core/type_system.py`

```python
from enum import Enum
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field

class TypeKind(Enum):
    UNKNOWN = 0
    NIL = 1
    BOOLEAN = 2
    NUMBER = 3
    STRING = 4
    TABLE = 5
    FUNCTION = 6
    VARIANT = 7

@dataclass
class Type:
    kind: TypeKind
    is_constant: bool = False
    subtypes: List['Type'] = field(default_factory=list)

    def can_specialize(self) -> bool:
        return self.kind != TypeKind.UNKNOWN and self.kind != TypeKind.VARIANT

    def cpp_type(self) -> str:
        if self.kind == TypeKind.UNKNOWN:
            return "auto"
        elif self.kind == TypeKind.VARIANT:
            inner_types = [t.cpp_type() for t in self.subtypes]
            return f"std::variant<{', '.join(inner_types)}>"
        elif self.kind == TypeKind.BOOLEAN:
            return "bool"
        elif self.kind == TypeKind.NUMBER:
            return "double"
        elif self.kind == TypeKind.STRING:
            return "std::string"
        elif self.kind == TypeKind.TABLE:
            return "auto"
        elif self.kind == TypeKind.FUNCTION:
            return "auto"
        else:
            return "auto"

@dataclass
class TableTypeInfo:
    is_array: bool = False
    array_type: Optional[Type] = None
    key_type: Optional[Type] = None
    value_type: Optional[Type] = None
    has_numeric_keys: Set[int] = field(default_factory=set)
    has_string_keys: Set[str] = field(default_factory=set)
```

## Implementation Steps

### Step 1: Create Type System
- Create `lua2c/core/type_system.py`
- Define Type, TypeKind, TableTypeInfo classes

### Step 2: Implement Type Inference
- Create `lua2c/analyzers/type_inference.py`
- Implement type inference visitor
- Handle all expression and statement types

### Step 3: Extend Symbol Table
- Modify Symbol class to include inferred_type

### Step 4: Modify Expression Generator
- Remove luaValue wrappers where types are known
- Generate raw values for primitives

### Step 5: Modify Statement Generator
- Use inferred types for local variables
- Use auto for function parameters

### Step 6: Update CppEmitter
- Integrate type inference pass
- Update includes

## Expected Outcomes

Before:
```cpp
luaValue x = luaValue(42);
luaValue y = luaValue(3.14);
luaValue result = x + y;
```

After:
```cpp
double x = 42;
double y = 3.14;
auto result = x + y;
```
