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
from lua2cpp.core.library_call_collector import LibraryCallCollector
from lua2cpp.generators.header_generator import HeaderGenerator
from lua2cpp.core.library_registry import LibraryFunctionRegistry


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
        self._library_registry = LibraryFunctionRegistry()

        # Generators for expressions and statements
        self._expr_gen = ExprGenerator(self._library_registry)
        self._stmt_gen = StmtGenerator(self._library_registry)
        # Set cross-reference for anonymous function generation
        self._expr_gen._stmt_gen = self._stmt_gen

        # Type resolver (created per generate_file call)
        self._type_resolver: Optional[TypeResolver] = None

        # Track whether 'arg' variable is referenced in Lua code
        self._has_arg: bool = False

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

        # Detect if 'arg' variable is referenced
        self._has_arg = self._detect_arg_usage(chunk)

        # Extract and sanitize filename for module_init function name
        if input_file:
            filename_stem = input_file.stem
            sanitized_filename = self._sanitize_filename(filename_stem)
        else:
            sanitized_filename = 'module'

        # Generate module initialization function
        module_init_code = self._generate_module_body_init(sanitized_filename, chunk)
        lines.append(module_init_code)

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
                mangled_name = self._mangle_if_main(func_name)

                # Get return type
                return_type = "auto"
                type_info = ASTAnnotationStore.get_type(stmt)
                if type_info is not None:
                    return_type = type_info.cpp_type()

                # Build parameter list with template parameters
                template_params = []
                params = []
                template_param_idx = 1

                for arg in stmt.args:
                    param_type = "auto"
                    arg_type_info = ASTAnnotationStore.get_type(arg)
                    if arg_type_info is not None:
                        param_type = arg_type_info.cpp_type()
                    
                    # Use template parameter names (T1, T2, etc.)
                    template_params.append(f"T{template_param_idx}")
                    params.append(f"T{template_param_idx}")
                    template_param_idx += 1

                # Build template declaration
                if template_params:
                    template_params_str = ", ".join(f"typename {tp}" for tp in template_params)
                    declaration = f"template<{template_params_str}> {return_type} {mangled_name}({', '.join(params)});"
                else:
                    declaration = f"{return_type} {mangled_name}();"

                if isinstance(stmt, astnodes.LocalFunction):
                    # Local function: forward declare as lambda type
                    # For simplicity, we just note the function name
                    declarations.append(f"// Local function: {func_name}")
                else:
                    # Global function: standard forward declaration with template syntax
                    declarations.append(declaration)

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

    def _generate_header_file(
        self,
        chunk: astnodes.Chunk,
        output_path: Path
    ) -> str:
        """Generate state.h header file with library API declarations

        Collects all library function calls from AST and generates
        a single state.h header file containing:
        - Struct definitions for each Lua library module (io, string, math, etc.)
        - Global function declarations in lua2c:: namespace
        - Template function definitions inline (header-only pattern)

        Args:
            chunk: Lua AST chunk to analyze
            output_path: Full path to output state.h file

        Returns:
            Path to generated state.h file as string

        Example:
            >>> emitter = CppEmitter()
            >>> emitter.generate_file(chunk)
            >>> header_path = emitter._generate_header_file(chunk, Path("state.h"))
            >>> print(f"Generated: {header_path}")
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        collector = LibraryCallCollector()
        collector.visit(chunk)
        library_calls = collector.get_library_calls()

        global_functions = set()

        generator = HeaderGenerator()
        header = generator.generate_header(library_calls, global_functions)

        with open(output_path, 'w') as f:
            f.write(header)

        return str(output_path)

    def generate_header_file(self, chunk: astnodes.Chunk, output_dir: Optional[Path] = None) -> Path:
        """Generate state.h header file with library API declarations

        Collects all library function calls from AST and generates
        a single state.h header file containing:
        - Struct definitions for each Lua library module (io, string, math, etc.)
        - Global function declarations in lua2c:: namespace
        - Template function definitions inline (header-only pattern)

        Args:
            chunk: Lua AST chunk to analyze
            output_dir: Optional directory for state.h output (default: current directory)

        Returns:
            Path to generated state.h file

        Example:
            >>> emitter = CppEmitter()
            >>> emitter.generate_file(chunk)
            >>> header_path = emitter.generate_header_file(chunk, Path("output"))
            >>> print(f"Generated: {header_path}")
        """
        if output_dir is None:
            output_dir = Path.cwd()

        output_dir.mkdir(parents=True, exist_ok=True)

        collector = LibraryCallCollector()
        collector.visit(chunk)
        library_calls = collector.get_library_calls()

        global_functions = set()

        header_gen = HeaderGenerator()
        header_content = header_gen.generate_header(library_calls, global_functions)

        header_path = output_dir / "state.h"
        with open(header_path, 'w') as f:
            f.write(header_content)

        return header_path

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to create valid C identifier

        Converts filename to valid C identifier by:
        - Replacing special characters with underscores
        - Keeping only alphanumeric and underscore characters
        - Stripping random alphanumeric suffixes from temp files
        - Handling test patterns for module init naming

        Args:
            filename: Filename to sanitize (without extension)

        Returns:
            Sanitized filename valid as C identifier
        """
        import re

        if filename.startswith('tmp'):
            return 'module'

        segments = re.split(r'[-_]', filename)

        meaningful_segments = []
        for seg in segments:
            if not seg:
                continue

            if seg.isalpha():
                meaningful_segments.append(seg)
            else:
                # Extract alphabetic prefix; apply length heuristic for random suffix detection
                match = re.match(r'^([a-z]+)', seg)
                if match:
                    prefix = match.group(1)
                    remaining = seg[len(prefix):]
                    # If digits follow, use length heuristic (random suffixes typically < 5 chars)
                    if re.match(r'\d', remaining) and len(prefix) >= 5:
                        meaningful_segments.append(prefix)
                    elif not re.match(r'\d', remaining):
                        meaningful_segments.append(prefix)
                break

        if meaningful_segments:
            result = '_'.join(meaningful_segments)
        else:
            result = 'module'

        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', result)
        return sanitized if sanitized else 'module'

    def _mangle_if_main(self, func_name: str) -> str:
        """Return '_l2c_main' for 'main' function, else return name unchanged"""
        return "_l2c_main" if func_name == "main" else func_name

    def _generate_module_body_init(self, filename: str, chunk: astnodes.Chunk) -> str:
        """Generate module initialization function with filename-based naming

        Generates a C++ function named <filename>_module_init that contains
        all module body statements. The function signature includes:
        - State* state parameter (always)
        - TABLE arg parameter (when arg is detected in code)

        Args:
            filename: Sanitized filename for function name
            chunk: Lua AST chunk
            global_vars: List of global variable names that need declarations

        Returns:
            C++ code for module init function as string
        """
        lines: List[str] = []
        function_name = f"{filename}_module_init"

        # Build function signature
        params = []
        if self._has_arg:
            params.append("TABLE arg")

        params_str = ", ".join(params)
        lines.append(f"void {function_name}({params_str}) {{")
        lines.append(f"    // {function_name} - Module initialization")
        lines.append(f"    // This function contains all module-level statements")

        global_vars = self._collect_global_variables(chunk)
        for var_name in global_vars:
            lines.append(f"    TABLE {var_name};")

        # Generate module body statements
        body_statements = self._generate_module_body(chunk)
        lines.extend(body_statements)
        lines.append("}")

        return "\n".join(lines)

    def _detect_arg_usage(self, chunk: astnodes.Chunk) -> bool:
        """Detect if the special 'arg' variable is referenced in Lua code

        Traverses the AST to find Name nodes with id='arg', ignoring:
        - String literals and comments
        - Table keys
        - Explicit function parameters
        - Local variable shadowing (assignment, not reference)

        Args:
            chunk: Lua AST chunk to analyze

        Returns:
            True if 'arg' is implicitly referenced, False otherwise
        """
        has_explicit_arg_decl = False

        def check_explicit_arg(node: astnodes.Node) -> None:
            nonlocal has_explicit_arg_decl
            if node is None:
                return

            node_type = type(node).__name__

            if node_type == "LocalAssign" and hasattr(node, 'targets'):
                for target in node.targets:
                    target_type = type(target).__name__
                    if target_type == "Name" and hasattr(target, 'id') and target.id == "arg":
                        has_explicit_arg_decl = True

            if node_type in ("Function", "LocalFunction") and hasattr(node, 'args'):
                for arg in node.args:
                    arg_type = type(arg).__name__
                    if arg_type == "Name" and hasattr(arg, 'id') and arg.id == "arg":
                        has_explicit_arg_decl = True

            for attr_name in dir(node):
                if not attr_name.startswith('_') and attr_name not in ('fields', 'args', 'targets', 'key'):
                    attr = getattr(node, attr_name, None)
                    if attr is not None:
                        if isinstance(attr, astnodes.Node):
                            check_explicit_arg(attr)
                        elif isinstance(attr, (list, tuple)):
                            for item in attr:
                                if isinstance(item, astnodes.Node):
                                    check_explicit_arg(item)

        def find_implicit_arg(node: astnodes.Node) -> bool:
            if node is None:
                return False

            node_type = type(node).__name__

            if node_type == "Name" and hasattr(node, 'id') and node.id == "arg":
                return True

            if node_type == "String":
                return False

            if node_type == "Table" and hasattr(node, 'fields'):
                for field in node.fields:
                    if hasattr(field, 'key') and field.key:
                        field_key_type = type(field.key).__name__
                        if field_key_type == "Name" and hasattr(field.key, 'id') and field.key.id == "arg":
        return False

    def _is_inside_function(self, node: astnodes.Node, chunk: astnodes.Chunk) -> bool:
        from luaparser import astnodes

        def find_all_functions(n):
            functions = []
            if type(n).__name__ in ("Function", "LocalFunction"):
                functions.append(n)
            if hasattr(n, 'body'):
                if hasattr(n.body, 'body'):
                    for stmt in n.body.body:
                        functions.extend(find_all_functions(stmt))
                else:
                    functions.extend(find_all_functions(n.body))
            return functions

        for func_node in find_all_functions(chunk):
            if self._node_in_function(node, func_node):
                return True
        return False

    def _node_in_function(self, node: astnodes.Node, func_node: astnodes.Node) -> bool:
        def is_in_scope(check_node, scope_node):
            if check_node is scope_node:
                return True
            if not hasattr(scope_node, 'body'):
                return False
            body = scope_node.body
            if hasattr(body, 'body'):
                if check_node in body.body:
                    return True
                for stmt in body.body:
                    if type(stmt).__name__ in ("Fornum", "If", "While", "Forin", "Repeat"):
                        if is_in_scope(check_node, stmt):
                            return True
            return False

        return is_in_scope(node, func_node)

            for attr_name in dir(node):
                if not attr_name.startswith('_') and attr_name not in ('fields', 'targets', 'key'):
                    attr = getattr(node, attr_name, None)
                    if attr is not None:
                        if isinstance(attr, astnodes.Node):
                            if find_implicit_arg(attr):
                                return True
                        elif isinstance(attr, (list, tuple)):
                            for item in attr:
                                if isinstance(item, astnodes.Node):
                                    if find_implicit_arg(item):
                                        return True

            return False

        check_explicit_arg(chunk)
        if has_explicit_arg_decl:
            return False
        return find_implicit_arg(chunk)

    def _collect_global_variables(self, chunk: astnodes.Chunk) -> List[str]:
        """Collect names of global variables from Assign nodes in module body

        Returns global variables that need TABLE declarations.
        - LocalAssign nodes are excluded (they generate auto declarations)
        - Variables that shadow LocalAssign declarations are excluded
        - Assign nodes inside functions are scanned for implicit globals
        """
        # First, collect all variables declared via LocalAssign at module level
        local_declared = set()
        for stmt in chunk.body.body:
            if type(stmt).__name__ == "LocalAssign" and hasattr(stmt, 'targets'):
                for target in stmt.targets:
                    if hasattr(target, 'id'):
                        local_declared.add(target.id)

        # Then collect global Assign targets, excluding those already declared locally
        global_vars = []
        for stmt in chunk.body.body:
            if type(stmt).__name__ == "Assign" and hasattr(stmt, 'targets'):
                for target in stmt.targets:
                    target_type = type(target).__name__
                    if target_type == "Name" and hasattr(target, 'id'):
                        if target.id in local_declared:
                            continue
                        if self._is_inside_function(stmt, chunk):
                            if not self._is_local_in_function(stmt, target.id, chunk):
                                global_vars.append(target.id)
                        else:
                            global_vars.append(target.id)

        return global_vars

    def _is_local_in_function(self, assign_node: astnodes.Node, var_name: str, chunk: astnodes.Chunk) -> bool:
        from luaparser import astnodes

        def is_local_in_scope(node: astnodes.Node, current_func: Optional[astnodes.Node] = None) -> bool:
            if current_func is None:
                return False

            if not hasattr(current_func, 'body'):
                return False

            body = current_func.body
            if hasattr(body, 'body'):
                for stmt in body.body:
                    if type(stmt).__name__ == "LocalAssign" and hasattr(stmt, 'targets'):
                        for target in stmt.targets:
                            target_type = type(target).__name__
                            if target_type == "Name" and hasattr(target, 'id') and target.id == var_name:
                                return True

                    if type(stmt).__name__ == "Fornum" and hasattr(stmt, 'target') and hasattr(stmt.target, 'id'):
                        if stmt.target.id == var_name:
                            return True

                    if type(stmt).__name__ in ("Function", "LocalFunction"):
                        if is_local_in_scope(node, stmt):
                            return True

                if hasattr(body, 'body'):
                    for stmt in body.body:
                        if type(stmt).__name__ == "Fornum" and hasattr(stmt, 'body') and hasattr(stmt.body, 'body'):
                            if is_local_in_scope(node, stmt):
                                return True
            return False

        for stmt in chunk.body.body:
            stmt_type = type(stmt).__name__
            if stmt_type in ("Function", "LocalFunction"):
                if self._is_inside_function(assign_node, chunk):
                    if stmt is assign_node:
                        return is_local_in_scope(assign_node, stmt)
                    if is_local_in_scope(assign_node, stmt):
                        return True

        return False
