"""Expression generator for Lua2C++ transpiler

Generates C++ code from Lua AST expression nodes.
Implements double-dispatch pattern for literal and name expressions.
"""

from typing import Any, Optional, TYPE_CHECKING
from lua2cpp.core.ast_visitor import ASTVisitor
from lua2cpp.core.library_registry import LibraryFunctionRegistry as _LibraryFunctionRegistry

try:
    from luaparser import astnodes
except ImportError:
    raise ImportError(
        "luaparser is required. Install with: pip install luaparser"
    )

if TYPE_CHECKING:
    from lua2cpp.core.library_registry import LibraryFunctionRegistry


class ExprGenerator(ASTVisitor):
    """Generates C++ code from Lua AST expression nodes

    Focuses on literal expressions (Number, String, Boolean) and Name nodes.
    More complex expressions (operators, calls, indexing) are handled separately.
    """

    def __init__(self, library_registry: Optional[_LibraryFunctionRegistry] = None) -> None:
        """Initialize expression generator

        Args:
            library_registry: Optional registry for detecting library function calls.
                            If provided, generates API syntax for library functions.
        """
        super().__init__()
        self._library_registry = library_registry

    def generate(self, node: Any) -> str:
        """Generate C++ code from an expression node using double-dispatch

        Args:
            node: AST node (expression node)

        Returns:
            str: Generated C++ code as a string
        """
        return self.visit(node)

    def visit_Number(self, node: astnodes.Number) -> str:
        """Generate C++ number literal

        Args:
            node: Number AST node

        Returns:
            str: Number literal as raw value
        """
        # Lua numbers are always double in C++ representation
        # Return the numeric value as-is (Lua parser handles formatting)
        return str(node.n)

    def visit_String(self, node: astnodes.String) -> str:
        """Generate C++ string literal with proper escaping

        Args:
            node: String AST node

        Returns:
            str: C++ string literal with escaped quotes and special characters
        """
        # String node's .s attribute contains bytes, need to decode
        content = node.s.decode() if isinstance(node.s, bytes) else node.s

        # Escape special characters for C++ output
        # C++ string literals need escapes for: ", \, newline, tab, etc.
        escaped = (
            content
            .replace('\\', '\\\\')
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
            .replace('\t', '\\t')
        )
        return f'"{escaped}"'

    def visit_TrueExpr(self, node: astnodes.TrueExpr) -> str:
        """Generate C++ true boolean literal

        Args:
            node: TrueExpr AST node

        Returns:
            str: C++ true keyword
        """
        return "true"

    def visit_FalseExpr(self, node: astnodes.FalseExpr) -> str:
        """Generate C++ false boolean literal

        Args:
            node: FalseExpr AST node

        Returns:
            str: C++ false keyword
        """
        return "false"

    def visit_Name(self, node: astnodes.Name) -> str:
        """Generate C++ variable name reference

        Args:
            node: Name AST node

        Returns:
            str: Variable name as-is
        """
        # Return the identifier name directly
        return node.id

    def visit_AddOp(self, node: astnodes.AddOp) -> str:
        """Generate C++ addition operation

        Args:
            node: AddOp AST node with left and right operands

        Returns:
            str: C++ addition expression
        """
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} + {right}"

    def visit_SubOp(self, node: astnodes.SubOp) -> str:
        """Generate C++ subtraction operation

        Args:
            node: SubOp AST node with left and right operands

        Returns:
            str: C++ subtraction expression
        """
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} - {right}"

    def visit_MultOp(self, node: astnodes.MultOp) -> str:
        """Generate C++ multiplication operation

        Args:
            node: MultOp AST node with left and right operands

        Returns:
            str: C++ multiplication expression
        """
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} * {right}"

    def visit_FloatDivOp(self, node: astnodes.FloatDivOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} / {right}"

    def visit_EqToOp(self, node: astnodes.EqToOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} == {right}"

    def visit_LessThanOp(self, node: astnodes.LessThanOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} < {right}"

    def visit_GreaterThanOp(self, node: astnodes.GreaterThanOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} > {right}"

    def visit_LessOrEqThanOp(self, node: astnodes.LessOrEqThanOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} <= {right}"

    def visit_GreaterOrEqThanOp(self, node: astnodes.GreaterOrEqThanOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} >= {right}"

    def visit_NotEqToOp(self, node: astnodes.NotEqToOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} != {right}"

    def visit_AndLoOp(self, node: astnodes.AndLoOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"(({left}) ? ({right}) : ({left}))"

    def visit_OrLoOp(self, node: astnodes.OrLoOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"(({left}) ? ({left}) : ({right}))"

    def visit_Call(self, node: astnodes.Call) -> str:
        func = self.generate(node.func)
        args = [self.generate(arg) for arg in node.args]
        args_str = ", ".join([f"state"] + args) if args else "state"
        return f"{func}({args_str})"

    def visit_Index(self, node: astnodes.Index) -> str:
        """Generate C++ index expression

        For library function calls (io.write, math.sqrt), generates member access
        syntax (io.write) instead of pointer access (io->write).

        Args:
            node: Index AST node with value and idx

        Returns:
            str: Generated C++ code
        """
        value = self.generate(node.value)
        idx = self.generate(node.idx)

        if hasattr(node, 'notation') and str(node.notation) == "IndexNotation.DOT":
            if self._is_library_index(node):
                return f"{value}.{idx}"
            else:
                return f"{value}->{idx}"
        else:
            return f"{value}[{idx}]"

    def _is_library_index(self, node: astnodes.Index) -> bool:
        """Check if Index node represents a library function reference

        Library functions have pattern: Index.value is Name with library name.
        Examples: io.write, math.sqrt, string.format

        Args:
            node: Index AST node

        Returns:
            True if this is a library function reference, False otherwise
        """
        if self._library_registry is None:
            return False

        if not isinstance(node.value, astnodes.Name):
            return False

        library_name = node.value.id
        return self._library_registry.is_standard_library(library_name)

    def visit_Table(self, node: astnodes.Table) -> str:
        """Generate C++ table constructor

        For now, always returns NEW_TABLE macro for simplicity.

        Args:
            node: Table AST node

        Returns:
            str: NEW_TABLE macro string
        """
        return "NEW_TABLE"

    def visit_Assign(self, node: astnodes.Assign) -> str:
        """Generate C++ assignment expression

        Args:
            node: Assign AST node with targets and values

        Returns:
            str: C++ assignment expression (target = value, no semicolon)
        """
        target = self.generate(node.targets[0])
        value = self.generate(node.values[0])
        return f"{target} = {value}"
