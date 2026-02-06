"""Tests for statement generator"""

import pytest
from pathlib import Path
from lua2c.core.context import TranslationContext
from lua2c.generators.stmt_generator import StmtGenerator

try:
    from luaparser import ast
    from luaparser import astnodes
except ImportError:
    pytest.skip("luaparser not installed", allow_module_level=True)


class TestStmtGenerator:
    """Test suite for StmtGenerator"""

    @pytest.fixture
    def context(self):
        """Create translation context for tests"""
        return TranslationContext(Path("/project"), "test_module")

    @pytest.fixture
    def generator(self, context):
        """Create statement generator for tests"""
        return StmtGenerator(context)

    def test_generate_assignment_single(self, generator):
        """Test generating single assignment"""
        src = "x = 42"
        tree = ast.parse(src)
        assign = tree.body.body[0]
        result = generator.generate(assign)
        assert "=" in result
        assert ";" in result

    def test_generate_assignment_multiple(self, generator):
        """Test generating multiple assignment"""
        src = "x, y = 1, 2"
        tree = ast.parse(src)
        assign = tree.body.body[0]
        result = generator.generate(assign)
        assert ";" in result

    def test_generate_local_assignment_single(self, generator):
        """Test generating local single variable assignment"""
        src = "local x = 42"
        tree = ast.parse(src)
        local_assign = tree.body.body[0]
        result = generator.generate(local_assign)
        assert "luaValue" in result
        assert "=" in result
        assert ";" in result

    def test_generate_local_assignment_no_value(self, generator):
        """Test generating local variable without value"""
        src = "local x"
        tree = ast.parse(src)
        local_assign = tree.body.body[0]
        result = generator.generate(local_assign)
        assert "luaValue" in result
        assert "L2C_NIL" in result

    def test_generate_local_function(self, generator, context):
        """Test generating local function definition"""
        src = "local function add(a, b) return a + b end"
        tree = ast.parse(src)
        local_func = tree.body.body[0]
        result = generator.generate(local_func)
        assert "luaValue" in result
        assert "add" in result
        assert "(" in result
        assert ")" in result

    def test_generate_call_statement(self, generator):
        """Test generating function call as statement"""
        src = "print('hello')"
        tree = ast.parse(src)
        call = tree.body.body[0]
        result = generator.generate(call)
        assert "L2C_CALL" in result
        assert ";" in result

    def test_generate_return_no_value(self, generator):
        """Test generating return with no value"""
        src = "return"
        tree = ast.parse(src)
        ret = tree.body.body[0]
        result = generator.generate(ret)
        assert "return" in result

    def test_generate_return_single_value(self, generator):
        """Test generating return with single value"""
        src = "return 42"
        tree = ast.parse(src)
        ret = tree.body.body[0]
        result = generator.generate(ret)
        assert "return" in result
        assert "1" in result

    def test_generate_return_multiple_values(self, generator):
        """Test generating return with multiple values"""
        src = "return 1, 2, 3"
        tree = ast.parse(src)
        ret = tree.body.body[0]
        result = generator.generate(ret)
        assert "return" in result
        assert "3" in result

    def test_generate_break(self, generator):
        """Test generating break statement"""
        src = "break"
        tree = ast.parse(src)
        break_stmt = tree.body.body[0]
        result = generator.generate(break_stmt)
        assert result == "break;"

    def test_generate_unsupported_statement(self, generator):
        """Test that unsupported statements raise error"""
        stmt = astnodes.Do(body=astnodes.Block([]))
        with pytest.raises(NotImplementedError):
            generator.generate(stmt)

    def test_generate_while_not_implemented(self, generator):
        """Test that while loops not implemented"""
        stmt = astnodes.While(test=astnodes.TrueExpr(), body=astnodes.Block([]))
        with pytest.raises(NotImplementedError):
            generator.generate(stmt)

    def test_generate_if_not_implemented(self, generator):
        """Test that if statements not implemented"""
        stmt = astnodes.If(
            test=astnodes.TrueExpr(),
            body=astnodes.Block([]),
            orelse=None
        )
        with pytest.raises(NotImplementedError):
            generator.generate(stmt)

    def test_generate_for_in_not_implemented(self, generator):
        """Test that for-in loops not implemented"""
        stmt = astnodes.Forin(
            body=astnodes.Block([]),
            iter=[astnodes.Name(identifier="t")],
            targets=[astnodes.Name(identifier="k")]
        )
        with pytest.raises(NotImplementedError):
            generator.generate(stmt)
