"""Y-combinator pattern detector for Lua2C++ transpiler

Detects self-application patterns that cannot be compiled in C++17.
"""

from dataclasses import dataclass
from typing import List
from .core.ast_visitor import ASTVisitor

try:
    from luaparser import astnodes
except ImportError:
    raise ImportError("luaparser is required. Install with: pip install luaparser")


@dataclass
class YCombinatorWarning:
    """Warning about detected Y-combinator pattern"""
    line_start: int
    line_end: int
    source_snippet: str
    message: str


class YCombinatorDetector(ASTVisitor):
    """Detects Y-combinator (fixed-point combinator) patterns in Lua AST
    
    Y-combinator patterns use self-application (e.g., f(f)) which cannot
    be compiled in C++17 due to circular type dependencies.
    """
    
    def __init__(self, source_lines: List[str] = None) -> None:
        super().__init__()
        self._warnings: List[YCombinatorWarning] = []
        self._source_lines = source_lines or []
    
    def visit_Call(self, node: astnodes.Call) -> None:
        if isinstance(node.func, astnodes.Name):
            func_name = node.func.id
            for arg in node.args:
                if isinstance(arg, astnodes.Name) and arg.id == func_name:
                    line_start = self._get_line_number(node)
                    line_end = line_start
                    snippet = self._get_source_snippet(line_start, line_end)
                    warning = YCombinatorWarning(
                        line_start=line_start,
                        line_end=line_end,
                        source_snippet=snippet,
                        message=f"Self-application '{func_name}({func_name})' detected. This Y-combinator pattern cannot compile in C++17."
                    )
                    self._warnings.append(warning)
        self.generic_visit(node)
    
    def get_warnings(self) -> List[YCombinatorWarning]:
        return self._warnings.copy()
    
    def _get_line_number(self, node: astnodes.Node) -> int:
        if hasattr(node, '_first_token') and node._first_token:
            return int(node._first_token.line)
        return 0
    
    def _get_source_snippet(self, line_start: int, line_end: int) -> str:
        if not self._source_lines or line_start <= 0:
            return ""
        lines = []
        for i in range(line_start - 1, min(line_end, len(self._source_lines))):
            lines.append(self._source_lines[i].rstrip())
        return "\n".join(lines)
