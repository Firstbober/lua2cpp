"""Type conversion utilities for Lua2C transpiler

Provides helper functions for converting between concrete types and luaValue.
Used in code generation to add appropriate type conversions.
"""

from typing import Optional
from lua2c.core.type_system import Type, TypeKind


class TypeConverter:
    """Handles type conversion for C++ code generation"""

    @staticmethod
    def needs_conversion(from_type: Type, to_type: Type) -> bool:
        """Check if conversion is needed between two types

        Args:
            from_type: Source type
            to_type: Target type

        Returns:
            True if conversion is needed
        """
        if from_type.kind == to_type.kind:
            return False

        # luaValue to concrete type needs conversion
        if from_type.kind in (TypeKind.UNKNOWN, TypeKind.VARIANT):
            return to_type.can_specialize()

        # Concrete type to luaValue needs conversion
        if to_type.kind in (TypeKind.UNKNOWN, TypeKind.VARIANT):
            return from_type.can_specialize()

        return False

    @staticmethod
    def wrap_in_lua_value(expr: str, type_info: Type) -> str:
        """Wrap an expression in luaValue constructor

        Args:
            expr: C++ expression string
            type_info: Type of the expression

        Returns:
            Wrapped expression
        """
        if type_info.kind == TypeKind.NUMBER:
            return f"luaValue({expr})"
        elif type_info.kind == TypeKind.STRING:
            return f"luaValue({expr})"
        elif type_info.kind == TypeKind.BOOLEAN:
            return f"luaValue({expr})"
        elif type_info.kind == TypeKind.NIL:
            return "luaValue()"
        else:
            # Already luaValue or unknown
            return expr

    @staticmethod
    def unwrap_from_lua_value(expr: str, target_type: Type) -> str:
        """Extract concrete type from luaValue expression

        Args:
            expr: luaValue C++ expression string
            target_type: Target concrete type

        Returns:
            Expression with type extraction
        """
        if target_type.kind == TypeKind.NUMBER:
            return f"{expr}.as_number()"
        elif target_type.kind == TypeKind.STRING:
            return f"{expr}.as_string()"
        elif target_type.kind == TypeKind.BOOLEAN:
            return f"{expr}.is_truthy()"
        elif target_type.kind == TypeKind.TABLE:
            # For tables, we might need special handling
            return expr
        else:
            return expr

    @staticmethod
    def generate_type_conversion(expr: str, from_type: Type, to_type: Type) -> str:
        """Generate type conversion between two types

        Args:
            expr: Source expression string
            from_type: Source type
            to_type: Target type

        Returns:
            Converted expression string
        """
        if not TypeConverter.needs_conversion(from_type, to_type):
            return expr

        # luaValue to concrete type
        if from_type.kind in (TypeKind.UNKNOWN, TypeKind.VARIANT):
            return TypeConverter.unwrap_from_lua_value(expr, to_type)

        # Concrete type to luaValue
        if to_type.kind in (TypeKind.UNKNOWN, TypeKind.VARIANT):
            return TypeConverter.wrap_in_lua_value(expr, from_type)

        # Concrete type to different concrete type (rare, but handle it)
        # Use luaValue as intermediate
        wrapped = TypeConverter.wrap_in_lua_value(expr, from_type)
        return TypeConverter.unwrap_from_lua_value(wrapped, to_type)

    @staticmethod
    def get_cpp_value_type(type_info: Type) -> str:
        """Get C++ type name for value declarations

        Args:
            type_info: Type information

        Returns:
            C++ type string
        """
        return type_info.cpp_type()

    @staticmethod
    def is_lua_value_type(type_info: Type) -> bool:
        """Check if type is luaValue

        Args:
            type_info: Type to check

        Returns:
            True if type is luaValue
        """
        return type_info.kind == TypeKind.UNKNOWN or type_info.kind == TypeKind.VARIANT
