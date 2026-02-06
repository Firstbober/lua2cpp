"""C++ code emitter for Lua2C transpiler

Combines generated statements into complete C++ files.
Handles #line directives for debug info and proper formatting.
"""

from typing import List
from pathlib import Path
from lua2c.core.context import TranslationContext
from lua2c.generators.expr_generator import ExprGenerator
from lua2c.generators.stmt_generator import StmtGenerator
from lua2c.generators.decl_generator import DeclGenerator
from lua2c.generators.naming import NamingScheme

try:
    from luaparser import ast
    from luaparser import astnodes
except ImportError:
    raise ImportError("luaparser is required. Install with: pip install luaparser")


class CppEmitter:
    """Emits complete C++ code from Lua AST"""

    def __init__(self, context: TranslationContext) -> None:
        """Initialize C++ emitter

        Args:
            context: Translation context
        """
        self.context = context
        self.expr_gen = ExprGenerator(context)
        self.stmt_gen = StmtGenerator(context)
        self.decl_gen = DeclGenerator(context)
        self.naming = NamingScheme()

    def generate_file(self, lua_ast: astnodes.Chunk, input_file: Path) -> str:
        """Generate complete C++ file

        Args:
            lua_ast: Lua AST chunk
            input_file: Input Lua file path

        Returns:
            Complete C++ code as string
        """
        from lua2c.analyzers.type_inference import TypeInference

        lines = []

        # Phase 1: Type inference
        type_inferencer = TypeInference(self.context)
        type_inferencer.infer_chunk(lua_ast)

        # Store inferred types in symbol table for code generation access
        for symbol_name, inferred_type in type_inferencer.inferred_types.items():
            symbol = self.context.resolve_symbol(symbol_name)
            if symbol:
                symbol.inferred_type = inferred_type

        for symbol_name, table_info in type_inferencer.table_info.items():
            symbol = self.context.resolve_symbol(symbol_name)
            if symbol:
                symbol.table_info = table_info

        # Set type inferencer for expression generator and context
        self.expr_gen.set_type_inferencer(type_inferencer)
        self.context.set_type_inferencer(type_inferencer)

        # Phase 2: String collection (existing)
        self._collect_strings(lua_ast)

        # Header comment
        lines.append(f"// Auto-generated from {input_file}")
        lines.append("// Lua2C Transpiler with Type Optimization")
        lines.append("")

        # Includes (add deque and unordered_map)
        lines.extend([
            "#include \"lua_value.hpp\"",
            "#include \"lua_state.hpp\"",
            "#include \"lua_table.hpp\"",
            "#include <vector>",
            "#include <string>",
            "#include <deque>",
            "#include <unordered_map>",
            "#include <variant>",
            "",
        ])

        # String pool
        lines.append("// String pool")
        lines.append(self.decl_gen.generate_string_pool())
        lines.append("")

        # Forward declarations
        forward_decls = self.decl_gen.generate_forward_declarations()
        if forward_decls:
            lines.append("// Forward declarations")
            lines.extend(forward_decls)
            lines.append("")

        # Generate function definitions first
        functions = self._collect_functions(lua_ast)
        for func_def in functions:
            lines.append(func_def)
            lines.append("")

        # Generate module body statements
        module_name = str(input_file.with_suffix(''))
        export_name = self.naming.module_export_name(module_name)
        lines.append(f"// Module export: {export_name}")
        lines.append(f"luaValue {export_name}(luaState* state) {{")
        lines.extend(self._generate_module_body(lua_ast))
        lines.append("}")

        return "\n".join(lines)

    def _collect_strings(self, chunk: astnodes.Chunk) -> None:
        """First pass: collect all string literals into pool

        Args:
            chunk: Lua AST chunk
        """
        for stmt in chunk.body.body:
            self._collect_strings_from_node(stmt)

    def _collect_strings_from_node(self, node: astnodes.Node) -> None:
        """Recursively collect strings from a node

        Args:
            node: AST node
        """
        if isinstance(node, astnodes.String):
            string_value = node.s.decode() if isinstance(node.s, bytes) else node.s
            self.context.add_string_literal(string_value)
            return

        # Known fields that contain child nodes
        child_fields = []
        if hasattr(node, 'body'):
            if isinstance(node.body, astnodes.Block):
                child_fields.extend(node.body.body)
            elif isinstance(node.body, list):
                child_fields.extend(node.body)
            else:
                child_fields.append(node.body)

        if hasattr(node, 'left') and node.left:
            child_fields.append(node.left)
        if hasattr(node, 'right') and node.right:
            child_fields.append(node.right)
        if hasattr(node, 'operand') and node.operand:
            child_fields.append(node.operand)
        if hasattr(node, 'func') and node.func:
            child_fields.append(node.func)
        if hasattr(node, 'args') and node.args:
            child_fields.extend(node.args)
        if hasattr(node, 'targets') and node.targets:
            child_fields.extend(node.targets)
        if hasattr(node, 'values') and node.values:
            child_fields.extend(node.values)
        if hasattr(node, 'test') and node.test:
            child_fields.append(node.test)
        if hasattr(node, 'orelse') and node.orelse:
            if isinstance(node.orelse, list):
                child_fields.extend(node.orelse)
            else:
                child_fields.append(node.orelse)

        # Recursively visit child nodes
        for child in child_fields:
            if isinstance(child, astnodes.Node):
                self._collect_strings_from_node(child)
            elif isinstance(child, list):
                for item in child:
                    if isinstance(item, astnodes.Node):
                        self._collect_strings_from_node(item)

    def _collect_functions(self, chunk: astnodes.Chunk) -> List[str]:
        """Collect and generate all function definitions

        Args:
            chunk: Lua AST chunk

        Returns:
            List of C++ function definition strings
        """
        functions = []

        for stmt in chunk.body.body:
            if isinstance(stmt, astnodes.LocalFunction):
                func_code = self.stmt_gen.generate(stmt)
                functions.append(func_code)
                func_name = stmt.name.id if hasattr(stmt.name, 'id') else "anonymous"
                self.context.define_local(func_name)

        return functions

    def _generate_module_body(self, chunk: astnodes.Chunk) -> List[str]:
        """Generate module body statements (non-function definitions)

        Args:
            chunk: Lua AST chunk

        Returns:
            List of C++ statement strings
        """
        statements = []

        for stmt in chunk.body.body:
            # Skip function definitions (they're generated separately)
            if not isinstance(stmt, astnodes.LocalFunction):
                stmt_code = self.stmt_gen.generate(stmt)
                if stmt_code:
                    statements.append(f"    {stmt_code}")

        # Add return statement at end
        statements.append("    return luaValue();")

        return statements

    def _generate_line_directive(self, line: int, file: str) -> str:
        """Generate #line directive for debug info

        Args:
            line: Lua source line number
            file: Lua source file path

        Returns:
            C++ preprocessor directive
        """
        return f"#line {line} \"{file}\""
