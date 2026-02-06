"""Tests for AST visitor"""

import pytest
from lua2c.core.ast_visitor import ASTVisitor

try:
    from luaparser import ast
except ImportError:
    pytest.skip("luaparser not installed", allow_module_level=True)


class CountingVisitor(ASTVisitor):
    """Visitor that counts node types"""

    def __init__(self) -> None:
        super().__init__()
        self.counts: dict = {}
        self.names: list = []

    def visit_Name(self, node) -> None:
        """Count Name nodes and collect identifiers"""
        node_type = node.__class__.__name__
        self.counts[node_type] = self.counts.get(node_type, 0) + 1
        self.names.append(node.id)
        self.generic_visit(node)

    def visit_Number(self, node) -> None:
        """Count Number nodes"""
        node_type = node.__class__.__name__
        self.counts[node_type] = self.counts.get(node_type, 0) + 1
        self.generic_visit(node)

    def visit_String(self, node) -> None:
        """Count String nodes"""
        node_type = node.__class__.__name__
        self.counts[node_type] = self.counts.get(node_type, 0) + 1
        self.generic_visit(node)

    def visit_Function(self, node) -> None:
        """Count Function nodes"""
        node_type = node.__class__.__name__
        self.counts[node_type] = self.counts.get(node_type, 0) + 1
        self.generic_visit(node)

    def visit_AnonymousFunction(self, node) -> None:
        """Count AnonymousFunction nodes"""
        node_type = node.__class__.__name__
        self.counts[node_type] = self.counts.get(node_type, 0) + 1
        self.generic_visit(node)


class TestASTVisitor:
    """Test suite for ASTVisitor"""

    def test_basic_traversal(self):
        """Test basic AST traversal"""
        src = """
        local x = 10
        local y = x + 5
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert visitor.counts.get("Name", 0) >= 2
        assert visitor.counts.get("Number", 0) >= 2

    def test_function_detection(self):
        """Test function scope detection"""
        visitor = ASTVisitor()
        assert visitor.in_function is False

    def test_simple_assignment(self):
        """Test simple assignment parsing and traversal"""
        src = "local a = 42"
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "a" in visitor.names
        assert visitor.counts.get("Number", 0) == 1

    def test_string_literal(self):
        """Test string literal traversal"""
        src = 'local msg = "hello world"'
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert visitor.counts.get("String", 0) == 1

    def test_function_definition(self):
        """Test function definition traversal"""
        src = """
        local function add(a, b)
          return a + b
        end
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "add" in visitor.names
        assert "a" in visitor.names
        assert "b" in visitor.names

    def test_anonymous_function(self):
        """Test anonymous function traversal"""
        src = """
        local f = function(x) return x * 2 end
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "f" in visitor.names
        assert "x" in visitor.names
        assert visitor.counts.get("AnonymousFunction", 0) == 1

    def test_if_statement(self):
        """Test if statement traversal"""
        src = """
        if x > 0 then
          print("positive")
        else
          print("non-positive")
        end
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "x" in visitor.names
        assert visitor.counts.get("String", 0) >= 1

    def test_while_loop(self):
        """Test while loop traversal"""
        src = """
        while i < 10 do
          i = i + 1
        end
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "i" in visitor.names

    def test_for_loop(self):
        """Test numeric for loop traversal"""
        src = """
        for i = 1, 10, 1 do
          print(i)
        end
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "i" in visitor.names

    def test_for_in_loop(self):
        """Test for-in loop traversal"""
        src = """
        for k, v in pairs(t) do
          print(k, v)
        end
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "k" in visitor.names
        assert "v" in visitor.names
        assert "t" in visitor.names

    def test_table_constructor(self):
        """Test table constructor traversal"""
        src = "local t = {1, 2, 3}"
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert visitor.counts.get("Number", 0) >= 3

    def test_method_call(self):
        """Test method call (colon syntax) traversal"""
        src = "object:method(arg)"
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "object" in visitor.names
        assert "arg" in visitor.names

    def test_nested_functions(self):
        """Test nested function traversal"""
        src = """
        local function outer()
          local function inner()
            return 42
          end
          return inner()
        end
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "outer" in visitor.names
        assert "inner" in visitor.names

    def test_return_statement(self):
        """Test return statement traversal"""
        src = """
        function foo()
          return 1, 2, 3
        end
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert visitor.counts.get("Number", 0) >= 3

    def test_break_statement(self):
        """Test break statement in loop"""
        src = """
        while true do
          break
        end
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

    def test_nil_and_boolean(self):
        """Test nil and boolean values"""
        src = """
        local a = nil
        local b = true
        local c = false
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "a" in visitor.names
        assert "b" in visitor.names
        assert "c" in visitor.names

    def test_binary_operations(self):
        """Test various binary operations"""
        src = """
        local a = x + y
        local b = x - y
        local c = x * y
        local d = x / y
        local e = x % y
        local f = x ^ y
        local g = x == y
        local h = x ~= y
        local i = x < y
        local j = x <= y
        local k = x > y
        local l = x >= y
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "x" in visitor.names
        assert "y" in visitor.names

    def test_unary_operations(self):
        """Test unary operations"""
        src = """
        local a = -x
        local b = not x
        local c = #x
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert visitor.names.count("x") >= 3

    def test_table_access(self):
        """Test table field access"""
        src = """
        local x = t.field
        local y = t["key"]
        local z = t[1]
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert visitor.names.count("t") >= 3
        assert "x" in visitor.names
        assert "y" in visitor.names
        assert "z" in visitor.names

    def test_multiple_assignment(self):
        """Test multiple assignment"""
        src = "local a, b, c = 1, 2, 3"
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "a" in visitor.names
        assert "b" in visitor.names
        assert "c" in visitor.names
        assert visitor.counts.get("Number", 0) >= 3

    def test_varargs(self):
        """Test varargs (...)"""
        src = """
        function foo(...)
          return ...
        end
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "foo" in visitor.names

    def test_comments_ignored(self):
        """Test that comments are ignored in traversal"""
        src = """
        -- This is a comment
        local x = 42  -- inline comment
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "x" in visitor.names

    def test_generic_visit_children(self):
        """Test that generic_visit visits all children"""
        src = """
        local function test(a, b, c)
          if a then
            return b
          else
            return c
          end
        end
        """
        tree = ast.parse(src)
        visitor = CountingVisitor()
        visitor.visit(tree)

        assert "test" in visitor.names
        assert "a" in visitor.names
        assert "b" in visitor.names
        assert "c" in visitor.names
