"""C++ code emitter for Lua2Cpp transpiler

Orchestrates code generation by coordinating TypeResolver, ExprGenerator,
and StmtGenerator to produce complete C++ files from Lua AST.

Architecture:
- Multi-pass type inference using TypeResolver (4 passes)
- Forward declarations for all functions
- Function definitions generated via StmtGenerator
- Module body with remaining statements
"""

from typing import List, Optional
from pathlib import Path

try:
    from luaparser import astnodes
except ImportError:
    raise ImportError("luaparser is required. Install with: pip install luaparser")

from lua2cpp.core.scope import ScopeManager
from lua2cpp.core.symbol_table import SymbolTable
from lua2cpp.core.types import Type, TypeKind, ASTAnnotationStore
from lua2cpp.analyzers.function_registry import FunctionSignatureRegistry
from lua2cpp.analyzers.type_resolver import TypeResolver
from lua2cpp.generators.expr_generator import ExprGenerator
from lua2cpp.generators.stmt_generator import StmtGenerator


class CppEmitter:
    """Emits complete C++ code from Lua AST

    Orchestrates type inference and code generation to produce
    a single .cpp file from a Lua AST chunk.

    The generate_file() method:
    1. Runs TypeResolver for 4-pass type inference
    2. Collects all function definitions
    3. Generates forward declarations
    4. Generates function bodies using StmtGenerator
    5. Generates module body statements
    6. Returns complete C++ code
    """

    def __init__(self) -> None:
        """Initialize C++ emitter with required components

        Creates ScopeManager, SymbolTable, and FunctionSignatureRegistry
        for type inference and symbol resolution.
        """
        self.scope_manager = ScopeManager()
        self.symbol_table = SymbolTable(self.scope_manager)
        self.function_registry = FunctionSignatureRegistry()

        # Generators for expressions and statements
        self._expr_gen = ExprGenerator()
        self._stmt_gen = StmtGenerator()

        # Type resolver (created per generate_file call)
        self._type_resolver: Optional[TypeResolver] = None

    def generate_file(self, chunk: astnodes.Chunk, input_file: Optional[Path] = None) -> str:
        """Generate complete C++ file from Lua AST chunk

        Performs multi-pass type inference before code generation:
        1. Collect function signatures
        2. Infer local types
        3. Inter-procedural type propagation
        4. Type validation and finalization

        Args:
            chunk: Lua AST chunk to generate code from
            input_file: Optional input file path for comments/debug info

        Returns:
            str: Complete C++ code as string

        Example:
            >>> from luaparser import ast
            >>> emitter = CppEmitter()
            >>> lua_code = "local function add(a, b) return a + b end"
            >>> chunk = ast.parse(lua_code)
            >>> cpp_code = emitter.generate_file(chunk)
            >>> print(cpp_code)
            // Auto-generated C++ code...
        """
        lines: List[str] = []

        # Phase 1: Type resolution
        self._type_resolver = TypeResolver(
            self.scope_manager,
            self.symbol_table,
            self.function_registry
        )
        self._type_resolver.resolve_chunk(chunk)

        # Phase 2: Generate forward declarations
        forward_decls = self._generate_forward_declarations(chunk)
        if forward_decls:
            lines.append("// Forward declarations")
            lines.extend(forward_decls)
            lines.append("")

        # Phase 3: Generate function definitions
        functions = self._collect_functions(chunk)
        for func_code in functions:
            lines.append(func_code)
            lines.append("")

        # Phase 4: Generate module body
        lines.append("// Module body")
        lines.append("void module_body() {")
        body_statements = self._generate_module_body(chunk)
        lines.extend(body_statements)
        lines.append("}")

        # Add header comment if input_file provided
        if input_file:
            header_comment = f"// Auto-generated from {input_file}\n// Lua2Cpp Transpiler"
            lines.insert(0, header_comment)

        return "\n".join(lines)

    def _generate_forward_declarations(self, chunk: astnodes.Chunk) -> List[str]:
        """Generate forward declarations for all functions

        Scans the chunk for all function definitions and generates
        forward declarations. This is necessary for functions that
        may call each other (including recursive calls).

        Args:
            chunk: Lua AST chunk

        Returns:
            List of forward declaration strings
        """
        declarations: List[str] = []

        for stmt in chunk.body.body:
            if isinstance(stmt, (astnodes.LocalFunction, astnodes.Function)):
                func_name = stmt.name.id if hasattr(stmt.name, 'id') else "anonymous"

                # Get return type
                return_type = "auto"
                type_info = ASTAnnotationStore.get_type(stmt)
                if type_info is not None:
                    return_type = type_info.cpp_type()

                # Build parameter list
                params = ["State* state"]
                for arg in stmt.args:
                    param_type = "auto"
                    arg_type_info = ASTAnnotationStore.get_type(arg)
                    if arg_type_info is not None:
                        param_type = arg_type_info.cpp_type()
                    params.append(f"{param_type} {arg.id}")

                params_str = ", ".join(params)

                if isinstance(stmt, astnodes.LocalFunction):
                    # Local function: forward declare as lambda type
                    # For simplicity, we just note the function name
                    declarations.append(f"// Local function: {func_name}")
                else:
                    # Global function: standard forward declaration
                    declarations.append(f"{return_type} {func_name}({params_str});")

        return declarations

    def _collect_functions(self, chunk: astnodes.Chunk) -> List[str]:
        """Collect and generate all function definitions

        Traverses the AST and generates C++ code for all function
        definitions (both LocalFunction and Function nodes).

        Args:
            chunk: Lua AST chunk

        Returns:
            List of C++ function definition strings
        """
        functions: List[str] = []

        for stmt in chunk.body.body:
            if isinstance(stmt, (astnodes.LocalFunction, astnodes.Function)):
                # Generate function code using StmtGenerator
                func_code = self._stmt_gen.generate(stmt)
                functions.append(func_code)

        return functions

    def _generate_module_body(self, chunk: astnodes.Chunk) -> List[str]:
        """Generate module body statements (non-function definitions)

        Generates C++ code for all statements that are not function
        definitions. These are placed inside the module_body() function.

        Args:
            chunk: Lua AST chunk

        Returns:
            List of indented C++ statement strings
        """
        statements: List[str] = []

        for stmt in chunk.body.body:
            # Skip function definitions (they're generated separately)
            if not isinstance(stmt, (astnodes.LocalFunction, astnodes.Function)):
                stmt_code = self._stmt_gen.generate(stmt)
                if stmt_code:
                    statements.append(f"    {stmt_code}")

        return statements

    def get_type_resolver(self) -> TypeResolver:
        """Get the type resolver used for the last generation

        Returns:
            TypeResolver instance with inferred type information

        Raises:
            RuntimeError: If called before generate_file()
        """
        if self._type_resolver is None:
            raise RuntimeError("Type resolver not initialized. Call generate_file() first.")
        return self._type_resolver

    def get_inferred_type(self, symbol_name: str) -> Type:
        """Get inferred type for a symbol

        Convenience method to access type inference results.

        Args:
            symbol_name: Name of the symbol to query

        Returns:
            Inferred Type object

        Example:
            >>> emitter = CppEmitter()
            >>> emitter.generate_file(chunk)
            >>> x_type = emitter.get_inferred_type("x")
            >>> print(x_type.kind)
            TypeKind.NUMBER
        """
        if self._type_resolver is None:
            raise RuntimeError("Type resolver not initialized. Call generate_file() first.")
        return self._type_resolver.get_type(symbol_name)
