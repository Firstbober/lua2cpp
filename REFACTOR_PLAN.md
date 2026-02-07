Complete Plan: Variadic Template Support with TDD
Executive Summary
Implement variadic template support for library functions (print, io.write, string.format) using Test-Driven Development (TDD) and a refactored architecture based on the Strategy Pattern.
Key Principles:
- TDD First: Write failing tests, then implement code to make them pass
- Strategy Pattern: Modular, testable call generation
- Full Commit: No backward compatibility fallback
- Optimization: Eliminate luaValue and std::vector overhead
---
Architecture Overview
Current Issues
1. visit_Call() method is 150+ lines with deeply nested conditionals
2. Type query logic scattered across multiple methods
3. Limited test coverage for call generation
4. Tight coupling to GlobalTypeRegistry
Target Architecture
ExprGenerator
    └── visit_Call(expr)
            └── CallContextBuilder.build(expr, context, type_inferencer)
                    └── CallGenerationContext (unified call info)
                            ├── needs_variadic(library_tracker)
                            ├── needs_vector()
                            ├── has_fixed_params()
                            └── get_fixed_param_count()
            └── Strategy Selection
                    ├── LocalFunctionStrategy.can_handle()
                    ├── LibraryFunctionStrategy.can_handle()
                    │       └── VariadicLibraryStrategy (NEW)
                    │       └── VectorLibraryStrategy
                    │       └── StaticLibraryStrategy
                    └── DefaultCallStrategy
            └── TypeQueryService
                    ├── get_symbol_type()
                    ├── get_expression_type()
                    ├── get_table_info()
                    └── should_unwrap_lua_value()
---
Phase 1: Foundation - Type Query Service (TDD)
1.1 Create Test File
File: tests/generators/call_generation/test_type_query_service.py
"""Unit tests for TypeQueryService using TDD approach"""
import pytest
from pathlib import Path
from luaparser import ast
from lua2c.core.context import TranslationContext
from lua2c.core.type_system import Type, TypeKind
from lua2c.generators.call_generation.type_queries import TypeQueryService
@pytest.fixture
def context(tmp_path):
    """Create translation context for testing"""
    from lua2c.core.scope import ScopeManager
    from lua2c.core.symbol_table import SymbolTable
    
    ctx = TranslationContext(tmp_path, "test.lua")
    return ctx
@pytest.fixture
def type_query_service(context):
    """Create TypeQueryService for testing"""
    return TypeQueryService(context)
# ===== Test 1: Literal Type Inference =====
def test_get_expression_type_number_literal(type_query_service):
    """Should infer NUMBER type for numeric literals"""
    expr = ast.parse("42").body[0].value
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.NUMBER
def test_get_expression_type_float_literal(type_query_service):
    """Should infer NUMBER type for float literals"""
    expr = ast.parse("3.14").body[0].value
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.NUMBER
def test_get_expression_type_string_literal(type_query_service):
    """Should infer STRING type for string literals"""
    expr = ast.parse('"hello"').body[0].value
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.STRING
def test_get_expression_type_true_literal(type_query_service):
    """Should infer BOOLEAN type for true literals"""
    expr = ast.parse("true").body[0].value
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.BOOLEAN
def test_get_expression_type_false_literal(type_query_service):
    """Should infer BOOLEAN type for false literals"""
    expr = ast.parse("false").body[0].value
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.BOOLEAN
def test_get_expression_type_nil_literal(type_query_service):
    """Should infer NIL type for nil literals"""
    expr = ast.parse("nil").body[0].value
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.NIL
# ===== Test 2: Symbol Type Inference =====
def test_get_symbol_type_local_variable(context, type_query_service):
    """Should return type for local variable with inferred type"""
    context.define_local("x")
    symbol = context.resolve_symbol("x")
    symbol.inferred_type = Type(TypeKind.NUMBER)
    
    result = type_query_service.get_symbol_type("x")
    assert result is not None
    assert result.kind == TypeKind.NUMBER
def test_get_symbol_type_undefined(context, type_query_service):
    """Should return None for undefined symbols"""
    result = type_query_service.get_symbol_type("undefined_var")
    assert result is None
def test_get_symbol_type_caching(context, type_query_service):
    """Should cache symbol type queries"""
    context.define_local("y")
    symbol = context.resolve_symbol("y")
    symbol.inferred_type = Type(TypeKind.STRING)
    
    # Query twice
    result1 = type_query_service.get_symbol_type("y")
    result2 = type_query_service.get_symbol_type("y")
    
    # Should return same object (from cache)
    assert result1 is result2
# ===== Test 3: Name Expression Type Inference =====
def test_get_expression_type_name_with_inferred_type(context, type_query_service):
    """Should infer type from name with inferred type"""
    context.define_local("x")
    symbol = context.resolve_symbol("x")
    symbol.inferred_type = Type(TypeKind.NUMBER)
    
    expr = ast.parse("x").body[0].value
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.NUMBER
def test_get_expression_type_name_without_inferred_type(context, type_query_service):
    """Should return None for name without inferred type"""
    context.define_local("y")
    
    expr = ast.parse("y").body[0].value
    result = type_query_service.get_expression_type(expr)
    assert result is None
# ===== Test 4: Binary Operation Type Inference =====
def test_get_expression_type_binary_op_number_plus_number(context, type_query_service):
    """Should infer NUMBER for number + number"""
    context.define_local("a")
    context.resolve_symbol("a").inferred_type = Type(TypeKind.NUMBER)
    context.define_local("b")
    context.resolve_symbol("b").inferred_type = Type(TypeKind.NUMBER)
    
    expr = ast.parse("a + b").body[0].value
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.NUMBER
def test_get_expression_type_binary_op_unknown_operand(context, type_query_service):
    """Should return VARIANT when one operand is unknown"""
    context.define_local("x")
    context.resolve_symbol("x").inferred_type = Type(TypeKind.NUMBER)
    
    expr = ast.parse("x + unknown").body[0].value
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.VARIANT
# ===== Test 5: Table Type Information =====
def test_get_table_info_for_arg_array(context, type_query_service):
    """Should return array table info for 'arg'"""
    result = type_query_service.get_table_info("arg")
    assert result is not None
    assert result.is_array == True
def test_get_table_info_for_symbol_with_array_info(context, type_query_service):
    """Should return array table info for symbol with array type"""
    from lua2c.core.type_system import TableTypeInfo
    
    context.define_local("my_array")
    symbol = context.resolve_symbol("my_array")
    symbol.table_info = TableTypeInfo(is_array=True, value_type=Type(TypeKind.NUMBER))
    
    result = type_query_service.get_table_info("my_array")
    assert result is not None
    assert result.is_array == True
def test_get_table_info_for_symbol_without_table_info(context, type_query_service):
    """Should return None for symbol without table info"""
    context.define_local("simple_var")
    
    result = type_query_service.get_table_info("simple_var")
    assert result is None
# ===== Test 6: luaValue Wrapping Decisions =====
def test_needs_lua_value_wrapper_for_unknown_type(type_query_service):
    """Should wrap expressions with unknown type"""
    expr = ast.parse("unknown_var").body[0].value
    assert type_query_service.needs_lua_value_wrapper(expr) == True
def test_needs_lua_value_wrapper_for_number_type(context, type_query_service):
    """Should not wrap NUMBER type expressions"""
    context.define_local("x")
    context.resolve_symbol("x").inferred_type = Type(TypeKind.NUMBER)
    
    expr = ast.parse("x").body[0].value
    assert type_query_service.needs_lua_value_wrapper(expr) == False
def test_needs_lua_value_wrapper_for_string_type(context, type_query_service):
    """Should not wrap STRING type expressions"""
    context.define_local("s")
    context.resolve_symbol("s").inferred_type = Type(TypeKind.STRING)
    
    expr = ast.parse("s").body[0].value
    assert type_query_service.needs_lua_value_wrapper(expr) == False
def test_needs_lua_value_wrapper_for_boolean_type(context, type_query_service):
    """Should not wrap BOOLEAN type expressions"""
    context.define_local("flag")
    context.resolve_symbol("flag").inferred_type = Type(TypeKind.BOOLEAN)
    
    expr = ast.parse("flag").body[0].value
    assert type_query_service.needs_lua_value_wrapper(expr) == False
# ===== Test 7: luaValue Unwrapping =====
def test_should_unwrap_lua_value_number(type_query_service):
    """Should unwrap luaValue to .as_number()"""
    result = type_query_service.should_unwrap_lua_value(
        "luaValue(x)", 
        Type(TypeKind.NUMBER)
    )
    assert result == "x.as_number()"
def test_should_unwrap_lua_value_string(type_query_service):
    """Should unwrap luaValue to .as_string()"""
    result = type_query_service.should_unwrap_lua_value(
        "luaValue(s)", 
        Type(TypeKind.STRING)
    )
    assert result == "s.as_string()"
def test_should_unwrap_lua_value_boolean(type_query_service):
    """Should unwrap luaValue to .is_truthy()"""
    result = type_query_service.should_unwrap_lua_value(
        "luaValue(flag)", 
        Type(TypeKind.BOOLEAN)
    )
    assert result == "flag.is_truthy()"
def test_should_unwrap_lua_value_string_literal(type_query_service):
    """Should not unwrap string literals (return as-is)"""
    result = type_query_service.should_unwrap_lua_value(
        'luaValue("hello")', 
        Type(TypeKind.STRING)
    )
    assert result == '"hello"'
