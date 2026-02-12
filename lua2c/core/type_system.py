"""Type system for Lua2C transpiler

Defines type representations for type inference and code generation.
"""

from enum import Enum
from typing import List, Optional, Set
from dataclasses import dataclass, field


class TypeKind(Enum):
    """Type categories for Lua values"""
    UNKNOWN = 0      # Cannot be determined
    NIL = 1          # nil only
    BOOLEAN = 2      # bool only
    NUMBER = 3       # double only
    STRING = 4       # std::string only
    TABLE = 5        # std::deque<T> or std::unordered_map<K,V>
    FUNCTION = 6     # std::function<auto(...)>
    VARIANT = 7      # std::variant<...> for dynamic types


@dataclass
class Type:
    """Type information for symbols and expressions"""
    kind: TypeKind
    is_constant: bool = False
    subtypes: List['Type'] = field(default_factory=list)

    def can_specialize(self) -> bool:
        """Check if this type can use concrete C++ type"""
        return self.kind != TypeKind.UNKNOWN and self.kind != TypeKind.VARIANT

    def cpp_type(self) -> str:
        """Get C++ type name"""
        if self.kind == TypeKind.UNKNOWN:
            return "auto"
        elif self.kind == TypeKind.VARIANT:
            inner_types = [t.cpp_type() for t in self.subtypes]
            if not inner_types:
                return "ANY"
            return f"ANY({', '.join(inner_types)})"
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
        elif self.kind == TypeKind.NIL:
            return "auto"
        else:
            return "auto"


@dataclass
class TableTypeInfo:
    """Type information for table variables"""
    is_array: bool = False
    array_type: Optional[Type] = None
    key_type: Optional[Type] = None
    value_type: Optional[Type] = None
    has_numeric_keys: Set[int] = field(default_factory=set)
    has_string_keys: Set[str] = field(default_factory=set)

    def finalize_array(self) -> bool:
        """Determine if table should be array based on collected info"""
        if self.has_string_keys:
            return False

        if not self.has_numeric_keys:
            return True

        max_key = max(self.has_numeric_keys)
        min_key = min(self.has_numeric_keys)

        return min_key == 1 and max_key == len(self.has_numeric_keys)
