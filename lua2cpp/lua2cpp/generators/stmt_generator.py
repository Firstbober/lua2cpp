"""Statement generator for Lua2C++ transpiler

Generates C++ code from Lua AST statement nodes.
Implements double-dispatch pattern for local assignments and return statements.
"""

from typing import Any, Optional, List
from lua2cpp.core.ast_visitor import ASTVisitor
from lua2cpp.core.types import Type, ASTAnnotationStore
from lua2cpp.generators.expr_generator import ExprGenerator

try:
    from luaparser import astnodes
except ImportError:
    raise ImportError(
        "luaparser is required. Install with: pip install luaparser"
    )


class StmtGenerator(ASTVisitor):
    """Generates C++ code from Lua AST statement nodes

    Focuses on local variable declarations and return statements.
    Integrates with ExprGenerator for expression generation.
    """

    def __init__(self) -> None:
        """Initialize statement generator with expression generator"""
        super().__init__()
        self._expr_gen = ExprGenerator()

    def generate(self, node: Any) -> str:
        """Generate C++ code from a statement node using double-dispatch

        Args:
            node: AST node (statement node)

        Returns:
            str: Generated C++ code as a string
        """
        return self.visit(node)

    def visit_LocalAssign(self, node: astnodes.LocalAssign) -> str:
        """Generate C++ local variable declaration

        Format: <type> <name> = <expr>;
        If type is unknown, use 'auto' keyword.
        If no initialization, just declare without assignment.

        Args:
            node: LocalAssign AST node with .names (list of Name nodes)
                  and .exprs (list of expression nodes, can be empty)

        Returns:
            str: C++ local variable declaration(s)
        """
        # LocalAssign has .names (list of Name nodes) and .exprs (list of expressions)
        # Multiple variables can be declared: local x, y = 1, 2
        lines = []

        for i, name_node in enumerate(node.names):
            var_name = name_node.id
            init_expr = None
            if i < len(node.exprs):
                init_expr = node.exprs[i]

            # Try to get type information from the name node
            var_type = None
            type_info = ASTAnnotationStore.get_type(name_node)
            if type_info is not None:
                var_type = type_info.cpp_type()
            else:
                var_type = "auto"

            if init_expr is not None:
                # Generate the expression
                expr_code = self._expr_gen.generate(init_expr)
                lines.append(f"{var_type} {var_name} = {expr_code};")
            else:
                # Declaration without initialization
                lines.append(f"{var_type} {var_name};")

        # If only one variable, return single line; otherwise return all lines
        if len(lines) == 1:
            return lines[0]
        return "\n".join(lines)

    def visit_Return(self, node: astnodes.Return) -> str:
        """Generate C++ return statement

        Format: return <expr>; or return;
        Handles multiple return values by taking the first one.

        Args:
            node: Return AST node with .exprs (list of expression nodes, can be empty)

        Returns:
            str: C++ return statement
        """
        # Return has .exprs (list of expressions, can be empty)
        # For now, we only handle single return values or empty return
        if not node.exprs:
            return "return;"

        # Take the first expression (Lua can return multiple values,
        # but we only handle the first for now)
        expr_code = self._expr_gen.generate(node.exprs[0])
        return f"return {expr_code};"
