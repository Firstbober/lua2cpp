"""Test suite for Bug #2: Local Function Recursive Calls

Tests that recursive calls to local functions use the correct calling convention:
- Correct: func(state, arg1, arg2, ...)
- Incorrect: (state->func)({arg1, arg2, ...})
"""

import pytest
from pathlib import Path
from luaparser import ast
from lua2c.core.context import TranslationContext
from lua2c.generators.expr_generator import ExprGenerator


class TestLocalFunctionRecursiveCalls:
    """Test that local function recursive calls are generated correctly"""

    @pytest.fixture
    def context(self):
        """Create context for testing"""
        ctx = TranslationContext(Path("/project"), "test_module")
        ctx.set_single_file_mode("test", as_library=False)
        return ctx

    def test_local_function_registration(self, context):
        """Test that local functions are registered in the symbol table"""
        # First, register the local function (simulating _collect_functions)
        func_name = "factorial"
        context.define_function(func_name, is_global=False)

        # Now verify the symbol can be resolved
        symbol = context.resolve_symbol(func_name)
        assert symbol is not None
        assert not symbol.is_global  # Local functions are not global
        assert symbol.is_function

    def test_recursive_call_uses_local_pattern(self, context):
        """Test that recursive calls use func(state, args) pattern"""
        # Register the local function
        context.define_local("Ack")
        context.enter_function()

        # Generate code for a recursive call
        expr_gen = ExprGenerator(context)
        tree = ast.parse("return Ack(M - 1, 1)")
        call_expr = tree.body.body[0].values[0]

        result = expr_gen.generate(call_expr)

        # Should use Ack(state, ...) not (state->Ack)({...})
        assert "Ack(state" in result
        assert "(state->Ack)" not in result
        assert "({{" not in result  # No old-style brace initialization

        print(f"Generated code: {result}")

    def test_local_function_call_vs_global_call(self, context):
        """Test that local function calls differ from global calls"""
        # Register a local function
        context.define_local("myFunc")
        context.enter_function()

        expr_gen = ExprGenerator(context)

        # Local function call
        tree = ast.parse("return myFunc(x, y)")
        call_expr = tree.body.body[0].values[0]
        local_call = expr_gen.generate(call_expr)

        # Should use myFunc(state, x, y) pattern
        assert "myFunc(state" in local_call
        assert "(state->myFunc)" not in local_call

        context.exit_function()

        # Global function call (no local registration)
        tree = ast.parse("return print(x, y)")
        call_expr = tree.body.body[0].values[0]
        global_call = expr_gen.generate(call_expr)

        # Should use (state->print)({x, y}) pattern
        assert "(state->print)" in global_call
        # Note: global calls may have {args} for library functions

        print(f"Local call: {local_call}")
        print(f"Global call: {global_call}")
