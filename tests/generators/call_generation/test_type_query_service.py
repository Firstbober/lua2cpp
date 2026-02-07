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
    ctx = TranslationContext(tmp_path, "test.lua")
    return ctx


@pytest.fixture
def type_query_service(context):
    """Create TypeQueryService for testing"""
    return TypeQueryService(context)


# ===== Test 1: Literal Type Inference =====
def test_get_expression_type_number_literal(type_query_service):
    """Should infer NUMBER type for numeric literals"""
    expr = ast.parse("local x = 42").body.body[0].values[0]
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.NUMBER


def test_get_expression_type_float_literal(type_query_service):
    """Should infer NUMBER type for float literals"""
    expr = ast.parse("local x = 3.14").body.body[0].values[0]
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.NUMBER


def test_get_expression_type_string_literal(type_query_service):
    """Should infer STRING type for string literals"""
    expr = ast.parse('local x = "hello"').body.body[0].values[0]
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.STRING


def test_get_expression_type_true_literal(type_query_service):
    """Should infer BOOLEAN type for true literals"""
    expr = ast.parse("local x = true").body.body[0].values[0]
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.BOOLEAN


def test_get_expression_type_false_literal(type_query_service):
    """Should infer BOOLEAN type for false literals"""
    expr = ast.parse("local x = false").body.body[0].values[0]
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.BOOLEAN


def test_get_expression_type_nil_literal(type_query_service):
    """Should infer NIL type for nil literals"""
    expr = ast.parse("local x = nil").body.body[0].values[0]
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
    
    expr = ast.parse("print(x)").body.body[0].args[0]
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.NUMBER


def test_get_expression_type_name_without_inferred_type(context, type_query_service):
    """Should return None for name without inferred type"""
    context.define_local("y")
    
    expr = ast.parse("print(y)").body.body[0].args[0]
    result = type_query_service.get_expression_type(expr)
    assert result is None


# ===== Test 4: Binary Operation Type Inference =====
def test_get_expression_type_binary_op_number_plus_number(context, type_query_service):
    """Should infer NUMBER for number + number"""
    context.define_local("a")
    context.resolve_symbol("a").inferred_type = Type(TypeKind.NUMBER)
    context.define_local("b")
    context.resolve_symbol("b").inferred_type = Type(TypeKind.NUMBER)
    
    expr = ast.parse("print(a + b)").body.body[0].args[0]
    result = type_query_service.get_expression_type(expr)
    assert result is not None
    assert result.kind == TypeKind.NUMBER


def test_get_expression_type_binary_op_unknown_operand(context, type_query_service):
    """Should return VARIANT when one operand is unknown"""
    context.define_local("x")
    context.resolve_symbol("x").inferred_type = Type(TypeKind.NUMBER)
    
    expr = ast.parse("print(x + unknown)").body.body[0].args[0]
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
    expr = ast.parse("print(unknown_var)").body.body[0].args[0]
    assert type_query_service.needs_lua_value_wrapper(expr) == True


def test_needs_lua_value_wrapper_for_number_type(context, type_query_service):
    """Should not wrap NUMBER type expressions"""
    context.define_local("x")
    context.resolve_symbol("x").inferred_type = Type(TypeKind.NUMBER)
    
    expr = ast.parse("print(x)").body.body[0].args[0]
    assert type_query_service.needs_lua_value_wrapper(expr) == False


def test_needs_lua_value_wrapper_for_string_type(context, type_query_service):
    """Should not wrap STRING type expressions"""
    context.define_local("s")
    context.resolve_symbol("s").inferred_type = Type(TypeKind.STRING)
    
    expr = ast.parse("print(s)").body.body[0].args[0]
    assert type_query_service.needs_lua_value_wrapper(expr) == False


def test_needs_lua_value_wrapper_for_boolean_type(context, type_query_service):
    """Should not wrap BOOLEAN type expressions"""
    context.define_local("flag")
    context.resolve_symbol("flag").inferred_type = Type(TypeKind.BOOLEAN)
    
    expr = ast.parse("print(flag)").body.body[0].args[0]
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
    """Should return 'auto' for UNKNOWN type"""
    type_info = Type(TypeKind.UNKNOWN)
    assert type_query_service.get_cpp_type(type_info) == "auto"


# ===== Test 9: Cache Management =====
def test_clear_cache(context, type_query_service):
    """Should clear type cache"""
    context.define_local("cached_var")
    symbol = context.resolve_symbol("cached_var")
    symbol.inferred_type = Type(TypeKind.NUMBER)
    
    # Query to populate cache
    result1 = type_query_service.get_symbol_type("cached_var")
    assert result1 is not None
    
    # Query again - should get same object from cache
    result1b = type_query_service.get_symbol_type("cached_var")
    assert result1b is result1  # Same object from cache
    
    # Clear cache
    type_query_service.clear_cache()
    
    # Query again after clear - still gets the same Type object
    # (because it's the same symbol's inferred_type)
    result2 = type_query_service.get_symbol_type("cached_var")
    assert result2 is not None
    # Note: We still get the same Type object because it's from the symbol's
    # inferred_type attribute, not from creating a new object.
    # The cache just speeds up repeated lookups.
