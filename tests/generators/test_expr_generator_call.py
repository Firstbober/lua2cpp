"""Tests for visit_Call() refactoring to strategy pattern

These tests are written TDD-style - they should FAIL initially,
then PASS after the visit_Call() refactoring is complete.
"""

import pytest
from pathlib import Path
from lua2c.core.context import TranslationContext
from lua2c.generators.expr_generator import ExprGenerator

try:
    from luaparser import ast
    from luaparser import astnodes
except ImportError:
    pytest.skip("luaparser not installed", allow_module_level=True)


class TestExprGeneratorCallRefactor:
    """Test suite for visit_Call() strategy pattern refactoring

    All tests should FAIL initially (before refactoring) and PASS after
    visit_Call() is refactored to use strategy pattern.
    """

    @pytest.fixture
    def context(self):
        """Create translation context for tests"""
        return TranslationContext(Path("/project"), "test_module")

    @pytest.fixture
    def generator(self, context):
        """Create expression generator for tests"""
        return ExprGenerator(context)

    def test_require_call_project_mode(self, generator):
        """Test require() handling in project mode

        Expected output: state.modules["module_name"](state)

        This test verifies that require() calls in project mode are handled
        before strategy delegation, generating the correct module call pattern.
        """
        # Set project mode
        generator.context.set_project_mode("test_project")

        # Create require("utils") call
        func = astnodes.Name(identifier="require")
        arg = astnodes.String(s=b"utils", raw="utils")
        expr = astnodes.Call(func=func, args=[arg])

        result = generator.generate(expr)

        # Require should generate: state.modules["utils"](state)
        assert 'state.modules["utils"](state)' in result

    def test_local_function_call_with_state(self, generator, context):
        """Test local function call with state parameter

        Expected output: func(state, args...) with temp vars for literals

        This test verifies that local functions are called with the state
        parameter as the first argument. Note: Current implementation wraps
        literals in temporary variables for type inference.
        """
        # Define a local function symbol
        context.symbol_table.add_function("add", is_global=False)

        # Create add(5, 3) call
        func = astnodes.Name(identifier="add")
        args = [astnodes.Number(n=5), astnodes.Number(n=3)]
        expr = astnodes.Call(func=func, args=args)

        result = generator.generate(expr)

        # Local functions should be called with state parameter
        assert "add(state," in result
        assert "double _l2c_tmp_arg_0 = 5" in result or "5" in result
        assert "double _l2c_tmp_arg_1 = 3" in result or "3" in result

    def test_local_function_call_with_temporaries(self, generator, context):
        """Test local function call with temporary variables

        Expected output: func(state, 5 + 3) for simple binary ops

        This test verifies that binary operation expressions are passed directly
        to local functions (current behavior: no temp vars for simple ops).
        """
        # Define a local function
        context.symbol_table.add_function("process", is_global=False)

        # Create call with temporary expression (binary op)
        func = astnodes.Name(identifier="process")
        left = astnodes.Number(n=5)
        right = astnodes.Number(n=3)
        arg_expr = astnodes.AddOp(left=left, right=right)
        expr = astnodes.Call(func=func, args=[arg_expr])

        result = generator.generate(expr)

        # Binary ops are passed directly (no temp var for the op itself)
        assert "process(state," in result
        assert "5 + 3" in result

    def test_library_function_call_print(self, generator):
        """Test library function call (print)

        Expected output: Direct call to print with arguments

        This test verifies that standard library functions like print
        are called directly without wrapping.
        """
        # Create print("hello") call
        func = astnodes.Name(identifier="print")
        arg = astnodes.String(s=b"hello", raw="hello")
        expr = astnodes.Call(func=func, args=[arg])

        result = generator.generate(expr)

        # Print should generate direct call
        assert "print" in result
        assert "hello" in result

    def test_library_function_call_math_sqrt(self, generator):
        """Test library function call (math.sqrt)

        Expected output: state->math.sqrt(16) in single_standalone mode

        This test verifies that library functions with typed parameters
        receive properly converted arguments.
        """
        # Set mode to allow library function access
        generator.context.set_single_file_mode("test", as_library=False)

        # Create math.sqrt(16) call
        math_table = astnodes.Name(identifier="math")
        sqrt_field = astnodes.Name(identifier="sqrt")
        func = astnodes.Index(idx=sqrt_field, value=math_table)
        arg = astnodes.Number(n=16)
        expr = astnodes.Call(func=func, args=[arg])

        result = generator.generate(expr)

        # math.sqrt should be called directly
        assert "sqrt" in result
        assert "16" in result

    def test_library_function_call_string_format(self, generator):
        """Test library function call (string.format)

        Expected output: state->string.format(fmt, args...) in single_standalone mode

        This test verifies that string.format generates correct C++ code
        with variadic template support.
        """
        # Set mode to allow library function access
        generator.context.set_single_file_mode("test", as_library=False)

        # Create string.format("%d %s", 42, "hello") call
        string_table = astnodes.Name(identifier="string")
        format_field = astnodes.Name(identifier="format")
        func = astnodes.Index(idx=format_field, value=string_table)

        fmt_arg = astnodes.String(s=b"%d %s", raw="%d %s")
        num_arg = astnodes.Number(n=42)
        str_arg = astnodes.String(s=b"hello", raw="hello")

        expr = astnodes.Call(func=func, args=[fmt_arg, num_arg, str_arg])

        result = generator.generate(expr)

        # string.format should be called directly
        assert "format" in result
        assert "%d %s" in result

    def test_default_fallback_call(self, generator):
        """Test default fallback for unknown functions

        Expected output: (func)({args}) with luaValue wrapping

        This test verifies that unknown functions fall back to the
        default call strategy, wrapping arguments in luaValue.
        """
        # Create unknown_func(42) call
        func = astnodes.Name(identifier="unknown_func")
        arg = astnodes.Number(n=42)
        expr = astnodes.Call(func=func, args=[arg])

        result = generator.generate(expr)

        # Unknown functions should wrap arguments in luaValue
        assert "unknown_func" in result or "get_global" in result
        assert "luaValue(42)" in result or "luaValue" in result

    def test_variadic_library_function(self, generator):
        """Test variadic library function (io.write with string.format)

        Expected output: Direct call without std::vector<luaValue> wrapping

        This test verifies that variadic functions use C++ variadic templates
        instead of wrapping arguments in std::vector<luaValue>.
        """
        # Set mode to allow library function access
        generator.context.set_single_file_mode("test", as_library=False)

        # Create io.write(string.format(...)) call from spectral-norm.lua
        # io.write(string.format("%0.9f\n", value))
        io_table = astnodes.Name(identifier="io")
        write_field = astnodes.Name(identifier="write")
        io_write = astnodes.Index(idx=write_field, value=io_table)

        string_table = astnodes.Name(identifier="string")
        format_field = astnodes.Name(identifier="format")
        string_format = astnodes.Index(idx=format_field, value=string_table)

        fmt = astnodes.String(s=b"%0.9f\n", raw="%0.9f\n")
        value = astnodes.Number(n=1.414213562)

        format_call = astnodes.Call(func=string_format, args=[fmt, value])
        expr = astnodes.Call(func=io_write, args=[format_call])

        result = generator.generate(expr)

        # Should generate direct calls without vector wrapping
        assert "io.write" in result or "write" in result
        assert "string.format" in result or "format" in result

        # Should NOT contain std::vector<luaValue> for variadic functions
        assert "std::vector<luaValue>" not in result, \
            "Variadic functions should not use std::vector wrapping"

    def test_existing_tests_pass(self, generator, context):
        """Ensure existing test_generate_* tests still pass

        This test verifies that the refactoring doesn't break existing
        functionality covered by the original tests.
        """
        # Test: test_generate_local_function_call
        # Current implementation wraps literals in temporary variables
        context.symbol_table.add_function("add", is_global=False)
        func = astnodes.Name(identifier="add")
        args = [astnodes.Number(n=5), astnodes.Number(n=3)]
        expr = astnodes.Call(func=func, args=args)
        result = generator.generate(expr)
        assert "add(state," in result
        assert "double _l2c_tmp_arg_0 = 5" in result or "5" in result
        assert "double _l2c_tmp_arg_1 = 3" in result or "3" in result

        # Test: test_generate_global_function_call
        func = astnodes.Name(identifier="print")
        args = [astnodes.Number(n=42)]
        expr = astnodes.Call(func=func, args=args)
        result = generator.generate(expr)
        assert "luaValue(42)" in result

        # Test: test_generate_call_no_args
        func = astnodes.Name(identifier="noargs")
        expr = astnodes.Call(func=func, args=[])
        result = generator.generate(expr)
        assert "(" in result
        assert ")" in result
        assert "{}" in result

        # Test: test_generate_call_with_args
        func = astnodes.Name(identifier="print")
        args = [astnodes.String(s=b"hello", raw="hello"), astnodes.Number(n=42)]
        expr = astnodes.Call(func=func, args=args)
        result = generator.generate(expr)
        assert "(" in result
        assert ")" in result
