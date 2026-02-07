"""Centralized type query interface for call generation
Provides a single entry point for all type-related queries during
call generation, eliminating scattered type checking logic.
"""
from typing import Optional, Dict
from luaparser import astnodes
from lua2c.core.type_system import Type, TypeKind, TableTypeInfo
from lua2c.core.context import TranslationContext


class TypeQueryService:
    """Service for querying type information during code generation
    
    Consolidates all type-related queries:
    - Symbol type inference
    - Expression type inference
    - Table type information
    - Type compatibility checks
    """
    
    def __init__(self, context: TranslationContext, type_inferencer=None):
        """Initialize type query service
        
        Args:
            context: Translation context
            type_inferencer: Optional type inference engine
        """
        self._context = context
        self._type_inferencer = type_inferencer
        self._cache: Dict[str, Type] = {}
    
    def get_symbol_type(self, symbol_name: str) -> Optional[Type]:
        """Get inferred type for a symbol
        
        Args:
            symbol_name: Symbol name to query
            
        Returns:
            Type or None if unknown
        """
        if symbol_name in self._cache:
            return self._cache[symbol_name]
        
        symbol = self._context.resolve_symbol(symbol_name)
        if not symbol:
            return None
        
        inferred_type = getattr(symbol, 'inferred_type', None)
        if inferred_type:
            self._cache[symbol_name] = inferred_type
            return inferred_type
        
        return None
    
    def get_expression_type(self, expr: astnodes.Node) -> Optional[Type]:
        """Infer type for an expression
        
        Args:
            expr: AST node
            
        Returns:
            Inferred type or None
        """
        # Literal types
        if isinstance(expr, astnodes.Number):
            return Type(TypeKind.NUMBER)
        elif isinstance(expr, astnodes.String):
            return Type(TypeKind.STRING)
        elif isinstance(expr, (astnodes.TrueExpr, astnodes.FalseExpr)):
            return Type(TypeKind.BOOLEAN)
        elif isinstance(expr, astnodes.Nil):
            return Type(TypeKind.NIL)
        
        # Name references
        if isinstance(expr, astnodes.Name):
            return self.get_symbol_type(expr.id)
        
        # Binary operations
        if hasattr(expr, 'left') and hasattr(expr, 'right'):
            left_type = self.get_expression_type(expr.left)
            right_type = self.get_expression_type(expr.right)
            return self._infer_binary_op_type(left_type, right_type)
        
        # Unary operations
        if hasattr(expr, 'operand'):
            operand_type = self.get_expression_type(expr.operand)
            return operand_type
        
        # Unknown
        return None
    
    def get_table_info(self, symbol_name: str) -> Optional[TableTypeInfo]:
        """Get table type information for a symbol
        
        Args:
            symbol_name: Symbol name
            
        Returns:
            TableTypeInfo or None
        """
        # Check if it's special 'arg' array (even if not in symbol table)
        if symbol_name == "arg":
            return TableTypeInfo(is_array=True, value_type=Type(TypeKind.VARIANT))
        
        symbol = self._context.resolve_symbol(symbol_name)
        if not symbol:
            return None
        
        table_info = getattr(symbol, 'table_info', None)
        if table_info:
            return table_info
        
        return None
        
        table_info = getattr(symbol, 'table_info', None)
        if table_info:
            return table_info
        
        return None
        
        table_info = getattr(symbol, 'table_info', None)
        if table_info:
            return table_info
        
        # Check if it's special 'arg' array
        if symbol_name == "arg":
            return TableTypeInfo(is_array=True, value_type=Type(TypeKind.VARIANT))
        
        return None
    
    def needs_lua_value_wrapper(self, expr: astnodes.Node) -> bool:
        """Check if expression needs luaValue wrapper
        
        Args:
            expr: Expression to check
            
        Returns:
            True if wrapper is needed
        """
        expr_type = self.get_expression_type(expr)
        
        # Unknown or variant types need luaValue
        if not expr_type or expr_type.kind == TypeKind.UNKNOWN:
            return True
        
        # Concrete types that can be used directly
        if expr_type.kind in (TypeKind.NUMBER, TypeKind.STRING, TypeKind.BOOLEAN):
            return False
        
        return True
    
    def get_cpp_type(self, type_info: Type) -> str:
        """Get C++ type string for a Type
        
        Args:
            type_info: Type object
            
        Returns:
            C++ type string (e.g., "double", "const std::string&")
        """
        return type_info.cpp_type()
    
    def should_unwrap_lua_value(self, expr: str, target_type: Type) -> str:
        """Generate unwrapping code if needed
        
        Args:
            expr: Expression that might be wrapped in luaValue
            target_type: Target concrete type
            
        Returns:
            Expression with unwrapping if needed
        """
        if not expr.startswith("luaValue("):
            return expr
        
        # Extract inner expression
        inner = expr[9:-1]  # Remove "luaValue(" and ")"
        
        # Check if inner is a literal (no unwrapping needed)
        if inner.startswith('"'):
            return inner
        if inner.replace('.', '').replace('-', '').replace('+', '').isdigit():
            return inner
        
        # Unwrap based on target type
        if target_type.kind == TypeKind.NUMBER:
            return f"{inner}.as_number()"
        elif target_type.kind == TypeKind.STRING:
            return f"{inner}.as_string()"
        elif target_type.kind == TypeKind.BOOLEAN:
            return f"{inner}.is_truthy()"
        else:
            return inner
    
    def _infer_binary_op_type(self, left_type: Optional[Type], right_type: Optional[Type]) -> Optional[Type]:
        """Infer type for binary operation result
        
        Args:
            left_type: Left operand type
            right_type: Right operand type
            
        Returns:
            Inferred type or None
        """
        # Both numbers → number
        if (left_type and left_type.kind == TypeKind.NUMBER and
            right_type and right_type.kind == TypeKind.NUMBER):
            return Type(TypeKind.NUMBER)
        
        # At least one unknown → variant (not unknown, as we expect a value)
        if not left_type or not right_type:
            return Type(TypeKind.VARIANT)
        
        return Type(TypeKind.VARIANT)
    
    def clear_cache(self):
        """Clear type cache (useful for testing)"""
        self._cache.clear()
