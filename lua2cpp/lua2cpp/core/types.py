"""Type system for Lua 5.4 to C++ transpiler

Defines TypeKind enum, Type dataclass, and ASTAnnotationStore for
attaching type information to AST nodes.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Any, Set


class TypeKind(Enum):
    """Type categories in Lua"""

    UNKNOWN = 0
    STRING = 1
    NUMBER = 2
    FUNCTION = 3
    BOOLEAN = 4
    TABLE = 5
    ANY = 6
    VARIANT = 7  # std::variant<...> for dynamic types


@dataclass
class Type:
    """Represents a type in the type system"""

    kind: TypeKind
    is_constant: bool = False
    subtypes: List['Type'] = field(default_factory=list)

    def can_specialize(self) -> bool:
        """Check if this type can use concrete C++ type"""
        return self.kind != TypeKind.UNKNOWN and self.kind != TypeKind.VARIANT

    def cpp_type(self) -> str:
        """Map TypeKind to C++ type name

        Returns:
            str: C++ type name
        """
        if self.kind == TypeKind.UNKNOWN:
            return "auto"
        elif self.kind == TypeKind.VARIANT:
            inner_types = [t.cpp_type() for t in self.subtypes]
            if not inner_types:
                return "std::variant<>"
            return f"std::variant<{', '.join(inner_types)}>"
        elif self.kind == TypeKind.BOOLEAN:
            return "bool"
        elif self.kind == TypeKind.NUMBER:
            return "double"
        elif self.kind == TypeKind.STRING:
            return "std::string"
        elif self.kind == TypeKind.TABLE:
            return "TABLE"
        elif self.kind == TypeKind.FUNCTION:
            return "auto"
        elif self.kind == TypeKind.ANY:
            return "std::variant<...>"
        else:
            return "auto"


@dataclass
class TableTypeInfo:
    """Type information for table variables

    Attributes:
        is_array: True if table is array-like
        array_type: Type of array elements (if array)
        key_type: Type of table keys (if map)
        value_type: Type of table values (if map)
        has_numeric_keys: Set of numeric keys observed
        has_string_keys: Set of string keys observed
    """
    is_array: bool = False
    array_type: Optional[Type] = None
    key_type: Optional[Type] = None
    value_type: Optional[Type] = None
    has_numeric_keys: Set[int] = field(default_factory=set)
    has_string_keys: Set[str] = field(default_factory=set)

    def finalize_array(self) -> bool:
        """Determine if table should be array based on collected info

        Returns:
            True if table should be treated as array, False otherwise
        """
        if self.has_string_keys:
            return False

        if not self.has_numeric_keys:
            return True

        max_key = max(self.has_numeric_keys)
        min_key = min(self.has_numeric_keys)

        return min_key == 1 and max_key == len(self.has_numeric_keys)


class ASTAnnotationStore:
    """Stores type and custom annotations on AST nodes"""

    @staticmethod
    def set_type(node: Any, type_obj: Type) -> None:
        """Attach type information to AST node using private namespace

        Args:
            node: AST node from luaparser
            type_obj: Type object to attach
        """
        # Use private namespace _l2c_ to avoid conflicts
        node._l2c_type = type_obj

    @staticmethod
    def get_type(node: Any) -> Optional[Type]:
        """Retrieve type information from AST node

        Args:
            node: AST node from luaparser

        Returns:
            Type object if found, None otherwise
        """
        return getattr(node, '_l2c_type', None)

    @staticmethod
    def set_annotation(node: Any, key: str, value: Any) -> None:
        """Attach custom annotation to AST node

        Args:
            node: AST node from luaparser
            key: Annotation key
            value: Annotation value
        """
        # Use private namespace _l2c_ to avoid conflicts
        setattr(node, f'_l2c_{key}', value)

    @staticmethod
    def get_annotation(node: Any, key: str) -> Any:
        """Retrieve custom annotation from AST node

        Args:
            node: AST node from luaparser
            key: Annotation key

        Returns:
            Annotation value if found, None otherwise
        """
        return getattr(node, f'_l2c_{key}', None)

    @staticmethod
    def has_annotation(node: Any, key: str) -> bool:
        """Check if AST node has specific annotation

        Args:
            node: AST node from luaparser
            key: Annotation key

        Returns:
            True if annotation exists, False otherwise
        """
        return hasattr(node, f'_l2c_{key}')