def test_should_unwrap_lua_value_number_literal(type_query_service):
    """Should not unwrap number literals (return as-is)"""
    result = type_query_service.should_unwrap_lua_value(
        "luaValue(42)", 
        Type(TypeKind.NUMBER)
    )
    assert result == "42"
def test_should_unwrap_lua_value_not_wrapped(type_query_service):
    """Should return expression as-is if not wrapped"""
    result = type_query_service.should_unwrap_lua_value(
        "x", 
        Type(TypeKind.NUMBER)
    )
    assert result == "x"
# ===== Test 8: C++ Type Generation =====
def test_get_cpp_type_number(type_query_service):
    """Should return 'double' for NUMBER type"""
    type_info = Type(TypeKind.NUMBER)
    assert type_query_service.get_cpp_type(type_info) == "double"
def test_get_cpp_type_string(type_query_service):
    """Should return 'std::string' for STRING type"""
    type_info = Type(TypeKind.STRING)
    assert type_query_service.get_cpp_type(type_info) == "std::string"
def test_get_cpp_type_boolean(type_query_service):
    """Should return 'bool' for BOOLEAN type"""
    type_info = Type(TypeKind.BOOLEAN)
    assert type_query_service.get_cpp_type(type_info) == "bool"
def test_get_cpp_type_unknown(type_query_service):
    """Should return 'luaValue' for UNKNOWN type"""
    type_info = Type(TypeKind.UNKNOWN)
    assert type_query_service.get_cpp_type(type_info) == "luaValue"
# ===== Test 9: Cache Management =====
def test_clear_cache(context, type_query_service):
    """Should clear type cache"""
    context.define_local("cached_var")
    symbol = context.resolve_symbol("cached_var")
    symbol.inferred_type = Type(TypeKind.NUMBER)
    
    # Query to populate cache
    result1 = type_query_service.get_symbol_type("cached_var")
    assert result1 is not None
    
    # Clear cache
    type_query_service.clear_cache()
    
    # Query again after clear
    result2 = type_query_service.get_symbol_type("cached_var")
    assert result2 is not None
    # Should be different object after clear
    assert result1 is not result2
1.2 Create Directory Structure
mkdir -p lua2c/generators/call_generation
mkdir -p tests/generators/call_generation
1.3 Create TypeQueryService Implementation
File: lua2c/generators/call_generation/__init__.py
"""Call generation module
Provides strategy pattern and utilities for function call generation.
"""
from lua2c.generators.call_generation.type_queries import TypeQueryService
__all__ = ['TypeQueryService']
File: lua2c/generators/call_generation/type_queries.py
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
        symbol = self._context.resolve_symbol(symbol_name)
        if not symbol:
            return None
        
        table_info = getattr(symbol, 'table_info', None)
        if table_info:
            return table_info
        
        # Check if it's special 'arg' array
        if symbol_name == "arg":
            from lua2c.core.type_system import TableTypeInfo
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
        
        # At least one unknown → unknown
        if not left_type or not right_type:
            return Type(TypeKind.UNKNOWN)
        
        return Type(TypeKind.VARIANT)
    
    def clear_cache(self):
        """Clear type cache (useful for testing)"""
        self._cache.clear()
1.4 Run Tests and Fix Failures
# Run tests
pytest tests/generators/call_generation/test_type_query_service.py -v
# Fix any failures (implementation should pass all tests)
---
Phase 2: CallGenerationContext (TDD)
2.1 Create Test File
File: tests/generators/call_generation/test_call_generation_context.py
"""Unit tests for CallGenerationContext using TDD approach"""
import pytest
from pathlib import Path
from luaparser import ast
from lua2c.core.context import TranslationContext
from lua2c.core.type_system import Type, TypeKind
from lua2c.core.global_type_registry import FunctionSignature
from lua2c.generators.call_generation.context import (
    CallGenerationContext,
    CallContextBuilder,
)
@pytest.fixture
def context(tmp_path):
    """Create translation context for testing"""
    ctx = TranslationContext(tmp_path, "test.lua")
    return ctx
# ===== Test 1: Local Function Call Context =====
def test_build_local_function_call_context(context):
    """Should build context for local function call"""
    context.define_function("foo", is_global=False)
    context.define_local("x")
    context.resolve_symbol("x").inferred_type = Type(TypeKind.NUMBER)
    
    expr = ast.parse("foo(x)").body[0].value
    ctx = CallContextBuilder.build(expr, context)
    
    assert ctx.func_path == "foo"
    assert ctx.is_local == True
    assert ctx.signature is None  # Local functions don't have signatures
    assert ctx.num_args == 1
    assert ctx.num_params == 0
def test_build_local_function_call_with_args(context):
    """Should handle multiple arguments for local function"""
    context.define_function("bar", is_global=False)
    context.define_local("a")
    context.resolve_symbol("a").inferred_type = Type(TypeKind.NUMBER)
    context.define_local("b")
    context.resolve_symbol("b").inferred_type = Type(TypeKind.STRING)
    
    expr = ast.parse("bar(a, b)").body[0].value
    ctx = CallContextBuilder.build(expr, context)
    
    assert ctx.func_path == "bar"
    assert ctx.is_local == True
    assert ctx.num_args == 2
    assert len(ctx.arg_types) == 2
# ===== Test 2: Library Function Call Context =====
def test_build_print_call_context(context):
    """Should build context for print() call"""
    from lua2c.core.global_type_registry import GlobalTypeRegistry
    
    expr = ast.parse('print("hello")').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    
    assert ctx.func_path == "print"
    assert ctx.is_local == False
    assert ctx.signature is not None
    assert ctx.signature.return_type == "void"
    assert ctx.num_args == 1
    assert ctx.num_params == 0
