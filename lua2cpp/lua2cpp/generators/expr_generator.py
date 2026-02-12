"""Expression generator for Lua2C++ transpiler

Generates C++ code from Lua AST expression nodes.
Implements double-dispatch pattern for literal and name expressions.
"""

from typing import Any, Optional, TYPE_CHECKING
from lua2cpp.core.ast_visitor import ASTVisitor
from lua2cpp.core.library_registry import LibraryFunctionRegistry as _LibraryFunctionRegistry
from lua2cpp.core.types import ASTAnnotationStore

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

    def __init__(self, library_registry: Optional[_LibraryFunctionRegistry] = None, stmt_gen: Optional[Any] = None) -> None:
        """Initialize expression generator

        Args:
            library_registry: Optional registry for detecting library function calls.
                            If provided, generates API syntax for library functions.
            stmt_gen: Optional statement generator for generating anonymous function bodies.
        """
        super().__init__()
        self._library_registry = library_registry
        self._stmt_gen = stmt_gen

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

    def visit_UMinusOp(self, node: astnodes.UMinusOp) -> str:
        operand = self.generate(node.operand)
        return f"-({operand})"

    def visit_Call(self, node: astnodes.Call) -> str:
        func = self.generate(node.func)
        args = []
        for i, arg in enumerate(node.args):
            generated = self.generate(arg)
            if generated is None:
                raise TypeError(f"Cannot generate code for argument {i} of type {type(arg).__name__} in Call to {func}")
            args.append(generated)

        # Check if this is a call to a global library function (e.g., print, tonumber)
        if self._is_global_function_call(node):
            # Global library functions are in l2c namespace and don't need state parameter
            args_str = ", ".join(args) if args else ""
            return f"l2c::{func}({args_str})"
        else:
            # Regular function calls don't include state parameter
            args_str = ", ".join(args) if args else ""
            return f"{func}({args_str})"

    def _is_global_function_call(self, node: astnodes.Call) -> bool:
        """Check if this is a call to a global Lua library function

        Global functions like print, tonumber, tostring, etc. are in l2c namespace
        and don't require the state parameter.

        Args:
            node: Call AST node

        Returns:
            True if this is a global library function call, False otherwise
        """
        if self._library_registry is None:
            return False

        # Check if func is a Name node (direct function call like print())
        if isinstance(node.func, astnodes.Name):
            func_name = node.func.id
            return self._library_registry.is_global_function(func_name)

        return False

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

    def visit_AnonymousFunction(self, node: astnodes.AnonymousFunction) -> str:
        """Generate C++ lambda expression for anonymous function"""
        params = []
        for arg in node.args:
            if hasattr(arg, 'id'):
                params.append(f"const auto& {arg.id}")
            else:
                params.append("const auto& arg")

        params_str = ", ".join(params)

        return_type = "auto"
        type_info = ASTAnnotationStore.get_type(node)
        if type_info is not None:
            return_type = type_info.cpp_type()

        if self._stmt_gen is None:
            body_str = "    /* Anonymous function body - stmt_gen not available */"
        else:
            body_lines = []
            for stmt in node.body.body:
                body_lines.append(f"    {self._stmt_gen.generate(stmt)}")
            body_str = "\n".join(body_lines) if body_lines else ""

        return f"[]({params_str}) -> {return_type} {{\n{body_str}\n}}"

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
