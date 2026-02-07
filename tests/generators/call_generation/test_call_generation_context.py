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
    
    expr = ast.parse("foo(x)").body.body[0]
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
    
    expr = ast.parse("bar(a, b)").body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    
    assert ctx.func_path == "bar"
    assert ctx.is_local == True
    assert ctx.num_args == 2
    assert len(ctx.arg_types) == 2


# ===== Test 2: Library Function Call Context =====
def test_build_print_call_context(context):
    """Should build context for print() call"""
    expr = ast.parse('print("hello")').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    
    assert ctx.func_path == "print"
    assert ctx.is_local == False
    assert ctx.signature is not None
    assert ctx.signature.return_type == "void"
    assert ctx.num_args == 1
    assert ctx.num_params == 1  # Has one parameter: vector<luaValue>


def test_build_string_format_call_context(context):
    """Should build context for string.format() call"""
    expr = ast.parse('string.format("%s %d", x, 42)').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    
    assert ctx.func_path == "string.format"
    assert ctx.is_local == False
    assert ctx.signature is not None
    assert ctx.signature.return_type == "std::string"
    assert ctx.num_args == 3
    assert ctx.num_params == 2  # Format string and vector<luaValue>


def test_build_math_sqrt_call_context(context):
    """Should build context for math.sqrt() call"""
    expr = ast.parse("math.sqrt(x)").body.body[0]
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
    expr = ast.parse('print(x)').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    ctx.signature.always_variadic = True
    
    assert ctx.needs_variadic() == True


def test_needs_variadic_signature_flag(context):
    """Should return True when signature.is_variadic is True"""
    expr = ast.parse('string.format("test", x)').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    ctx.signature.is_variadic = True
    
    assert ctx.needs_variadic() == True


def test_needs_variadic_library_tracker(context):
    """Should query library_tracker for variadic decision"""
    # Mock library tracker
    class MockTracker:
        def is_variadic(self, func_path):
            return func_path == "print"
    
    expr = ast.parse('print(x)').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    
    tracker = MockTracker()
    assert ctx.needs_variadic(library_tracker=tracker) == True
    
    # Different function
    expr2 = ast.parse('math.sqrt(x)').body.body[0]
    ctx2 = CallContextBuilder.build(expr2, context)
    assert ctx2.needs_variadic(library_tracker=tracker) == False


def test_needs_vector_detection(context):
    """Should detect functions with vector<luaValue> parameters"""
    # io.write uses vector<luaValue>
    expr = ast.parse('io.write(x)').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    
    assert ctx.needs_vector() == True
    
    # math.sqrt does not use vector
    expr2 = ast.parse('math.sqrt(x)').body.body[0]
    ctx2 = CallContextBuilder.build(expr2, context)
    
    assert ctx2.needs_vector() == False


def test_has_fixed_params(context):
    """Should detect functions with fixed parameters"""
    # string.format has 1 fixed param (format string) + vector param
    expr = ast.parse('string.format("test", x)').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    
    assert ctx.has_fixed_params() == True
    assert ctx.get_fixed_param_count() == 2
    
    # print has no fixed params (uses vector only)
    expr2 = ast.parse('print(x)').body.body[0]
    ctx2 = CallContextBuilder.build(expr2, context)
    
    assert ctx2.has_fixed_params() == True
    assert ctx2.get_fixed_param_count() == 1  # Just vector<luaValue>


# ===== Test 4: Function Path Extraction =====
def test_get_function_path_standalone(context):
    """Should extract path for standalone function (print)"""
    expr = ast.parse('print(x)').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.func_path == "print"


def test_get_function_path_module_function(context):
    """Should extract path for module.function (string.format)"""
    expr = ast.parse('string.format("test")').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.func_path == "string.format"


def test_get_function_path_math_function(context):
    """Should extract path for math function (math.sqrt)"""
    expr = ast.parse("math.sqrt(x)").body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.func_path == "math.sqrt"


# ===== Test 5: Argument Type Inference =====
def test_infer_arg_types_literals(context):
    """Should infer types for literal arguments"""
    expr = ast.parse('print(42, "hello", true)').body.body[0]
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
    
    expr = ast.parse('print(x, y)').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    
    assert len(ctx.arg_types) == 2
    assert ctx.arg_types[0].kind == TypeKind.NUMBER
    assert ctx.arg_types[1].kind == TypeKind.STRING


def test_infer_arg_types_mixed(context):
    """Should handle mixed literal and symbol arguments"""
    context.define_local("x")
    context.resolve_symbol("x").inferred_type = Type(TypeKind.NUMBER)
    
    expr = ast.parse('print(x, 42, "text")').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    
    assert len(ctx.arg_types) == 3
    assert ctx.arg_types[0].kind == TypeKind.NUMBER
    assert ctx.arg_types[1].kind == TypeKind.NUMBER
    assert ctx.arg_types[2].kind == TypeKind.STRING


# ===== Test 6: Return Type Inference =====
def test_infer_return_type_void(context):
    """Should infer void return type for print"""
    expr = ast.parse('print(x)').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.return_type.kind == TypeKind.NIL  # void maps to NIL in TypeKind


def test_infer_return_type_std_string(context):
    """Should infer std::string return type for string.format"""
    expr = ast.parse('string.format("test")').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.return_type.kind == TypeKind.STRING


def test_infer_return_type_double(context):
    """Should infer double return type for math.sqrt"""
    expr = ast.parse("math.sqrt(x)").body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.return_type.kind == TypeKind.NUMBER


def test_infer_return_type_lua_value(context):
    """Should infer luaValue return type for functions without signature"""
    context.define_function("custom", is_global=False)
    expr = ast.parse('custom(x)').body.body[0]
    ctx = CallContextBuilder.build(expr, context)
    assert ctx.return_type.kind == TypeKind.UNKNOWN
