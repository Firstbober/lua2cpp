"""AST visitor base class for Lua2C transpiler

Provides a visitor pattern for traversing Lua AST nodes.
Based on luaparser's astnodes module.
"""

from abc import ABC
from typing import Any, Optional

try:
    from luaparser import ast as luaparser_ast
    from luaparser import astnodes
except ImportError:
    raise ImportError(
        "luaparser is required. Install with: pip install luaparser"
    )


class ASTVisitor(ABC):
    """Base visitor for Lua AST traversal

    Override visit_* methods to handle specific node types.
    Call super().visit_*() to continue traversal.
    """

    def __init__(self) -> None:
        """Initialize visitor"""
        self._in_function = False
        self._current_line = 0

    def visit(self, node: Any) -> Any:
        """Visit a node using double-dispatch pattern

        Args:
            node: AST node to visit

        Returns:
            Result from visit method (often None)
        """
        method_name = f"visit_{node.__class__.__name__}"
        method = getattr(self, method_name, self.generic_visit)
        return method(node)

    def generic_visit(self, node: Any) -> None:
        """Default visitor - visit all child nodes

        Args:
            node: AST node
        """
        for child in self.get_children(node):
            if child is not None:
                self.visit(child)

    def get_children(self, node: Any) -> list:
        """Get all child nodes of a node

        Args:
            node: AST node

        Returns:
            List of child nodes
        """
        children = []
        if hasattr(node, "__dict__"):
            for value in node.__dict__.values():
                if isinstance(value, (astnodes.Node, list)):
                    if isinstance(value, list):
                        children.extend(value)
                    else:
                        children.append(value)
        return children

    def visit_Chunk(self, node: astnodes.Chunk) -> None:
        """Visit chunk node (root of Lua AST)

        Args:
            node: Chunk node
        """
        self.generic_visit(node)

    def visit_Block(self, node: astnodes.Block) -> None:
        """Visit block node

        Args:
            node: Block node
        """
        self.generic_visit(node)

    def visit_Assign(self, node: astnodes.Assign) -> None:
        """Visit assignment node

        Args:
            node: Assign node
        """
        self.generic_visit(node)

    def visit_LocalAssign(self, node: astnodes.LocalAssign) -> None:
        """Visit local assignment node

        Args:
            node: LocalAssign node
        """
        self.generic_visit(node)

    def visit_Name(self, node: astnodes.Name) -> None:
        """Visit name node (identifier)

        Args:
            node: Name node
        """
        self.generic_visit(node)

    def visit_Number(self, node: astnodes.Number) -> None:
        """Visit number node

        Args:
            node: Number node
        """
        self.generic_visit(node)

    def visit_String(self, node: astnodes.String) -> None:
        """Visit string node

        Args:
            node: String node
        """
        self.generic_visit(node)

    def visit_Nil(self, node: astnodes.Nil) -> None:
        """Visit nil node

        Args:
            node: Nil node
        """
        self.generic_visit(node)

    def visit_True(self, node: astnodes.TrueExpr) -> None:
        """Visit true node

        Args:
            node: TrueExpr node
        """
        self.generic_visit(node)

    def visit_False(self, node: astnodes.FalseExpr) -> None:
        """Visit false node

        Args:
            node: FalseExpr node
        """
        self.generic_visit(node)

    def visit_Function(self, node: astnodes.Function) -> None:
        """Visit function node

        Args:
            node: Function node
        """
        was_in_function = self._in_function
        self._in_function = True
        self.generic_visit(node)
        self._in_function = was_in_function

    def visit_AnonymousFunction(self, node: astnodes.AnonymousFunction) -> None:
        """Visit anonymous function node

        Args:
            node: AnonymousFunction node
        """
        was_in_function = self._in_function
        self._in_function = True
        self.generic_visit(node)
        self._in_function = was_in_function

    def visit_LocalFunction(self, node: astnodes.LocalFunction) -> None:
        """Visit local function node

        Args:
            node: LocalFunction node
        """
        was_in_function = self._in_function
        self._in_function = True
        self.generic_visit(node)
        self._in_function = was_in_function

    def visit_Call(self, node: astnodes.Call) -> None:
        """Visit function call node

        Args:
            node: Call node
        """
        self.generic_visit(node)

    def visit_Invoke(self, node: astnodes.Invoke) -> None:
        """Visit method invocation (colon syntax) node

        Args:
            node: Invoke node
        """
        self.generic_visit(node)

    def visit_Index(self, node: astnodes.Index) -> None:
        """Visit index node (table[index])

        Args:
            node: Index node
        """
        self.generic_visit(node)

    def visit_Field(self, node: astnodes.Field) -> None:
        """Visit field node (table.field)

        Args:
            node: Field node
        """
        self.generic_visit(node)

    def visit_TableConstructor(self, node: astnodes.TableConstructor) -> None:
        """Visit table constructor node

        Args:
            node: TableConstructor node
        """
        self.generic_visit(node)

    def visit_Binop(self, node: astnodes.Binop) -> None:
        """Visit binary operation node

        Args:
            node: Binop node
        """
        self.generic_visit(node)

    def visit_Unop(self, node: astnodes.Unop) -> None:
        """Visit unary operation node

        Args:
            node: Unop node
        """
        self.generic_visit(node)

    def visit_While(self, node: astnodes.While) -> None:
        """Visit while loop node

        Args:
            node: While node
        """
        self.generic_visit(node)

    def visit_Repeat(self, node: astnodes.Repeat) -> None:
        """Visit repeat-until loop node

        Args:
            node: Repeat node
        """
        self.generic_visit(node)

    def visit_If(self, node: astnodes.If) -> None:
        """Visit if statement node

        Args:
            node: If node
        """
        self.generic_visit(node)

    def visit_Forin(self, node: astnodes.Forin) -> None:
        """Visit for-in loop node

        Args:
            node: Forin node
        """
        self.generic_visit(node)

    def visit_Fornum(self, node: astnodes.Fornum) -> None:
        """Visit numeric for loop node

        Args:
            node: Fornum node
        """
        self.generic_visit(node)

    def visit_Return(self, node: astnodes.Return) -> None:
        """Visit return statement node

        Args:
            node: Return node
        """
        self.generic_visit(node)

    def visit_Break(self, node: astnodes.Break) -> None:
        """Visit break statement node

        Args:
            node: Break node
        """
        self.generic_visit(node)

    def visit_Label(self, node: astnodes.Label) -> None:
        """Visit label node

        Args:
            node: Label node
        """
        self.generic_visit(node)

    def visit_Goto(self, node: astnodes.Goto) -> None:
        """Visit goto statement node

        Args:
            node: Goto node
        """
        self.generic_visit(node)

    def visit_Dots(self, node: astnodes.Dots) -> None:
        """Visit varargs (...) node

        Args:
            node: Dots node
        """
        self.generic_visit(node)

    def visit_Ellipsis(self, node: astnodes.Ellipsis) -> None:
        """Visit ellipsis node (multiple values)

        Args:
            node: Ellipsis node
        """
        self.generic_visit(node)

    def visit_DotMethod(self, node: astnodes.DotMethod) -> None:
        """Visit dot method node

        Args:
            node: DotMethod node
        """
        self.generic_visit(node)

    def visit_ColonMethod(self, node: astnodes.ColonMethod) -> None:
        """Visit colon method node

        Args:
            node: ColonMethod node
        """
        self.generic_visit(node)

    def visit_Array(self, node: astnodes.Array) -> None:
        """Visit array node

        Args:
            node: Array node
        """
        self.generic_visit(node)

    def visit_Anchor(self, node: astnodes.Anchor) -> None:
        """Visit anchor node

        Args:
            node: Anchor node
        """
        self.generic_visit(node)

    def visit_Semicolon(self, node: astnodes.Semicolon) -> None:
        """Visit semicolon node

        Args:
            node: Semicolon node
        """
        self.generic_visit(node)

    def visit_Identifier(self, node: astnodes.Identifier) -> None:
        """Visit identifier node

        Args:
            node: Identifier node
        """
        self.generic_visit(node)

    def visit_Comment(self, node: astnodes.Comment) -> None:
        """Visit comment node

        Args:
            node: Comment node
        """
        pass  # Comments are ignored in code generation

    @property
    def in_function(self) -> bool:
        """Check if currently inside a function

        Returns:
            True if inside a function
        """
        return self._in_function

    @property
    def current_line(self) -> int:
        """Get current line number

        Returns:
            Current line number
        """
        return self._current_line
