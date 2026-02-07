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

    def generate_file(self, lua_ast: astnodes.Chunk, input_file: Path, generate_header: bool = False) -> str:
        """Generate complete C++ file with multi-pass type inference

        Performs four-phase type analysis:

        1. Function signature collection
        2. Local type inference
        3. Inter-procedural type propagation
        4. Type validation

        Args:
            lua_ast: Lua AST chunk
            input_file: Input Lua file path
            generate_header: If True, also return module header content

        Returns:
            Complete C++ code as string, or tuple of (code, header) if generate_header=True
        """
        from lua2c.analyzers.type_inference import TypeInference
        from lua2c.analyzers.type_validator import TypeValidator, ValidationSeverity

        lines = []

        # Phase 1: Multi-pass type inference
        type_inferencer = TypeInference(self.context, verbose=False)
        type_inferencer.infer_chunk(lua_ast)

        # Phase 2: Type validation
        validator = TypeValidator(type_inferencer)
        issues = validator.validate_all()

        # Print validation warnings (if any)
        if validator.has_warnings():
            print("\n" + validator.print_issues(filter_severity=ValidationSeverity.WARNING))

        # Print propagation summary (if any warnings)
        if type_inferencer.propagation_logger.warnings:
            print("\n" + type_inferencer.propagation_logger.print_summary())

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

        # Store module name for project mode
        module_name = str(input_file.with_suffix('').name)
        self._module_name = module_name

        # Header comment
        lines.append(f"// Auto-generated from {input_file}")
        lines.append("// Lua2C Transpiler with Type Optimization")
        lines.append("")

        # Includes based on mode
        mode = self.context.get_mode()
        state_name = self.context.get_project_name()
        if mode in ('project', 'single_standalone', 'single_library'):
            # Custom state modes: include state header and module header
            # Use state_name for both to ensure consistent naming
            module_header_name = f"{state_name}_module.hpp"
            lines.extend([
                f'#include "{state_name}_state.hpp"',
                f'#include "{module_header_name}"',
                "",
            ])
        else:
            raise RuntimeError(f"Legacy mode '{mode}' not supported. Use project or single_custom modes.")

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
        export_name = self.naming.module_export_name(module_name)
        state_type = self.context.get_state_type()
        state_name = self.context.get_project_name()
        if state_name is None:
            state_name = module_name
        lines.append(f"// Module export: {export_name}")
        lines.append(f"luaValue {export_name}({state_type} state) {{")
        lines.extend(self._generate_module_body(lua_ast))
        lines.append("}")

        module_cpp = "\n".join(lines)

        if generate_header:
            module_header = self.generate_module_header(module_name, state_type.rstrip('*'))
            return module_cpp, module_header

        return module_cpp

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

    def generate_module_header(self, module_name: str, state_name: str) -> str:
        """Generate module header file for single-file mode

        Args:
            module_name: Name of module (e.g., "simple")
            state_name: Name of state type (e.g., "simple_lua_State")

        Returns:
            Module header content as string
        """
        # Calculate state base name (remove _lua_State suffix from state_name)
        state_base = state_name.replace('_lua_State', '')
        # Use naming scheme to generate export function name
        export_name = self.naming.module_export_name(state_base)
        return f"""#pragma once

#include "l2c_runtime.hpp"
#include "{state_base}_state.hpp"

luaValue {export_name}({state_name}* state);
"""
