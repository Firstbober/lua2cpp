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
        assert result == "L2C_NUMBER_INT(42)"

    def test_generate_number_float(self, generator):
        """Test generating float number"""
        expr = astnodes.Number(n=3.14)
        result = generator.generate(expr)
        assert result == "L2C_NUMBER_FLOAT(3.14)"

    def test_generate_string_literal(self, generator, context):
        """Test generating string literal"""
        expr = astnodes.String(s=b"hello", raw="hello")
        result = generator.generate(expr)
        assert result.startswith("L2C_STRING_LITERAL(")
        assert result.endswith(")")

    def test_generate_nil(self, generator):
        """Test generating nil"""
        expr = astnodes.Nil()
        result = generator.generate(expr)
        assert result == "L2C_NIL"

    def test_generate_true(self, generator):
        """Test generating true"""
        expr = astnodes.TrueExpr()
        result = generator.generate(expr)
        assert result == "L2C_TRUE"

    def test_generate_false(self, generator):
        """Test generating false"""
        expr = astnodes.FalseExpr()
        result = generator.generate(expr)
        assert result == "L2C_FALSE"

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
        assert "L2C_GET_GLOBAL" in result
        assert "undefined_var" in result

    def test_generate_name_global(self, generator, context):
        """Test generating global variable reference"""
        context.define_global("g")
        expr = astnodes.Name(identifier="g")
        result = generator.generate(expr)
        assert "L2C_GET_GLOBAL" in result
        assert "g" in result

    def test_generate_binop_add(self, generator):
        """Test generating addition operation"""
        left = astnodes.Number(n=5)
        right = astnodes.Number(n=3)
        expr = astnodes.AddOp(left=left, right=right)
        result = generator.generate(expr)
        assert "L2C_BINOP" in result
        assert "L2C_OP_ADD" in result

    def test_generate_binop_sub(self, generator):
        """Test generating subtraction operation"""
        left = astnodes.Number(n=10)
        right = astnodes.Number(n=4)
        expr = astnodes.SubOp(left=left, right=right)
        result = generator.generate(expr)
        assert "L2C_BINOP" in result
        assert "L2C_OP_SUB" in result

    def test_generate_binop_mul(self, generator):
        """Test generating multiplication operation"""
        left = astnodes.Number(n=6)
        right = astnodes.Number(n=7)
        expr = astnodes.MultOp(left=left, right=right)
        result = generator.generate(expr)
        assert "L2C_BINOP" in result
        assert "L2C_OP_MUL" in result

    def test_generate_binop_div(self, generator):
        """Test generating division operation"""
        left = astnodes.Number(n=20)
        right = astnodes.Number(n=4)
        expr = astnodes.FloatDivOp(left=left, right=right)
        result = generator.generate(expr)
        assert "L2C_BINOP" in result
        assert "L2C_OP_DIV" in result

    def test_generate_binop_eq(self, generator):
        """Test generating equality operation"""
        left = astnodes.Number(n=5)
        right = astnodes.Number(n=5)
        expr = astnodes.EqToOp(left=left, right=right)
        result = generator.generate(expr)
        assert "L2C_BINOP" in result
        assert "L2C_OP_EQ" in result

    def test_generate_binop_lt(self, generator):
        """Test generating less-than operation"""
        left = astnodes.Number(n=3)
        right = astnodes.Number(n=5)
        expr = astnodes.LessThanOp(left=left, right=right)
        result = generator.generate(expr)
        assert "L2C_BINOP" in result
        assert "L2C_OP_LT" in result

    def test_generate_unop_neg(self, generator):
        """Test generating negation operation"""
        operand = astnodes.Number(n=5)
        expr = astnodes.UMinusOp(operand=operand)
        result = generator.generate(expr)
        assert "L2C_UNOP" in result
        assert "L2C_OP_NEG" in result

    def test_generate_unop_not(self, generator):
        """Test generating logical not operation"""
        operand = astnodes.TrueExpr()
        expr = astnodes.ULNotOp(operand=operand)
        result = generator.generate(expr)
        assert "L2C_UNOP" in result
        assert "L2C_OP_NOT" in result

    def test_generate_unop_len(self, generator):
        """Test generating length operation"""
        operand = astnodes.String(s=b"hello", raw="hello")
        expr = astnodes.ULengthOP(operand=operand)
        result = generator.generate(expr)
        assert "L2C_UNOP" in result
        assert "L2C_OP_LEN" in result

    def test_generate_call_no_args(self, generator):
        """Test generating function call with no arguments"""
        func = astnodes.Name(identifier="print")
        expr = astnodes.Call(func=func, args=[])
        result = generator.generate(expr)
        assert "L2C_CALL" in result
        assert "0" in result  # Zero arguments

    def test_generate_call_with_args(self, generator):
        """Test generating function call with arguments"""
        func = astnodes.Name(identifier="print")
        args = [astnodes.String(s=b"hello", raw="hello"), astnodes.Number(n=42)]
        expr = astnodes.Call(func=func, args=args)
        result = generator.generate(expr)
        assert "L2C_CALL" in result
        assert "2" in result  # Two arguments

    def test_generate_dots(self, generator):
        """Test generating varargs"""
        expr = astnodes.Dots()
        result = generator.generate(expr)
        assert result == "L2C_VARARGS"

    def test_generate_unsupported_binop(self, generator):
        """Test that unsupported binary operators raise error"""
        left = astnodes.Number(n=1)
        right = astnodes.Number(n=2)
        expr = astnodes.AndLoOp(left=left, right=right)
        with pytest.raises(NotImplementedError):
            generator.generate(expr)

    def test_generate_unsupported_node_type(self, generator):
        """Test that unsupported node types raise error"""
        expr = astnodes.Index(idx=astnodes.Number(n=1), value=astnodes.Number(n=2))
        with pytest.raises(NotImplementedError):
            generator.generate(expr)

    def test_generate_invoke_not_implemented(self, generator):
        """Test that method invocation is not implemented"""
        source = astnodes.Name(identifier="obj")
        func = astnodes.Name(identifier="method")
        expr = astnodes.Invoke(source=source, func=func, args=[])
        with pytest.raises(NotImplementedError):
            generator.generate(expr)

    def test_generate_table_constructor_not_implemented(self, generator):
        """Test that table constructor is not implemented"""
        expr = astnodes.Table(fields=[])
        with pytest.raises(NotImplementedError):
            generator.generate(expr)

    def test_generate_anonymous_function_not_implemented(self, generator):
        """Test that anonymous function is not implemented"""
        body = astnodes.Block(body=[])
        expr = astnodes.AnonymousFunction(args=[], body=body)
        with pytest.raises(NotImplementedError):
            generator.generate(expr)