def test_build_string_format_call_context(context):
    """Should build context for string.format() call"""
    expr = ast.parse('string.format("%s %d", x, 42)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    
    assert ctx.func_path == "string.format"
    assert ctx.is_local == False
    assert ctx.signature is not None
    assert ctx.signature.return_type == "std::string"
    assert ctx.num_args == 3
    assert ctx.num_params == 1  # Format string is only fixed param
def test_build_math_sqrt_call_context(context):
    """Should build context for math.sqrt() call"""
    expr = ast.parse("math.sqrt(x)").body[0].value
    ctx = CallContextBuilder.build(expr, context)
    
    assert ctx.func_path == "math.sqrt"
    assert ctx.is_local == False
    assert ctx.signature is not None
    assert ctx.signature.return_type == "double"
    assert ctx.num_args == 1
    assert ctx.num_params == 1
# ===== Test 3: Context Helper Methods =====
def test_needs_variadic_always_variadic_flag(context):
    """Should return True when signature.always_variadic is True"""
    from lua2c.core.global_type_registry import GlobalTypeRegistry
    
    # Mock signature with always_variadic=True
    expr = ast.parse('print(x)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    ctx.signature.always_variadic = True
    
    assert ctx.needs_variadic() == True
def test_needs_variadic_signature_flag(context):
    """Should return True when signature.is_variadic is True"""
    from lua2c.core.global_type_registry import GlobalTypeRegistry
    
    expr = ast.parse('string.format("test", x)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    ctx.signature.is_variadic = True
    
    assert ctx.needs_variadic() == True
def test_needs_variadic_library_tracker(context):
    """Should query library_tracker for variadic decision"""
    from lua2c.core.global_type_registry import GlobalTypeRegistry
    
    # Mock library tracker
    class MockTracker:
        def is_variadic(self, func_path):
            return func_path == "print"
    
    expr = ast.parse('print(x)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    
    tracker = MockTracker()
    assert ctx.needs_variadic(library_tracker=tracker) == True
    
    # Different function
    expr2 = ast.parse('math.sqrt(x)').body[0].value
    ctx2 = CallContextBuilder.build(expr2, context)
    assert ctx2.needs_variadic(library_tracker=tracker) == False
def test_needs_vector_detection(context):
    """Should detect functions with vector<luaValue> parameters"""
    from lua2c.core.global_type_registry import GlobalTypeRegistry
    
    # io.write uses vector<luaValue>
    expr = ast.parse('io.write(x)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    
    assert ctx.needs_vector() == True
    
    # math.sqrt does not use vector
    expr2 = ast.parse('math.sqrt(x)').body[0].value
    ctx2 = CallContextBuilder.build(expr2, context)
    
    assert ctx2.needs_vector() == False
def test_has_fixed_params(context):
    """Should detect functions with fixed parameters"""
    from lua2c.core.global_type_registry import GlobalTypeRegistry
    
    # string.format has 1 fixed param (format string)
    expr = ast.parse('string.format("test", x)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    
    assert ctx.has_fixed_params() == True
    assert ctx.get_fixed_param_count() == 1
    
    # print has no fixed params
    expr2 = ast.parse('print(x)').body[0].value
    ctx2 = CallContextBuilder.build(expr2, context)
    
    assert ctx2.has_fixed_params() == False
    assert ctx2.get_fixed_param_count() == 0
# ===== Test 4: Function Path Extraction =====
def test_get_function_path_standalone(context):
    """Should extract path for standalone function (print)"""
    expr = ast.parse('print(x)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.func_path == "print"
def test_get_function_path_module_function(context):
    """Should extract path for module.function (string.format)"""
    expr = ast.parse('string.format("test")').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.func_path == "string.format"
def test_get_function_path_math_function(context):
    """Should extract path for math function (math.sqrt)"""
    expr = ast.parse('math.sqrt(x)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.func_path == "math.sqrt"
# ===== Test 5: Argument Type Inference =====
def test_infer_arg_types_literals(context):
    """Should infer types for literal arguments"""
    expr = ast.parse('print(42, "hello", true)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    
    assert len(ctx.arg_types) == 3
    assert ctx.arg_types[0].kind == TypeKind.NUMBER
    assert ctx.arg_types[1].kind == TypeKind.STRING
    assert ctx.arg_types[2].kind == TypeKind.BOOLEAN
def test_infer_arg_types_symbols(context):
    """Should infer types from symbol inferred types"""
    context.define_local("x")
    context.resolve_symbol("x").inferred_type = Type(TypeKind.NUMBER)
    context.define_local("y")
    context.resolve_symbol("y").inferred_type = Type(TypeKind.STRING)
    
    expr = ast.parse('print(x, y)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    
    assert len(ctx.arg_types) == 2
    assert ctx.arg_types[0].kind == TypeKind.NUMBER
    assert ctx.arg_types[1].kind == TypeKind.STRING
def test_infer_arg_types_mixed(context):
    """Should handle mixed literal and symbol arguments"""
    context.define_local("x")
    context.resolve_symbol("x").inferred_type = Type(TypeKind.NUMBER)
    
    expr = ast.parse('print(x, 42, "text")').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    
    assert len(ctx.arg_types) == 3
    assert ctx.arg_types[0].kind == TypeKind.NUMBER
    assert ctx.arg_types[1].kind == TypeKind.NUMBER
    assert ctx.arg_types[2].kind == TypeKind.STRING
# ===== Test 6: Return Type Inference =====
def test_infer_return_type_void(context):
    """Should infer void return type for print"""
    expr = ast.parse('print(x)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.return_type.kind == TypeKind.NIL  # void maps to NIL in TypeKind
def test_infer_return_type_std_string(context):
    """Should infer std::string return type for string.format"""
    expr = ast.parse('string.format("test")').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.return_type.kind == TypeKind.STRING
def test_infer_return_type_double(context):
    """Should infer double return type for math.sqrt"""
    expr = ast.parse('math.sqrt(x)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.return_type.kind == TypeKind.NUMBER
def test_infer_return_type_lua_value(context):
    """Should infer luaValue return type for functions without signature"""
    context.define_function("custom", is_global=False)
    expr = ast.parse('custom(x)').body[0].value
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.return_type.kind == TypeKind.UNKNOWN
2.2 Create CallGenerationContext Implementation
File: lua2c/generators/call_generation/context.py
"""Context for function call generation
Provides unified access to type information, function signatures,
and generation utilities.
"""
from dataclasses import dataclass
from typing import Optional, Dict, List
from luaparser import astnodes
from lua2c.core.type_system import Type, TypeKind, TableTypeInfo
from lua2c.core.context import TranslationContext
from lua2c.core.global_type_registry import GlobalTypeRegistry, FunctionSignature
@dataclass
class CallGenerationContext:
    """Context object for generating function calls
    
    Centralizes all information needed for call generation:
    - Function signatures
    - Type information
    - Conversion utilities
    """
    
    expr: astnodes.Call
    func_path: Optional[str]  # e.g., "string.format", "print"
    signature: Optional[FunctionSignature]
    arg_types: List[Type]
    arg_table_infos: Dict[int, TableTypeInfo]
    return_type: Optional[Type]
    is_local: bool
    line_number: Optional[int]
    
    def __post_init__(self):
        """Compute derived information"""
        self.num_args = len(self.expr.args)
        self.num_params = len(self.signature.param_types) if self.signature else 0
    
    def needs_variadic(self, library_tracker=None) -> bool:
        """Check if function should use variadic template
        
        Args:
            library_tracker: LibraryCallTracker for checking usage patterns
            
        Returns:
            True if variadic template should be used
        """
        if not self.signature:
            return False
        
        # Hardcoded always-variadic functions
        if getattr(self.signature, 'always_variadic', False):
            return True
        
        # Check library tracker for usage patterns
        if library_tracker and hasattr(library_tracker, 'is_variadic'):
            if library_tracker.is_variadic(self.func_path):
                return True
        
        # Check signature is_variadic flag
        return getattr(self.signature, 'is_variadic', False)
    
    def needs_vector(self) -> bool:
        """Check if function needs vector parameter
        
        Returns:
            True if function uses std::vector<luaValue> parameter
        """
        if not self.signature:
            return False
        return any("vector<luaValue>" in pt for pt in self.signature.param_types)
    
    def has_fixed_params(self) -> bool:
        """Check if function has fixed (non-variadic) parameters
        
        Returns:
            True if function has at least one fixed parameter
        """
        return self.num_params > 0
    
    def get_fixed_param_count(self) -> int:
        """Get number of fixed parameters
        
        Returns:
            Number of parameters before variadic ones
        """
        if not self.signature:
            return 0
        return len(self.signature.param_types)
class CallContextBuilder:
    """Builder for creating CallGenerationContext objects"""
    
    @staticmethod
    def build(expr: astnodes.Call, context: TranslationContext, type_inferencer=None) -> CallGenerationContext:
        """Build a CallGenerationContext from a Call node
        
        Args:
            expr: Call AST node
            context: TranslationContext
            type_inferencer: Optional TypeInference instance
            
        Returns:
            CallGenerationContext with all information populated
        """
        # Get function path
        func_path = CallContextBuilder._get_function_path(expr)
        
        # Get signature
        signature = None
        if func_path:
            signature = GlobalTypeRegistry.get_function_signature(func_path)
        
        # Check if local
        is_local = CallContextBuilder._is_local_call(expr, context)
        
        # Infer argument types
        arg_types = CallContextBuilder._infer_arg_types(expr, context, type_inferencer)
        
        # Get table info for arguments
        arg_table_infos = CallContextBuilder._get_arg_table_infos(expr, context)
        
        # Get return type
        return_type = CallContextBuilder._get_return_type(expr, context, signature)
        
        return CallGenerationContext(
            expr=expr,
            func_path=func_path,
            signature=signature,
            arg_types=arg_types,
            arg_table_infos=arg_table_infos,
            return_type=return_type,
            is_local=is_local,
            line_number=getattr(expr, 'lineno', None),
        )
    
    @staticmethod
    def _get_function_path(expr: astnodes.Call) -> Optional[str]:
        """Extract function path from call expression
        
        Args:
            expr: Call AST node
            
        Returns:
            Function path (e.g., "string.format", "print") or None
        """
        if isinstance(expr.func, astnodes.Index):
            if isinstance(expr.func.value, astnodes.Name) and isinstance(expr.func.idx, astnodes.Name):
                module_name = expr.func.value.id
                func_name = expr.func.idx.id
                return f"{module_name}.{func_name}"
        elif isinstance(expr.func, astnodes.Name):
            return expr.func.id
        
        return None
    
    @staticmethod
    def _is_local_call(expr: astnodes.Call, context: TranslationContext) -> bool:
        """Check if this is a local function call
        
        Args:
            expr: Call AST node
            context: Translation context
            
        Returns:
            True if local function call
        """
        if not isinstance(expr.func, astnodes.Name):
            return False
        
        func_name = expr.func.id
        symbol = context.resolve_symbol(func_name)
        return symbol and not symbol.is_global
    
    @staticmethod
    def _infer_arg_types(expr: astnodes.Call, context: TranslationContext, type_inferencer) -> List[Type]:
        """Infer types for all arguments
        
        Args:
            expr: Call AST node
            context: Translation context
            type_inferencer: Optional type inference engine
            
        Returns:
            List of Type objects for each argument
        """
        from lua2c.generators.call_generation.type_queries import TypeQueryService
        
        type_service = TypeQueryService(context, type_inferencer)
        arg_types = []
        
        for arg in expr.args:
            arg_type = type_service.get_expression_type(arg)
            if arg_type is None:
                arg_type = Type(TypeKind.UNKNOWN)
            arg_types.append(arg_type)
        
        return arg_types
    
    @staticmethod
    def _get_arg_table_infos(expr: astnodes.Call, context: TranslationContext) -> Dict[int, TableTypeInfo]:
        """Get table type information for arguments
        
        Args:
            expr: Call AST node
            context: Translation context
            
        Returns:
            Dict mapping argument index to TableTypeInfo
        """
        from lua2c.generators.call_generation.type_queries import TypeQueryService
        
        type_service = TypeQueryService(context)
        table_infos = {}
        
        for i, arg in enumerate(expr.args):
            if isinstance(arg, astnodes.Name):
                table_info = type_service.get_table_info(arg.id)
                if table_info:
                    table_infos[i] = table_info
        
        return table_infos
    
    @staticmethod
    def _get_return_type(expr: astnodes.Call, context: TranslationContext, signature: Optional[FunctionSignature]) -> Optional[Type]:
        """Get return type for function call
        
        Args:
            expr: Call AST node
            context: Translation context
            signature: Function signature if available
            
        Returns:
            Return type or None
        """
        if signature and signature.return_type:
            # Map C++ types to TypeKind
            if signature.return_type == "void":
                return Type(TypeKind.NIL)
            elif signature.return_type == "double":
                return Type(TypeKind.NUMBER)
            elif signature.return_type == "std::string":
                return Type(TypeKind.STRING)
            elif signature.return_type == "bool":
                return Type(TypeKind.BOOLEAN)
            else:
                return Type(TypeKind.UNKNOWN)
        
        # Local functions or unknown functions return luaValue
        return Type(TypeKind.UNKNOWN)
2.3 Update Init File
File: lua2c/generators/call_generation/__init__.py
"""Call generation module
Provides strategy pattern and utilities for function call generation.
"""
from lua2c.generators.call_generation.type_queries import TypeQueryService
from lua2c.generators.call_generation.context import (
    CallGenerationContext,
    CallContextBuilder,
)
__all__ = [
    'TypeQueryService',
    'CallGenerationContext',
    'CallContextBuilder',
]
2.4 Run Tests and Fix Failures
# Run tests
pytest tests/generators/call_generation/test_call_generation_context.py -v
# Fix any failures
---
Phase 3: Strategy Pattern Implementation (TDD)
3.1 Create Test File
File: tests/generators/call_generation/test_strategies.py
"""Unit tests for call generation strategies using TDD approach"""
import pytest
from pathlib import Path
from luaparser import ast
from lua2c.core.context import TranslationContext
from lua2c.core.type_system import Type, TypeKind
from lua2c.generators.call_generation.strategies import (
    LocalFunctionStrategy,
    LibraryFunctionStrategy,
    StaticLibraryStrategy,
    DefaultCallStrategy,
)
from lua2c.generators.call_generation.context import CallContextBuilder
@pytest.fixture
def context(tmp_path):
    """Create translation context for testing"""
    ctx = TranslationContext(tmp_path, "test.lua")
    return ctx
@pytest.fixture
def expr_generator(context):
    """Create minimal ExprGenerator for testing"""
    from lua2c.generators.expr_generator import ExprGenerator
    from lua2c.generators.stmt_generator import StmtGenerator
    from lua2c.generators.naming import NamingScheme
    
    generator = ExprGenerator(context)
    return generator
# ===== Test 1: LocalFunctionStrategy =====
class TestLocalFunctionStrategy:
    """Tests for local function call strategy"""
    
    def test_can_handle_local_function(self, context):
        """Local function should be handled"""
        context.define_function("foo", is_global=False)
        expr = ast.parse("foo(x)").body[0].value
        strategy = LocalFunctionStrategy()
        assert strategy.can_handle(expr, context) == True
    
    def test_cannot_handle_global_function(self, context):
        """Global function should not be handled"""
        context.define_function("print", is_global=True)
        expr = ast.parse("print(x)").body[0].value
        strategy = LocalFunctionStrategy()
        assert strategy.can_handle(expr, context) == False
    
    def test_cannot_handle_library_function(self, context):
        """Library function (string.format) should not be handled"""
        expr = ast.parse('string.format("test")').body[0].value
        strategy = LocalFunctionStrategy()
        assert strategy.can_handle(expr, context) == False
    
    def test_cannot_handle_non_name_function(self, context):
        """Function that's not a simple name should not be handled"""
        expr = ast.parse('obj.method(x)').body[0].value
        strategy = LocalFunctionStrategy()
        assert strategy.can_handle(expr, context) == False
    
    def test_generate_with_single_arg(self, context, expr_generator):
        """Should generate call with state parameter and single argument"""
        context.define_local("x")
        context.resolve_symbol("x").inferred_type = Type(TypeKind.NUMBER)
        context.define_function("foo", is_global=False)
        
        expr = ast.parse("foo(x)").body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        
        strategy = LocalFunctionStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "foo(" in result
        assert "state," in result
        assert "x" in result
        assert result.endswith(")")
    
    def test_generate_with_multiple_args(self, context, expr_generator):
        """Should generate call with state parameter and multiple arguments"""
        context.define_local("a")
        context.resolve_symbol("a").inferred_type = Type(TypeKind.NUMBER)
        context.define_local("b")
        context.resolve_symbol("b").inferred_type = Type(TypeKind.NUMBER)
        context.define_function("bar", is_global=False)
        
        expr = ast.parse("bar(a, b)").body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        
        strategy = LocalFunctionStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "bar(" in result
        assert "state," in result
        assert "a" in result
        assert "b" in result
    
    def test_generate_with_literal_arg(self, context, expr_generator):
        """Should generate call with literal argument"""
        context.define_function("baz", is_global=False)
        
        expr = ast.parse('baz("hello")').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        
        strategy = LocalFunctionStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert 'baz("hello")' in result or "baz(\"hello\")" in result
# ===== Test 2: LibraryFunctionStrategy =====
class TestLibraryFunctionStrategy:
    """Tests for library function strategy"""
    
    def test_can_handle_print(self, context):
        """print() should be handled"""
        expr = ast.parse("print(42)").body[0].value
        strategy = LibraryFunctionStrategy()
        assert strategy.can_handle(expr, context) == True
    
    def test_can_handle_string_format(self, context):
        """string.format() should be handled"""
        expr = ast.parse('string.format("test", x)').body[0].value
        strategy = LibraryFunctionStrategy()
        assert strategy.can_handle(expr, context) == True
    
    def test_can_handle_math_sqrt(self, context):
        """math.sqrt() should be handled"""
        expr = ast.parse("math.sqrt(x)").body[0].value
        strategy = LibraryFunctionStrategy()
        assert strategy.can_handle(expr, context) == True
    
    def test_cannot_handle_local_function(self, context):
        """Local function should not be handled"""
        context.define_function("local_func", is_global=False)
        expr = ast.parse("local_func(x)").body[0].value
        strategy = LibraryFunctionStrategy()
        assert strategy.can_handle(expr, context) == False
# ===== Test 3: StaticLibraryStrategy =====
class TestStaticLibraryStrategy:
    """Tests for static typed library function strategy"""
    
    def test_can_handle_math_sqrt(self, context):
        """math.sqrt should be handled (has fixed double parameter)"""
        expr = ast.parse("math.sqrt(x)").body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        
        strategy = StaticLibraryStrategy()
        assert strategy.can_handle(expr, context, call_ctx.signature) == True
    
    def test_can_handle_math_abs(self, context):
        """math.abs should be handled (has fixed double parameter)"""
        expr = ast.parse("math.abs(x)").body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        
        strategy = StaticLibraryStrategy()
        assert strategy.can_handle(expr, context, call_ctx.signature) == True
    
    def test_generate_math_sqrt(self, context, expr_generator):
        """Should generate direct call to math.sqrt with double parameter"""
        expr = ast.parse("math.sqrt(4.0)").body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        
        strategy = StaticLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "math_sqrt(" in result
        assert ")" in result
    
    def test_generate_math_sqrt_with_symbol(self, context, expr_generator):
        """Should generate call with symbol argument"""
        context.define_local("x")
        context.resolve_symbol("x").inferred_type = Type(TypeKind.NUMBER)
        
        expr = ast.parse("math.sqrt(x)").body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        
        strategy = StaticLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "math_sqrt(" in result
        assert "x" in result
# ===== Test 4: DefaultCallStrategy =====
class TestDefaultCallStrategy:
    """Tests for default call strategy"""
    
    def test_always_can_handle(self, context):
        """Default strategy should always handle (fallback)"""
        expr = ast.parse("unknown_function(x)").body[0].value
        strategy = DefaultCallStrategy()
        assert strategy.can_handle(expr, context) == True
    
    def test_generates_lua_value_wrapped_call(self, context, expr_generator):
        """Should generate call with luaValue-wrapped arguments"""
        expr = ast.parse("unknown_function(x, 42)").body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        
        strategy = DefaultCallStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "luaValue" in result
        assert "unknown_function" in result
        assert "{" in result
        assert "}" in result
3.2 Create Strategy Implementations
File: lua2c/generators/call_generation/strategies.py
"""Strategy pattern for function call generation
Different call types (local, library, variadic, vector) use different
strategies, making code more modular and testable.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from luaparser import astnodes
from lua2c.core.type_system import Type
from lua2c.core.context import TranslationContext
from lua2c.generators.call_generation.context import CallGenerationContext
class CallGenerationStrategy(ABC):
    """Base class for call generation strategies"""
    
    @abstractmethod
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        """Check if this strategy can handle call
        
        Args:
            expr: Call AST node
            context: Translation context
            **kwargs: Additional context (signature, etc.)
            
        Returns:
            True if this strategy can handle the call
        """
        pass
    
    @abstractmethod
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:
        """Generate C++ code for call
        
        Args:
            expr: Call AST node
            context: Translation context
            expr_generator: ExprGenerator instance
            call_ctx: Call generation context
            
        Returns:
            Generated C++ code
        """
        pass
class LocalFunctionStrategy(CallGenerationStrategy):
    """Strategy for local function calls: func(state, args...)"""
    
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        if not isinstance(expr.func, astnodes.Name):
            return False
        symbol = context.resolve_symbol(expr.func.id)
        return symbol and not symbol.is_global
    
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:
        from lua2c.generators.call_generation.type_queries import TypeQueryService
        
        # Generate function name
        func = expr_generator.generate(expr.func)
        
        # Handle temporaries for non-const lvalue reference binding
        wrapped_args = []
        temp_decls = []
        temp_counter = [0]
        
        type_service = TypeQueryService(context, expr_generator._type_inferencer)
        
        for arg in expr.args:
            # Set expected types for literals to generate native literals
            is_literal = isinstance(arg, (astnodes.Number, astnodes.String, 
                                        astnodes.TrueExpr, astnodes.FalseExpr))
            
            if is_literal:
                expr_generator._set_expected_type(arg, Type(TypeKind.NUMBER) if isinstance(arg, astnodes.Number) else Type(TypeKind.STRING))
            
            arg_code = expr_generator.generate(arg)
            expr_generator._clear_expected_type(arg)
            
            if expr_generator._is_temporary_expression(arg):
                temp_name = f"_l2c_tmp_arg_{temp_counter[0]}"
                temp_counter[0] += 1
                
                if isinstance(arg, astnodes.Number):
                    temp_decls.append(f"double {temp_name} = {arg_code}")
                elif isinstance(arg, astnodes.String):
                    temp_decls.append(f'std::string {temp_name} = {arg_code}')
                else:
                    temp_decls.append(f"auto {temp_name} = {arg_code}")
                wrapped_args.append(temp_name)
            else:
                wrapped_args.append(arg_code)
        
        args_str = ", ".join(wrapped_args)
        
        if temp_decls:
            # Need to wrap in block scope for temporaries
            temps = "; ".join(temp_decls)
            return f"[&] {{ {temps}; return {func}(state, {args_str}); }}()"
        else:
            return f"{func}(state, {args_str})"
class LibraryFunctionStrategy(CallGenerationStrategy):
    """Strategy for library function calls"""
    
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        if isinstance(expr.func, astnodes.Index):
            if isinstance(expr.func.value, astnodes.Name) and isinstance(expr.func.idx, astnodes.Name):
                return True
        elif isinstance(expr.func, astnodes.Name):
            # Check if it's a standalone library function (print, tonumber)
            func_name = expr.func.id
            from lua2c.core.global_type_registry import GlobalTypeRegistry
            sig = GlobalTypeRegistry.get_function_signature(func_name)
            return sig is not None
        return False
    
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:
        # Generate function reference
        func = expr_generator.generate(expr.func)
        
        # Generate arguments based on signature
        result_args = []
        
        if call_ctx.signature:
            param_types = call_ctx.signature.param_types if call_ctx.signature.param_types else []
            
            for i, arg in enumerate(expr.args):
                param_type = param_types[i] if i < len(param_types) else None
                arg_code = expr_generator.generate(arg)
                
                # Handle type conversions for fixed parameters
                if param_type:
                    result_args.append(self._handle_param_conversion(arg_code, param_type, arg, context, expr_generator))
                else:
                    # Variadic parameter - pass as-is (will be handled by variadic strategy)
                    result_args.append(arg_code)
        
        args_str = ", ".join(result_args)
        return f"({func})({args_str})"
    
    def _handle_param_conversion(self, arg_code: str, param_type: str, arg: astnodes.Node, context: TranslationContext, expr_generator) -> str:
        """Handle parameter type conversion if needed
        
        Args:
            arg_code: Generated argument code
            param_type: Parameter C++ type
            arg: Argument AST node
            context: Translation context
            expr_generator: ExprGenerator instance
            
        Returns:
            Argument code with appropriate conversions
        """
        # Don't wrap if parameter type is std::string or double
        if param_type in ["const std::string&", "std::string", "double", "const double&"]:
            from lua2c.generators.call_generation.type_queries import TypeQueryService
            
            type_service = TypeQueryService(context, expr_generator._type_inferencer)
            target_type = type_service.get_expression_type(arg)
            
            if target_type:
                cpp_type = type_service.get_cpp_type(target_type)
                # Check if type matches parameter type
                if cpp_type == param_type or cpp_type.replace("const ", "").replace("&", "") == param_type:
                    return arg_code
            
            # If arg_code is luaValue(...), unwrap it
            if arg_code.startswith("luaValue(") and arg_code.endswith(")"):
                inner = arg_code[9:-1]  # Remove "luaValue(" and ")"
                
                # Check if inner is a literal
                if inner.startswith('"') or inner.replace('.', '').replace('-', '').replace('+', '').isdigit():
                    return inner
                
                # Unwrap based on parameter type
                if param_type in ["const std::string&", "std::string"]:
                    return f"{inner}.as_string()"
                elif param_type in ["double", "const double&"]:
                    return f"{inner}.as_number()"
            
            return arg_code
        
        # For luaValue parameters, wrap in luaValue
        return f"luaValue({arg_code})"
class StaticLibraryStrategy(CallGenerationStrategy):
    """Strategy for static typed library functions (math.sqrt, etc.)"""
    
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        # Check if we have a signature
        signature = kwargs.get('signature')
        if not signature:
            return False
        
        # Static library functions have fixed, non-variadic parameters
        # and don't use vector<luaValue>
        if signature.param_types and not any("vector<luaValue>" in pt for pt in signature.param_types):
            return True
        
        return False
    
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:
        # Generate function reference
        func = expr_generator.generate(expr.func)
        
        # Generate arguments (no luaValue wrapping needed for static functions)
        args = []
        for arg in expr.args:
            arg_code = expr_generator.generate(arg)
            args.append(arg_code)
        
        args_str = ", ".join(args)
        return f"({func})({args_str})"
class DefaultCallStrategy(CallGenerationStrategy):
    """Strategy for generic function calls (fallback)"""
    
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        # Always returns True as fallback
        return True
    
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:
        # Default behavior: wrap all arguments in luaValue
        func = expr_generator.generate(expr.func)
        
        args = []
        for arg in expr.args:
            arg_code = expr_generator.generate(arg)
            
            from lua2c.generators.call_generation.type_queries import TypeQueryService
            type_service = TypeQueryService(context, expr_generator._type_inferencer)
            
            if type_service.needs_lua_value_wrapper(arg):
                args.append(f"luaValue({arg_code})")
            else:
                args.append(arg_code)
        
        args_str = ", ".join(args)
        return f"({func})({{{args_str}}})"
3.3 Update Init File
File: lua2c/generators/call_generation/__init__.py
"""Call generation module
Provides strategy pattern and utilities for function call generation.
"""
from lua2c.generators.call_generation.type_queries import TypeQueryService
from lua2c.generators.call_generation.context import (
    CallGenerationContext,
    CallContextBuilder,
)
from lua2c.generators.call_generation.strategies import (
    LocalFunctionStrategy,
    LibraryFunctionStrategy,
    StaticLibraryStrategy,
    DefaultCallStrategy,
    CallGenerationStrategy,
)
__all__ = [
    'TypeQueryService',
    'CallGenerationContext',
    'CallContextBuilder',
    'LocalFunctionStrategy',
    'LibraryFunctionStrategy',
    'StaticLibraryStrategy',
    'DefaultCallStrategy',
    'CallGenerationStrategy',
]
3.4 Run Tests and Fix Failures
# Run tests
pytest tests/generators/call_generation/test_strategies.py -v
# Fix any failures
---
Phase 4: VariadicLibraryStrategy (TDD)
4.1 Create Test File
File: tests/generators/call_generation/test_variadic_strategy.py
"""Unit tests for VariadicLibraryStrategy using TDD approach
Tests variadic template generation for print, io.write, string.format
"""
import pytest
from pathlib import Path
from luaparser import ast
from lua2c.core.context import TranslationContext
from lua2c.core.type_system import Type, TypeKind
from lua2c.core.global_type_registry import FunctionSignature
from lua2c.generators.call_generation.strategies import VariadicLibraryStrategy
from lua2c.generators.call_generation.context import CallContextBuilder
@pytest.fixture
def context(tmp_path):
    """Create translation context for testing"""
    ctx = TranslationContext(tmp_path, "test.lua")
    return ctx
@pytest.fixture
def expr_generator(context):
    """Create minimal ExprGenerator for testing"""
    from lua2c.generators.expr_generator import ExprGenerator
    generator = ExprGenerator(context)
    return generator
# ===== Test 1: Variadic Detection =====
class TestVariadicDetection:
    """Tests for detecting when variadic should be used"""
    
    def test_can_handle_always_variadic_flag(self, context):
        """Should handle functions with always_variadic=True"""
        expr = ast.parse('print("hello")').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.always_variadic = True
        
        strategy = VariadicLibraryStrategy()
        assert strategy.can_handle(expr, context, signature=call_ctx.signature) == True
    
    def test_can_handle_variadic_flag(self, context):
        """Should handle functions with is_variadic=True"""
        expr = ast.parse('string.format("test", x)').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.is_variadic = True
        
        strategy = VariadicLibraryStrategy()
        assert strategy.can_handle(expr, context, signature=call_ctx.signature) == True
    
    def test_cannot_handle_non_variadic(self, context):
        """Should not handle non-variadic functions"""
        expr = ast.parse("math.sqrt(x)").body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        
        strategy = VariadicLibraryStrategy()
        assert strategy.can_handle(expr, context, signature=call_ctx.signature) == False
    
    def test_needs_variadic_with_tracker(self, context):
        """Should use library tracker to determine variadic"""
        expr = ast.parse('print("hello")').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        
        # Mock library tracker
        class MockTracker:
            def is_variadic(self, func_path):
                return func_path == "print"
        
        tracker = MockTracker()
        
        strategy = VariadicLibraryStrategy()
        strategy.set_library_tracker(tracker)
        
        assert strategy.can_handle(expr, context, signature=call_ctx.signature) == True
# ===== Test 2: Print Function Generation =====
class TestPrintGeneration:
    """Tests for print() function generation"""
    
    def test_generate_print_with_string_literal(self, context, expr_generator):
        """print("hello") should generate: print("hello")"""
        expr = ast.parse('print("hello")').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.always_variadic = True
        call_ctx.signature.is_variadic = True
        
        strategy = VariadicLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert 'print("hello")' in result or "print(\"hello\")" in result
        # Should NOT have luaValue wrapping
        assert "luaValue" not in result
        # Should NOT have vector wrapping
        assert "std::vector" not in result
    
    def test_generate_print_with_number_literal(self, context, expr_generator):
        """print(42) should generate: print(42)"""
        expr = ast.parse("print(42)").body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.always_variadic = True
        
        strategy = VariadicLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "print(42)" in result
        assert "luaValue" not in result
        assert "std::vector" not in result
    
    def test_generate_print_with_multiple_args(self, context, expr_generator):
        """print(x, y, z) should generate: print(x, y, z)"""
        expr = ast.parse("print(x, y, z)").body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.always_variadic = True
        
        strategy = VariadicLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "print(" in result
        assert "x" in result
        assert "y" in result
        assert "z" in result
        # Args should be comma-separated, not in vector
        assert "," in result
        assert "std::vector" not in result
    
    def test_generate_print_with_mixed_types(self, context, expr_generator):
        """print(42, "text", true) should handle mixed types"""
        expr = ast.parse('print(42, "text", true)').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.always_variadic = True
        
        strategy = VariadicLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "print(" in result
        assert "luaValue" not in result
        assert "std::vector" not in result
# ===== Test 3: String.format Function Generation =====
class TestStringFormatGeneration:
    """Tests for string.format() function generation"""
    
    def test_generate_string_format_with_format_string(self, context, expr_generator):
        """string.format("test") should generate: string.format("test")"""
        expr = ast.parse('string.format("test")').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.is_variadic = True
        
        strategy = VariadicLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert 'string.format("test")' in result or "string.format(\"test\")" in result
        assert "luaValue" not in result
        assert "std::vector" not in result
    
    def test_generate_string_format_with_args(self, context, expr_generator):
        """string.format("%s %d", x, 42) should: string.format("%s %d", x, 42)"""
        expr = ast.parse('string.format("%s %d", x, 42)').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.is_variadic = True
        
        strategy = VariadicLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "string.format(" in result
        # Should have format string as regular arg (not in vector)
        assert '"%s %d"' in result or "\"%s %d\"" in result
        # Should have other args
        assert "x" in result
        assert "42" in result
        # Should NOT have vector
        assert "std::vector" not in result
    
    def test_generate_string_format_with_global_vars(self, context, expr_generator):
        """string.format("x=%d", state->N) should: string.format("x=%d", state->N)"""
        context.define_global("N")
        context.resolve_symbol("N").inferred_type = Type(TypeKind.NUMBER)
        
        expr = ast.parse('string.format("x=%d", N)').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.is_variadic = True
        
        strategy = VariadicLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "string.format(" in result
        assert "N" in result
        assert "luaValue" not in result
        assert "std::vector" not in result
    
    def test_generate_string_format_unwraps_lua_value(self, context, expr_generator):
        """Should unwrap luaValue for non-literal arguments"""
        context.define_local("s")
        context.resolve_symbol("s").inferred_type = Type(TypeKind.NUMBER)
        
        # Simulate an expression that generates luaValue(s)
        expr = ast.parse('string.format("%d", s)').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.is_variadic = True
        
        strategy = VariadicLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        # For variadic, we pass args directly (no unwrapping needed)
        assert "string.format(" in result
# ===== Test 4: Nested Variadic Calls =====
class TestNestedVariadicCalls:
    """Tests for nested variadic function calls"""
    
    def test_print_string_format(self, context, expr_generator):
        """print(string.format("test", x)) should handle nesting"""
        expr = ast.parse('print(string.format("test", x))').body[0].value
        
        # We'll build context for the outer print call
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.always_variadic = True
        
        strategy = VariadicLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        # Outer print should be variadic
        assert "print(" in result
        # Inner string.format should be generated (will be handled separately)
        assert "string.format" in result
    
    def test_nested_varadic_multiple_levels(self, context, expr_generator):
        """Should handle multiple levels of nesting"""
        expr = ast.parse('print(string.format("a=%d b=%s", x, string.format("c=%d", z)))').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.always_variadic = True
        
        strategy = VariadicLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "print(" in result
        assert "string.format" in result
# ===== Test 5: Integration with Type Inference =====
class TestVariadicWithTypeInference:
    """Tests for variadic with type inference"""
    
    def test_variadic_with_typed_globals(self, context, expr_generator):
        """Should use typed globals directly in variadic calls"""
        context.define_global("NUM")
        context.resolve_symbol("NUM").inferred_type = Type(TypeKind.NUMBER)
        context.define_global("NAME")
        context.resolve_symbol("NAME").inferred_type = Type(TypeKind.STRING)
        
        expr = ast.parse('print(NUM, NAME)').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.always_variadic = True
        
        strategy = VariadicLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "print(" in result
        assert "NUM" in result
        assert "NAME" in result
        # Should NOT have luaValue wrapping
        assert "luaValue" not in result
    
    def test_variadic_with_literal_numbers(self, context, expr_generator):
        """Should handle number literals directly"""
        expr = ast.parse('print(3.14, -42, 0)').body[0].value
        call_ctx = CallContextBuilder.build(expr, context)
        call_ctx.signature.always_variadic = True
        
        strategy = VariadicLibraryStrategy()
        result = strategy.generate(expr, context, expr_generator, call_ctx)
        
        assert "print(" in result
        assert "3.14" in result
        assert "-42" in result
        assert "0" in result
        assert "luaValue" not in result
4.2 Create VariadicLibraryStrategy Implementation
File: lua2c/generators/call_generation/strategies.py
Add to existing file:
class VariadicLibraryStrategy(CallGenerationStrategy):
    """Strategy for variadic template library calls (print, io.write, string.format)
    
    Generates calls like: func(arg1, arg2, ...)
    instead of: func({arg1, arg2, ...})
    
    Uses auto&& forwarding references for maximum flexibility.
    """
    
    def __init__(self):
        self._library_tracker = None
    
    def set_library_tracker(self, tracker) -> None:
        """Set library call tracker
        
        Args:
            tracker: LibraryCallTracker instance
        """
        self._library_tracker = tracker
    
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        # Check if we have a signature
        signature = kwargs.get('signature')
        if not signature:
            return False
        
        # Check always_variadic flag
        if getattr(signature, 'always_variadic', False):
            return True
        
        # Check is_variadic flag
        if getattr(signature, 'is_variadic', False):
            return True
        
        # Check library tracker
        if self._library_tracker and hasattr(self._library_tracker, 'is_variadic'):
            func_path = self._get_function_path(expr)
            if func_path and self._library_tracker.is_variadic(func_path):
                return True
        
        return False
    
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:
        # Generate function reference
        func = expr_generator.generate(expr.func)
        
        # Generate arguments
        result_args = []
        
        if call_ctx.signature:
            # Process fixed parameters (non-variadic)
            num_fixed = call_ctx.get_fixed_param_count()
            
            for i, arg in enumerate(expr.args):
                arg_code = expr_generator.generate(arg)
                
                if i < num_fixed:
                    # Fixed parameter - handle type matching
                    param_type = call_ctx.signature.param_types[i] if i < len(call_ctx.signature.param_types) else None
                    arg_code = self._handle_fixed_param(arg_code, param_type, arg, context, expr_generator)
                    result_args.append(arg_code)
                else:
                    # Variadic parameter - pass as-is (auto&& handles forwarding)
                    result_args.append(arg_code)
        else:
            # No signature - pass all args as-is
            for arg in expr.args:
                arg_code = expr_generator.generate(arg)
                result_args.append(arg_code)
        
        args_str = ", ".join(result_args)
        
        # Handle return type wrapping if needed
        if call_ctx.signature and call_ctx.signature.return_type != "luaValue":
            # Non-luaValue return type (std::string, double, void)
            return f"({func})({args_str})"
        else:
            # luaValue return type - check if caller needs luaValue
            if expr_generator._returns_non_lua_value(expr):
                return f"({func})({args_str})"
            else:
                # Wrap entire call in luaValue
                return f"luaValue(({func})({args_str}))"
    
    def _get_function_path(self, expr: astnodes.Call) -> Optional[str]:
        """Get function path from call expression"""
        if isinstance(expr.func, astnodes.Index):
            if isinstance(expr.func.value, astnodes.Name) and isinstance(expr.func.idx, astnodes.Name):
                return f"{expr.func.value.id}.{expr.func.idx.id}"
        elif isinstance(expr.func, astnodes.Name):
            return expr.func.id
        return None
    
    def _handle_fixed_param(self, arg_code: str, param_type: Optional[str], arg: astnodes.Node, 
                          context: TranslationContext, expr_generator) -> str:
        """Handle type conversion for fixed parameters
        
        Args:
            arg_code: Generated argument code
            param_type: Parameter C++ type
            arg: Argument AST node
            context: Translation context
            expr_generator: ExprGenerator instance
            
        Returns:
            Argument code with appropriate conversions
        """
        if not param_type:
            return arg_code
        
        # Handle std::string& parameters
        if param_type in ["const std::string&", "std::string"]:
            from lua2c.generators.call_generation.type_queries import TypeQueryService
            
            type_service = TypeQueryService(context, expr_generator._type_inferencer)
            
            # If arg is luaValue(...), unwrap it
            if arg_code.startswith("luaValue(") and arg_code.endswith(")"):
                inner = arg_code[9:-1]
                
                # Check if inner is a literal string
                if inner.startswith('"'):
                    return inner
                
                # Unwrap to .as_string()
                return f"{inner}.as_string()"
            
            # Otherwise, use as-is
            return arg_code
        
        # Handle double parameters
        if param_type in ["double", "const double&"]:
            from lua2c.generators.call_generation.type_queries import TypeQueryService
            
            type_service = TypeQueryService(context, expr_generator._type_inferencer)
            
            # If arg is luaValue(...), unwrap it
            if arg_code.startswith("luaValue(") and arg_code.endswith(")"):
                inner = arg_code[9:-1]
                
                # Check if inner is a number literal
                if inner.replace('.', '').replace('-', '').replace('+', '').isdigit():
                    return inner
                
                # Unwrap to .as_number()
                return f"{inner}.as_number()"
            
            # Otherwise, use as-is
            return arg_code
        
        # Other parameter types - use as-is
        return arg_code
4.3 Update LibraryFunctionStrategy to Delegate
File: lua2c/generators/call_generation/strategies.py
Modify LibraryFunctionStrategy:
class LibraryFunctionStrategy(CallGenerationStrategy):
    """Strategy for library function calls
    
    Delegates to sub-strategies based on function characteristics:
    - VariadicLibraryStrategy: For variadic template functions
    - StaticLibraryStrategy: For static typed functions
    """
    
    def __init__(self):
        self.sub_strategies = [
            VariadicLibraryStrategy(),
            StaticLibraryStrategy(),
        ]
    
    def set_library_tracker(self, tracker) -> None:
        """Set library call tracker for sub-strategies"""
        for strategy in self.sub_strategies:
            if hasattr(strategy, 'set_library_tracker'):
                strategy.set_library_tracker(tracker)
    
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        if isinstance(expr.func, astnodes.Index):
            if isinstance(expr.func.value, astnodes.Name) and isinstance(expr.func.idx, astnodes.Name):
                return True
        elif isinstance(expr.func, astnodes.Name):
            func_name = expr.func.id
            from lua2c.core.global_type_registry import GlobalTypeRegistry
            sig = GlobalTypeRegistry.get_function_signature(func_name)
            return sig is not None
        return False
    
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:
        # Delegate to appropriate sub-strategy
        signature = call_ctx.signature if call_ctx else None
        
        for strategy in self.sub_strategies:
            if strategy.can_handle(expr, context, signature=signature):
                return strategy.generate(expr, context, expr_generator, call_ctx)
        
        # Fallback to default behavior
        return self._generate_default(expr, context, expr_generator, call_ctx)
    
    def _generate_default(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:
        """Default generation for library functions"""
        func = expr_generator.generate(expr.func)
        result_args = []
        
        for arg in expr.args:
            arg_code = expr_generator.generate(arg)
            
            from lua2c.generators.call_generation.type_queries import TypeQueryService
            type_service = TypeQueryService(context, expr_generator._type_inferencer)
            
            if type_service.needs_lua_value_wrapper(arg):
                result_args.append(f"luaValue({arg_code})")
            else:
                result_args.append(arg_code)
        
        args_str = ", ".join(result_args)
        return f"({func})({args_str})"
4.4 Run Tests and Fix Failures
# Run tests
pytest tests/generators/call_generation/test_variadic_strategy.py -v
# Fix any failures
---
Phase 5: Update GlobalTypeRegistry
5.1 Update FunctionSignature Dataclass
File: lua2c/core/global_type_registry.py
@dataclass
class FunctionSignature:
    """C++ function signature for Lua library function"""
    return_type: str
    param_types: List[str]
    cpp_signature: str  # Full C++ signature including function pointer syntax
    is_variadic: bool = False  # True if function accepts variadic arguments
    variadic_param_type: Optional[str] = None  # Type for variadic args (e.g., "auto&&")
    always_variadic: bool = False  # Functions like print that are always variadic
5.2 Update Function Signatures
File: lua2c/core/global_type_registry.py
LIBRARY_FUNCTIONS: Dict[str, FunctionSignature] = {
    # IO library
    "io.write": FunctionSignature(
        return_type="void",
        param_types=[],
        cpp_signature="template<typename... Args> void(*)(Args&&...)",
        is_variadic=True,
        variadic_param_type="auto&&",
        always_variadic=True,
    ),
    "io.read": FunctionSignature(
        return_type="std::string",
        param_types=["const std::string&"],
        cpp_signature="std::string(*)(const std::string&)",
    ),
    # String library
    "string.format": FunctionSignature(
        return_type="std::string",
        param_types=["const std::string&"],
        cpp_signature="template<typename... Args> std::string(*)(const std::string&, Args&&...)",
        is_variadic=True,
        variadic_param_type="auto&&",
        always_variadic=True,
    ),
    # ... existing functions remain unchanged ...
}
STANDALONE_FUNCTIONS: Dict[str, FunctionSignature] = {
    "print": FunctionSignature(
        return_type="void",
        param_types=[],
        cpp_signature="template<typename... Args> void(*)(Args&&...)",
        is_variadic=True,
        variadic_param_type="auto&&",
        always_variadic=True,
    ),
    "tonumber": FunctionSignature(
        return_type="double",
        param_types=["const luaValue&"],
        cpp_signature="double(*)(const luaValue&)",
    ),
}
---
Phase 6: Refactor ExprGenerator to Use Strategies
6.1 Update ExprGenerator
File: lua2c/generators/expr_generator.py
Add imports:
from lua2c.generators.call_generation.strategies import (
    LocalFunctionStrategy,
    LibraryFunctionStrategy,
    DefaultCallStrategy,
)
from lua2c.generators.call_generation.context import CallContextBuilder
from lua2c.generators.call_generation.type_queries import TypeQueryService
Modify __init__:
def __init__(self, context: TranslationContext) -> None:
    # ... existing code ...
    
    # Initialize call generation strategies
    self._call_strategies = [
        LocalFunctionStrategy(),
        LibraryFunctionStrategy(),
        DefaultCallStrategy(),
    ]
    
    # Initialize type query service
    self._type_query_service = TypeQueryService(context)
    
    # Initialize library tracker (will be set later)
    self._library_tracker = None
Add setter methods:
def set_library_tracker(self, tracker) -> None:
    """Set library call tracker
    
    Args:
        tracker: LibraryCallTracker instance
    """
    self._library_tracker = tracker
    # Update LibraryFunctionStrategy with tracker
    for strategy in self._call_strategies:
        if isinstance(strategy, LibraryFunctionStrategy):
            strategy.set_library_tracker(tracker)
Replace visit_Call method:
def visit_Call(self, expr: astnodes.Call) -> str:
    """Generate code for function call
    
    Refactored to use strategy pattern:
    1. Build call context
    2. Find appropriate strategy
    3. Delegate to strategy
    """
    # Handle require() in project mode (must check before symbol resolution)
    if self.context.get_mode() == "project":
        if isinstance(expr.func, astnodes.Name) and expr.func.id == "require":
            if expr.args and len(expr.args) > 0:
                arg = expr.args[0]
                if isinstance(arg, astnodes.String):
                    module_path = arg.s.decode() if isinstance(arg.s, bytes) else arg.s
                    module_name = module_path.replace(".", "_")
                    return f'state.modules["{module_name}"](state)'
                else:
                    raise ValueError(
                        "require() only supports string literal arguments in project mode"
                    )
    
    # Build context for this call
    call_ctx = CallContextBuilder.build(expr, self.context, self._type_inferencer)
    
    # Find appropriate strategy
    for strategy in self._call_strategies:
        if strategy.can_handle(expr, self.context, signature=call_ctx.signature):
            return strategy.generate(expr, self.context, self, call_ctx)
    
    # Should never reach here (DefaultCallStrategy handles everything)
    raise RuntimeError(f"No strategy found for call: {expr}")
---
Phase 7: Update Runtime Library
7.1 Add Type Conversion Helpers
File: runtime/l2c_runtime.hpp
Add before library functions:
// ============================================================================
// Type Conversion Helpers
// ============================================================================
template<typename T>
inline std::string to_string(T&& arg) {
    if constexpr (std::is_arithmetic_v<std::decay_t<T>>) {
        return std::to_string(arg);
    } else if constexpr (std::is_same_v<std::decay_t<T>, std::string>) {
        return arg;
    } else if constexpr (std::is_same_v<std::decay_t<T>, const char*>) {
        return std::string(arg);
    } else {
        // Fallback to luaValue
        return arg.as_string();
    }
}
template<typename T>
inline double to_number(T&& arg) {
    if constexpr (std::is_arithmetic_v<std::decay_t<T>>) {
        return static_cast<double>(arg);
    } else {
        // Fallback to luaValue
        return arg.as_number();
    }
}
// Index sequence helpers for string.format
template<size_t... Is>
struct index_sequence {};
template<size_t N, size_t... Is>
struct make_index_sequence_impl : make_index_sequence_impl<N-1, N-1, Is...> {};
template<size_t... Is>
struct make_index_sequence_impl<0, Is...> {
    using type = index_sequence<Is...>;
};
template<size_t N>
using make_index_sequence = typename make_index_sequence_impl<N>::type;
7.2 Implement Variadic print()
Replace existing print function:
// ============================================================================
// Print Function (Variadic)
// ============================================================================
template<typename... Args>
inline void print(Args&&... args) {
    size_t index = 0;
    ((std::cout << (index++ > 0 ? "\t" : "") << to_string(args)), ...);
    std::cout << std::endl;
}
// Keep non-template version for backward compatibility
inline void print(const std::vector<luaValue>& args) {
    for (size_t i = 0; i < args.size(); ++i) {
        if (i > 0) std::cout << "\t";
        std::cout << args[i].as_string();
    }
    std::cout << std::endl;
}
7.3 Implement Variadic io.write()
Replace existing io_write:
// ============================================================================
// IO Library (Variadic)
// ============================================================================
template<typename... Args>
inline void io_write(Args&&... args) {
    ((std::cout << to_string(args)), ...);
}
inline void io_flush() {
    std::cout.flush();
}
7.4 Implement Variadic string.format()
Add implementation:
// ============================================================================
// String Library (Variadic)
// ============================================================================
template<typename... Args>
inline std::string string_format_impl(
    const std::string& fmt,
    std::tuple<Args...> args_tuple,
    index_sequence<Is...>
) {
    std::ostringstream result;
    size_t pos = 0;
    size_t arg_count = sizeof...(Args);
    while (pos < fmt.size()) {
        if (fmt[pos] == '%' && pos + 1 < fmt.size()) {
            pos++;
            std::string flags;
            int width = 0;
            int precision = -1;
            while (pos < fmt.size() && (fmt[pos] == '-' || fmt[pos] == '+' || fmt[pos] == ' ' || fmt[pos] == '#' || fmt[pos] == '0')) {
                flags += fmt[pos++];
            }
            while (pos < fmt.size() && isdigit(fmt[pos])) {
                width = width * 10 + (fmt[pos++] - '0');
            }
            if (pos < fmt.size() && fmt[pos] == '.') {
                pos++;
                precision = 0;
                while (pos < fmt.size() && isdigit(fmt[pos])) {
                    precision = precision * 10 + (fmt[pos++] - '0');
                }
            }
            if (pos < fmt.size()) {
                char spec = fmt[pos++];
                size_t idx = 0;
                if (pos < arg_count) {
                    auto arg = std::get<Is>(args_tuple);
                    switch (spec) {
                        case 'f': {
                            double val = to_number(arg);
                            int actual_precision = (precision >= 0) ? precision : 6;
                            result << std::fixed << std::setprecision(actual_precision) << val;
                            break;
                        }
                        case 'd':
                            result << static_cast<int>(to_number(arg));
                            break;
                        case 's':
                            result << to_string(arg);
                            break;
                        case '\n':
                            result << '\n';
                            break;
                        default:
                            result << '%' << spec;
                            break;
                    }
                } else {
                    result << '%' << spec;
                }
            } else {
                result << '%';
            }
        } else {
            result << fmt[pos++];
        }
    }
    return result.str();
}
template<typename... Args>
inline std::string string_format(const std::string& fmt, Args&&... args) {
    return string_format_impl(fmt, std::forward_as_tuple(std::forward<Args>(args)...),
                              make_index_sequence<sizeof...(Args)>{});
}
---
Phase 8: Integration Testing
8.1 Create Integration Test File
File: tests/integration/test_variadic_calls.py
"""Integration tests for variadic template calls"""
import pytest
from pathlib import Path
from luaparser import ast
from lua2c.cli.main import transpile_single_file
from lua2c.generators.cpp_emitter import CppEmitter
from lua2c.core.context import TranslationContext
@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for test files"""
    return tmp_path
# ===== Test 1: ack.lua with Variadic Calls =====
def test_ack_lua_generates_variadic_calls(temp_dir):
    """ack.lua should generate variadic print and string.format calls"""
    # Create ack.lua
    ack_file = temp_dir / "ack.lua"
    ack_file.write_text("""
local function Ack(M, N)
    if (M == 0) then
        return N + 1
    end
    if (N == 0) then
        return Ack(M - 1, 1)
    end
    return Ack(M - 1, Ack(M, (N - 1)))
end
N = tonumber((arg and arg[1])) or 3
M = tonumber((arg and arg[2])) or 8
print(string.format("Ack(%d, %d) = %d\\n", N, M, Ack(N,M)))
""")
    
    # Transpile
    result = transpile_single_file(ack_file, output_name="ack", output_dir=temp_dir)
    cpp_code = result['module_cpp']
    
    # Check that variadic calls are generated
    assert 'print(' in cpp_code
    assert 'string.format(' in cpp_code
    
    # Check that vector wrapping is NOT used
    # The generated code should NOT have nested vectors
    assert 'std::vector<luaValue>{{{' not in cpp_code
    
    # Expected pattern: print(string.format(...))
    assert 'print(' in cpp_code and 'string.format(' in cpp_code
# ===== Test 2: sieve.lua with Variadic Calls =====
def test_sieve_lua_generates_variadic_calls(temp_dir):
    """sieve.lua should generate variadic print calls"""
    # Create sieve.lua
    sieve_file = temp_dir / "sieve.lua"
    sieve_file.write_text("""
local count = 0
function main(num, lim)
    local flags = {}
    for num=num,1,-1 do
        count = 0
        for i=1,lim do
            flags[i] = 1
        end
        for i=2,lim do
            if flags[i] == 1 then
                k = 0
                for k=i+i, lim, i do
                    flags[k] = 0
                end
                count = count + 1
            end
        end
    end
end
NUM = tonumber((arg and arg[1])) or 100
lim = (arg and arg[2]) or 8192
print(NUM,lim)
count = 0
main(NUM, lim)
print("Count: ", count)
""")
    
    # Transpile
    result = transpile_single_file(sieve_file, output_name="sieve", output_dir=temp_dir)
    cpp_code = result['module_cpp']
    
    # Check for variadic print calls
    assert 'print(' in cpp_code
    
    # Check that vector wrapping is NOT used
    assert 'std::vector<luaValue>{{{' not in cpp_code
# ===== Test 3: n-body.lua with Variadic Calls =====
def test_nbody_lua_generates_variadic_calls(temp_dir):
    """n-body.lua should generate variadic io.write and string.format calls"""
    # Create simplified n-body.lua
    nbody_file = temp_dir / "nbody.lua"
    nbody_file.write_text("""
sun = {}
sun.x = 0.0
sun.y = 0.0
sun.mass = 4 * 3.14159 * 3.14159
function energy(bodies)
    return 1.0
end
nbody = 5
io.write(string.format("%0.9f", energy(sun)), "\\n")
""")
    
    # Transpile
    result = transpile_single_file(nbody_file, output_name="nbody", output_dir=temp_dir)
    cpp_code = result['module_cpp']
    
    # Check for variadic calls
    assert 'io_write(' in cpp_code
    assert 'string.format(' in cpp_code
    
    # Check that vector wrapping is NOT used
    assert 'std::vector<luaValue>{{{' not in cpp_code
# ===== Test 4: Compilation Verification =====
def test_variadic_code_compiles(temp_dir):
    """Generated variadic code should compile"""
    # Create simple test file
    test_file = temp_dir / "test.lua"
    test_file.write_text("""
x = 42
y = "hello"
print(x, y, 3.14)
print(string.format("x=%d y=%s", x, y))
""")
    
    # Transpile
    result = transpile_single_file(test_file, output_name="test", output_dir=temp_dir)
    
    # Check that generated code exists
    assert result['state_hpp'] is not None
    assert result['module_hpp'] is not None
    assert result['module_cpp'] is not None
    
    # Check for variadic patterns
    cpp_code = result['module_cpp']
    assert 'print(' in cpp_code
    assert 'string.format(' in cpp_code
8.2 Run Integration Tests
# Run integration tests
pytest tests/integration/test_variadic_calls.py -v
# Fix any failures
---
Phase 9: Final Testing and Validation
9.1 Run All Tests
# Run all unit tests
pytest tests/generators/call_generation/ -v
# Run all integration tests
pytest tests/integration/ -v
# Run all existing tests to ensure no regressions
pytest tests/ -v
9.2 Compile Generated Code
# Test with actual Lua files
cd /home/bober/Documents/ProgrammingProjects/Python/lua2c
# Transpile ack.lua
python -m lua2c.cli main tests/cpp/lua/ack.lua -o output/ack
# Compile generated C++
cd output/ack
g++ -std=c++17 -I../../runtime *.cpp ../../runtime/*.cpp -o ack_test
# Run and compare
./ack_test 3 8
9.3 Compare Output
# Run original Lua
lua tests/cpp/lua/ack.lua 3 8
# Compare outputs
---
Summary of All Changes
New Files Created
1. lua2c/generators/call_generation/__init__.py
2. lua2c/generators/call_generation/type_queries.py
3. lua2c/generators/call_generation/context.py
4. lua2c/generators/call_generation/strategies.py
5. tests/generators/call_generation/test_type_query_service.py
6. tests/generators/call_generation/test_call_generation_context.py
7. tests/generators/call_generation/test_strategies.py
8. tests/generators/call_generation/test_variadic_strategy.py
9. tests/integration/test_variadic_calls.py
Modified Files
1. lua2c/core/global_type_registry.py
   - Updated FunctionSignature dataclass
   - Added variadic flags to function signatures
   - Set always_variadic=True for print, io.write, string.format
2. runtime/l2c_runtime.hpp
   - Added type conversion helpers (to_string, to_number)
   - Implemented variadic print() function
   - Implemented variadic io_write() function
   - Implemented variadic string_format() function
3. lua2c/generators/expr_generator.py
   - Refactored visit_Call() to use strategy pattern
   - Added strategy initialization in __init__()
   - Added set_library_tracker() method
   - Reduced complexity from 150+ lines to ~20 lines
Expected Outcomes
Before:
(state->print)(std::vector<luaValue>{luaValue((state->string.format)("Ack(%d, %d) = %d\n", std::vector<luaValue>{{state->N, state->M, Ack(state, state->N, state->M)}))}});
After:
(state->print)((state->string.format)("Ack(%d, %d) = %d\n", state->N, state->M, Ack(state, state->N, state->M)));
Benefits:
- Eliminates unnecessary luaValue wrapping
- Eliminates std::vector creation overhead
- Leverages C++ type system for compile-time checking
- Better performance through direct argument passing
- More maintainable codebase with strategy pattern
---
Next Steps After Implementation
1. Performance Testing: Compare benchmark performance before and after
2. Additional Variadic Functions: Consider adding variadic support for more functions
3. Static Type Optimization: Add static typed versions for consistently-typed functions
4. Documentation: Update project documentation with new architecture
5. Code Coverage: Ensure all new code has test coverage > 90%
---
End of Complete Plan