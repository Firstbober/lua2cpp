"""Library call collector for Lua standard library detection

AST visitor that traverses Lua AST and collects all calls to standard library functions.
Stores information about which library functions are called and where.
"""

from dataclasses import dataclass
from typing import List, Optional
from lua2cpp.core.ast_visitor import ASTVisitor
from lua2cpp.core.library_registry import LibraryFunctionRegistry

try:
    from luaparser import astnodes
except ImportError:
    raise ImportError(
        "luaparser is required. Install with: pip install luaparser"
    )


@dataclass
class LibraryCall:
    """Information about a library function call found in AST

    Attributes:
        module: Library module name (e.g., "io", "math", "string")
        func: Function name within module (e.g., "write", "sqrt", "format")
        line: Line number where call occurs (if available)
    """
    module: str
    func: str
    line: int

    def __str__(self) -> str:
        """String representation of library call"""
        line_info = f":{self.line}" if self.line > 0 else ""
        return f"{self.module}.{self.func}(){line_info}"


@dataclass
class GlobalCall:
    """Information about a global function call found in AST

    Attributes:
        module: Always empty string "" for global functions (global scope)
        func: Global function name (e.g., "print", "tonumber", "tostring")
        line: Line number where call occurs (if available)
    """
    module: str
    func: str
    line: int

    def __str__(self) -> str:
        """String representation of global call"""
        line_info = f":{self.line}" if self.line > 0 else ""
        return f"{self.func}(){line_info}"


class LibraryCallCollector(ASTVisitor):
    """AST visitor that collects all standard library function calls

    Traverses the AST and identifies calls to standard library functions
    (io.write, math.sqrt, string.format, etc.) by checking if the call's
    function reference is an Index expression with a known library name.

    Usage:
        collector = LibraryCallCollector()
        collector.visit(chunk)
        calls = collector.get_library_calls()
        for call in calls:
            print(f"{call.module}.{call.func}() at line {call.line}")
    """

    def __init__(self, registry: Optional[LibraryFunctionRegistry] = None) -> None:
        """Initialize library call collector

        Args:
            registry: LibraryFunctionRegistry to check for library functions (default: None creates new)
        """
        super().__init__()
        self._registry = registry if registry is not None else LibraryFunctionRegistry()
        self._library_calls: List[LibraryCall] = []
        self._global_calls: List[GlobalCall] = []

    def visit_Call(self, node: astnodes.Call) -> None:
        """Visit function call node and check if it's a library or global call

        Detects calls by checking:
        1. Is the function reference a Name node? (global function like print)
        2. Is the function reference an Index node? (library function like io.write)

        Args:
            node: Call AST node
        """
        # Check if func is a Name node (global function like print, tonumber)
        if isinstance(node.func, astnodes.Name):
            func_name = node.func.id
            # Check if this is a registered global function
            if self._registry.is_global_function(func_name):
                # This is a global function call - record it
                line_number = self._get_line_number(node)
                call = GlobalCall(
                    module="",  # Global functions have no module prefix
                    func=func_name,
                    line=line_number
                )
                self._global_calls.append(call)

                # Don't call generic_visit on the func part (already processed)
                # But still visit arguments
                for arg in node.args:
                    self.visit(arg)
                return

        # Check if func is an Index node (e.g., io.write, math.sqrt)
        if not isinstance(node.func, astnodes.Index):
            # Not a library call (regular function call like print())
            self.generic_visit(node)
            return

        idx_node = node.func

        # Check if Index.value is a Name node (library name like "io", "math")
        if not isinstance(idx_node.value, astnodes.Name):
            # Not a simple name (e.g., table[expr].func())
            self.generic_visit(node)
            return

        # Check if Index.idx is a Name node (function name like "write", "sqrt")
        if not isinstance(idx_node.idx, astnodes.Name):
            # Not a simple name (e.g., io[expr]())
            self.generic_visit(node)
            return

        # Get library and function names
        library_name = idx_node.value.id
        function_name = idx_node.idx.id

        # Check if this is a standard library function
        if not self._registry.is_standard_library(library_name):
            # Not a standard library (user-defined table)
            self.generic_visit(node)
            return

        # This is a library function call - record it
        line_number = self._get_line_number(node)
        call = LibraryCall(
            module=library_name,
            func=function_name,
            line=line_number
        )
        self._library_calls.append(call)

        # Don't call generic_visit on the func part (already processed)
        # But still visit arguments
        for arg in node.args:
            self.visit(arg)

    def visit_Invoke(self, node: astnodes.Invoke) -> None:
        """Visit method invocation node (colon syntax: io.stdout:write())

        Method invocations with colon syntax pass implicit 'self' as first argument.
        These are NOT standard library function calls in the same sense.

        Args:
            node: Invoke AST node
        """
        # Method calls with colon syntax are not simple library function calls
        # They pass 'self' implicitly, so we handle them differently
        self.generic_visit(node)

    def visit_Index(self, node: astnodes.Index) -> None:
        """Visit index node but don't process library references

        Library Index nodes are already handled in visit_Call.
        This prevents double counting.

        Args:
            node: Index AST node
        """
        # Check if this is a library reference (e.g., io.write)
        if isinstance(node.value, astnodes.Name) and isinstance(node.idx, astnodes.Name):
            library_name = node.value.id
            if self._registry.is_standard_library(library_name):
                # This is a library reference, already counted in visit_Call
                return

        # Regular table/array index - process normally
        self.generic_visit(node)

    def get_library_calls(self) -> List[LibraryCall]:
        """Get all collected library function calls

        Returns:
            List of LibraryCall objects found during traversal
        """
        return self._library_calls.copy()

    def get_global_calls(self) -> List[GlobalCall]:
        """Get all collected global function calls

        Returns:
            List of GlobalCall objects found during traversal
        """
        return self._global_calls.copy()

    def clear(self) -> None:
        """Clear all collected library and global calls

        Useful for reusing the collector with multiple ASTs.
        """
        self._library_calls.clear()
        self._global_calls.clear()

    def _get_line_number(self, node: astnodes.Node) -> int:
        """Get line number for a node

        Args:
            node: AST node

        Returns:
            Line number (1-based) or 0 if not available
        """
        if hasattr(node, '_first_token') and node._first_token:
            return int(node._first_token.line)
        return 0
