"""Tests for expression generator"""

import pytest
from pathlib import Path
from lua2c.core.context import TranslationContext
from lua2c.generators.expr_generator import ExprGenerator

try:
    from luaparser import ast
    from luaparser import astnodes
except ImportError:
    pytest.skip("luaparser not installed", allow_module_level=True)


class TestExprGenerator:
    """Test suite for ExprGenerator"""

    @pytest.fixture
    def context(self):
        """Create translation context for tests"""
        return TranslationContext(Path("/project"), "test_module")

    @pytest.fixture
    def generator(self, context):
        """Create expression generator for tests"""
        return ExprGenerator(context)

    def test_generate_number_integer(self, generator):
        """Test generating integer number"""
        expr = astnodes.Number(n=42)
        result = generator.generate(expr)
        assert result == "luaValue(42)"

    def test_generate_number_float(self, generator):
        """Test generating float number"""
        expr = astnodes.Number(n=3.14)
        result = generator.generate(expr)
        assert result == "luaValue(3.14)"

    def test_generate_string_literal(self, generator, context):
        """Test generating string literal"""
        expr = astnodes.String(s=b"hello", raw="hello")
        result = generator.generate(expr)
        assert "string_pool" in result
        assert "[" in result and "]" in result

    def test_generate_nil(self, generator):
        """Test generating nil"""
        expr = astnodes.Nil()
        result = generator.generate(expr)
        assert result == "luaValue()"

    def test_generate_true(self, generator):
        """Test generating true"""
        expr = astnodes.TrueExpr()
        result = generator.generate(expr)
        assert result == "luaValue(true)"

    def test_generate_false(self, generator):
        """Test generating false"""
        expr = astnodes.FalseExpr()
        result = generator.generate(expr)
        assert result == "luaValue(false)"

    def test_generate_name_local(self, generator, context):
        """Test generating local variable reference"""
        context.define_local("x")
        expr = astnodes.Name(identifier="x")
        result = generator.generate(expr)
        assert result == "x"

    def test_generate_name_undefined(self, generator):
        """Test generating undefined variable reference (global)"""
        expr = astnodes.Name(identifier="undefined_var")
        result = generator.generate(expr)
        assert "state->get_global" in result
        assert "undefined_var" in result

    def test_generate_name_global(self, generator, context):
        """Test generating global variable reference"""
        context.define_global("g")
        expr = astnodes.Name(identifier="g")
        result = generator.generate(expr)
        assert "state->get_global" in result
        assert "g" in result

    def test_generate_binop_add(self, generator):
        """Test generating addition operation"""
        left = astnodes.Number(n=5)
        right = astnodes.Number(n=3)
        expr = astnodes.AddOp(left=left, right=right)
        result = generator.generate(expr)
        assert "+" in result
        assert "5" in result
        assert "3" in result

    def test_generate_binop_sub(self, generator):
        """Test generating subtraction operation"""
        left = astnodes.Number(n=10)
        right = astnodes.Number(n=4)
        expr = astnodes.SubOp(left=left, right=right)
        result = generator.generate(expr)
        assert "-" in result

    def test_generate_binop_mul(self, generator):
        """Test generating multiplication operation"""
        left = astnodes.Number(n=6)
        right = astnodes.Number(n=7)
        expr = astnodes.MultOp(left=left, right=right)
        result = generator.generate(expr)
        assert "*" in result

    def test_generate_binop_div(self, generator):
        """Test generating division operation"""
        left = astnodes.Number(n=20)
        right = astnodes.Number(n=4)
        expr = astnodes.FloatDivOp(left=left, right=right)
        result = generator.generate(expr)
        assert "/" in result

    def test_generate_binop_eq(self, generator):
        """Test generating equality operation"""
        left = astnodes.Number(n=5)
        right = astnodes.Number(n=5)
        expr = astnodes.EqToOp(left=left, right=right)
        result = generator.generate(expr)
        assert "==" in result

    def test_generate_binop_lt(self, generator):
        """Test generating less-than operation"""
        left = astnodes.Number(n=3)
        right = astnodes.Number(n=5)
        expr = astnodes.LessThanOp(left=left, right=right)
        result = generator.generate(expr)
        assert "<" in result

    def test_generate_unop_neg(self, generator):
        """Test generating negation operation"""
        operand = astnodes.Number(n=5)
        expr = astnodes.UMinusOp(operand=operand)
        result = generator.generate(expr)
        assert "-" in result

    def test_generate_unop_not(self, generator):
        """Test generating logical not operation"""
        operand = astnodes.TrueExpr()
        expr = astnodes.ULNotOp(operand=operand)
        result = generator.generate(expr)
        assert "!" in result
        assert "is_truthy" in result

    def test_generate_unop_len(self, generator):
        """Test generating length operation"""
        operand = astnodes.String(s=b"hello", raw="hello")
        expr = astnodes.ULengthOP(operand=operand)
        result = generator.generate(expr)
        assert "l2c_len" in result

    def test_generate_call_no_args(self, generator):
        """Test generating function call with no arguments"""
        func = astnodes.Name(identifier="print")
        expr = astnodes.Call(func=func, args=[])
        result = generator.generate(expr)
        assert "(" in result
        assert ")" in result
        assert "{}" in result

    def test_generate_call_with_args(self, generator):
        """Test generating function call with arguments"""
        func = astnodes.Name(identifier="print")
        args = [astnodes.String(s=b"hello", raw="hello"), astnodes.Number(n=42)]
        expr = astnodes.Call(func=func, args=args)
        result = generator.generate(expr)
        assert "(" in result
        assert ")" in result

    def test_generate_dots(self, generator):
        """Test generating varargs"""
        expr = astnodes.Dots()
        result = generator.generate(expr)
        assert "varargs" in result

    def test_generate_and_or_operators(self, generator):
        """Test generating and/or operators"""
        left = astnodes.Number(n=1)
        right = astnodes.Number(n=2)
        and_expr = astnodes.AndLoOp(left=left, right=right)
        result = generator.generate(and_expr)
        assert "is_truthy" in result
        assert "?" in result
        assert ":" in result

        or_expr = astnodes.OrLoOp(left=left, right=right)
        result = generator.generate(or_expr)
        assert "is_truthy" in result
        assert "?" in result
        assert ":" in result

    def test_generate_index(self, generator):
        """Test generating table index"""
        table = astnodes.Name(identifier="t")
        key = astnodes.Number(n=1)
        expr = astnodes.Index(idx=key, value=table)
        result = generator.generate(expr)
        assert "[" in result
        assert "]" in result

    def test_generate_field(self, generator):
        """Test generating table field access"""
        table = astnodes.Name(identifier="obj")
        field_name = astnodes.Name(identifier="x")
        expr = astnodes.Field(key=field_name, value=table)
        result = generator.generate(expr)
        assert "[" in result
        assert "]" in result
        assert "string_pool" in result

    def test_generate_invoke(self, generator):
        """Test generating method invocation"""
        source = astnodes.Name(identifier="obj")
        func = astnodes.Name(identifier="method")
        expr = astnodes.Invoke(source=source, func=func, args=[])
        result = generator.generate(expr)
        assert "[" in result
        assert "]" in result
        assert "(" in result
        assert ")" in result

    def test_generate_table_constructor(self, generator):
        """Test generating table constructor"""
        expr = astnodes.Table(fields=[])
        result = generator.generate(expr)
        assert "new_table" in result

    def test_generate_anonymous_function(self, generator):
        """Test generating anonymous function"""
        body = astnodes.Block(body=[])
        expr = astnodes.AnonymousFunction(args=[], body=body)
        result = generator.generate(expr)
        assert "new_closure" in result

    def test_generate_local_function_call(self, generator, context):
        """Test generating local function call with state parameter"""
        # Define a local function symbol
        context.symbol_table.add_function("add", is_global=False)
        
        # Generate call to local function
        func = astnodes.Name(identifier="add")
        args = [astnodes.Number(n=5), astnodes.Number(n=3)]
        expr = astnodes.Call(func=func, args=args)
        result = generator.generate(expr)
        
        # Local functions should be called with state parameter
        assert "add(state," in result
        assert "luaValue(5)" in result
        assert "luaValue(3)" in result

    def test_generate_global_function_call(self, generator):
        """Test generating global function call with argument list"""
        # Global function (not defined as local symbol)
        func = astnodes.Name(identifier="print")
        args = [astnodes.Number(n=42)]
        expr = astnodes.Call(func=func, args=args)
        result = generator.generate(expr)
        
        # Global functions should be called with luaValue operator()
        # Since print is not a local symbol, it resolves to state->get_global("print")
        assert "state->get_global" in result or "(" in result
        assert "luaValue(42)" in result
        assert "{luaValue(42)})" in result or "{luaValue(42)}" in result
