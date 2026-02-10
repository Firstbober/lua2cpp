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
        assert "luaValue()" in result

    def test_generate_local_function(self, generator, context):
        """Test generating local function definition"""
        src = "local function add(a, b) return a + b end"
        tree = ast.parse(src)
        local_func = tree.body.body[0]
        result = generator.generate(local_func)
        assert "auto add" in result
        assert "auto&& a" in result
        assert "auto&& b" in result
        assert "add" in result
        assert "(" in result
        assert ")" in result

    def test_generate_call_statement(self, generator):
        """Test generating function call as statement"""
        src = "print('hello')"
        tree = ast.parse(src)
        call = tree.body.body[0]
        result = generator.generate(call)
        assert ";" in result

    def test_generate_return_no_value(self, generator):
        """Test generating return with no value"""
        src = "return"
        tree = ast.parse(src)
        ret = tree.body.body[0]
        result = generator.generate(ret)
        assert "return" in result
        assert "luaValue()" in result

    def test_generate_return_single_value(self, generator):
        """Test generating return with single value"""
        src = "return 42"
        tree = ast.parse(src)
        ret = tree.body.body[0]
        result = generator.generate(ret)
        assert "return" in result
        assert "42" in result

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

    def test_generate_invoke_statement(self, generator):
        """Test generating method invocation statement"""
        source = astnodes.Name(identifier="obj")
        func = astnodes.Name(identifier="method")
        stmt = astnodes.Invoke(source=source, func=func, args=[])
        result = generator.generate(stmt)
        assert ";" in result

    def test_generate_while(self, generator):
        """Test generating while loop"""
        stmt = astnodes.While(test=astnodes.TrueExpr(), body=astnodes.Block([]))
        result = generator.generate(stmt)
        assert "while" in result
        assert "is_truthy" in result

    def test_generate_if(self, generator):
        """Test generating if statement"""
        stmt = astnodes.If(
            test=astnodes.TrueExpr(),
            body=astnodes.Block([]),
            orelse=None
        )
        result = generator.generate(stmt)
        assert "if" in result
        assert "is_truthy" in result

    def test_generate_if_with_else(self, generator):
        """Test generating if-else statement"""
        stmt = astnodes.If(
            test=astnodes.TrueExpr(),
            body=astnodes.Block([]),
            orelse=[astnodes.Call(func=astnodes.Name(identifier="print"), args=[])]
        )
        result = generator.generate(stmt)
        assert "if" in result
        assert "else" in result

    def test_generate_repeat(self, generator):
        """Test generating repeat-until loop"""
        stmt = astnodes.Repeat(test=astnodes.TrueExpr(), body=astnodes.Block([]))
        result = generator.generate(stmt)
        assert "do" in result
        assert "while" in result

    def test_generate_for_in(self, generator):
        """Test generating for-in loop"""
        stmt = astnodes.Forin(
            body=astnodes.Block([]),
            iter=[astnodes.Name(identifier="t")],
            targets=[astnodes.Name(identifier="k")]
        )
        result = generator.generate(stmt)
        assert "for" in result

    def test_generate_for_num(self, generator):
        """Test generating numeric for loop"""
        stmt = astnodes.Fornum(
            target=astnodes.Name(identifier="i"),
            start=astnodes.Number(n=1),
            stop=astnodes.Number(n=10),
            step=astnodes.Number(n=1),
            body=astnodes.Block([])
        )
        result = generator.generate(stmt)
        assert "for" in result
        assert "luaValue" in result

    def test_generate_do(self, generator):
        """Test generating do block"""
        stmt = astnodes.Do(body=astnodes.Block([]))
        result = generator.generate(stmt)
        assert "do" in result
        assert "while" in result

    def test_generate_unsupported_statement(self, generator):
        """Test that unsupported statements raise error"""
        stmt = astnodes.Label(label_id=astnodes.Name(identifier="label"))
        with pytest.raises(NotImplementedError):
            generator.generate(stmt)

    def test_visit_assign_simple(self, generator):
        """Test visit_Assign with simple assignment: x = 1"""
        src = "x = 1"
        tree = ast.parse(src)
        assign = tree.body.body[0]
        result = generator.generate(assign)
        assert "=" in result
        assert ";" in result
        assert "None" not in result

    def test_visit_assign_complex_expression(self, generator, context):
        """Test visit_Assign with complex expression: vBv = vBv + ui*vi"""
        context.define_local("vBv")
        context.define_local("ui")
        context.define_local("vi")

        src = "vBv = vBv + ui*vi"
        tree = ast.parse(src)
        assign = tree.body.body[0]
        result = generator.generate(assign)
        assert "=" in result
        assert "+" in result
        assert "*" in result
        assert ";" in result
        assert "None" not in result

    def test_visit_assign_index(self, generator, context):
        """Test visit_Assign with index assignment: u[i] = 1"""
        context.define_local("u")
        context.define_local("i")

        src = "u[i] = 1"
        tree = ast.parse(src)
        assign = tree.body.body[0]
        result = generator.generate(assign)
        assert "=" in result
        assert "[" in result
        assert "]" in result
        assert ";" in result
        assert "None" not in result
