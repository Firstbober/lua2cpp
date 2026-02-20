"""C++ code emitter for Lua2Cpp transpiler

Orchestrates code generation by coordinating TypeResolver, ExprGenerator,
and StmtGenerator to produce complete C++ files from Lua AST.

Architecture:
- Multi-pass type inference using TypeResolver (4 passes)
- Forward declarations for all functions
- Function definitions generated via StmtGenerator
- Module body with remaining statements
"""

from typing import List, Optional, Set
from pathlib import Path

try:
    from luaparser import astnodes
except ImportError:
    raise ImportError("luaparser is required. Install with: pip install luaparser")

from ..core.scope import ScopeManager
from ..core.symbol_table import SymbolTable
from ..core.types import Type, TypeKind, ASTAnnotationStore
from ..analyzers.function_registry import FunctionSignatureRegistry
from ..analyzers.type_resolver import TypeResolver
from .expr_generator import ExprGenerator
from .stmt_generator import StmtGenerator
from ..core.library_call_collector import LibraryCallCollector
from .header_generator import HeaderGenerator
from ..core.library_registry import LibraryFunctionRegistry
from ..core.call_convention import CallConventionRegistry


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

    def __init__(self, convention_registry: Optional[CallConventionRegistry] = None) -> None:
        """Initialize C++ emitter with required components

        Creates ScopeManager, SymbolTable, and FunctionSignatureRegistry
        for type inference and symbol resolution.

        Args:
            convention_registry: Optional registry for call conventions (default: create new)
        """
        self.scope_manager = ScopeManager()
        self.symbol_table = SymbolTable(self.scope_manager)
        self.function_registry = FunctionSignatureRegistry()
        self._library_registry = LibraryFunctionRegistry()
        self._convention_registry = convention_registry or CallConventionRegistry()

        # Generators for expressions and statements
        self._expr_gen = ExprGenerator(self._library_registry, convention_registry=self._convention_registry)
        self._stmt_gen = StmtGenerator(self._library_registry, convention_registry=self._convention_registry)
        # Set cross-reference for anonymous function generation
        self._expr_gen._stmt_gen = self._stmt_gen

        # Type resolver (created per generate_file call)
        self._type_resolver: Optional[TypeResolver] = None

        # Track whether 'arg' variable is referenced in Lua code
        self._has_arg: bool = False

        # Track whether 'G' table is used (for extern TABLE G;)
        self._has_g_table: bool = False

        # Track whether 'love.*' API is used
        self._has_love: bool = False

        # Module dependency tracking
        # Maps known export symbol names to their module info
        # Format: {symbol_name: (module_path, cpp_var_name)}
        self._module_export_map = {
            # engine/object exports
            "Object": ("engine/object", "object_Object"),
            # engine/node exports
            "Node": ("engine/node", "node_Node"),
            # engine/moveable exports
            "Moveable": ("engine/moveable", "moveable_Moveable"),
            # engine/sprite exports
            "Sprite": ("engine/sprite", "sprite_Sprite"),
            # game exports
            "Game": ("game", "game_Game"),
            # card exports
            "Card": ("card", "card_Card"),
            # cardarea exports
            "CardArea": ("cardarea", "cardarea_CardArea"),
            # blind exports
            "Blind": ("blind", "blind_Blind"),
            # tag exports
            "Tag": ("tag", "tag_Tag"),
            # back exports
            "Back": ("back", "back_Back"),
            # engine/event exports
            "Event": ("engine/event", "event_Event"),
            # engine/animatedsprite exports
            "AnimatedSprite": ("engine/animatedsprite", "animatedsprite_AnimatedSprite"),
            # engine/ui exports
            "UI": ("engine/ui", "ui_UI"),
            # engine/text exports
            "Text": ("engine/text", "text_Text"),
            # engine/particles exports
            "Particles": ("engine/particles", "particles_Particles"),
        }
        # Track detected module dependencies
        self._module_deps: Set[str] = set()  # Set of module paths
        self._module_externs: Set[str] = set()  # Set of extern variable names

        # Track module-level state variables (locals + implicit globals)
        self._module_state: set[str] = set()

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

        # Extract and sanitize filename for module_init function name
        if input_file:
            filename_stem = input_file.stem
            sanitized_filename = self._sanitize_filename(filename_stem)
        else:
            sanitized_filename = 'module'

        # Phase 1: Type resolution
        self._type_resolver = TypeResolver(
            self.scope_manager,
            self.symbol_table,
            self.function_registry
        )
        self._type_resolver.resolve_chunk(chunk)

        # Detect optional dependencies
        self._has_g_table = self._detect_g_table_usage(chunk)
        self._has_love = self._detect_love_usage(chunk)
        self._detect_module_dependencies(chunk)

        # Phase 1.5: Module state (static file-scope globals)
        self._module_state = self._collect_module_state(chunk)
        self._module_prefix = sanitized_filename

        # Propagate module context to StmtGenerator for name mangling
        self._stmt_gen.set_module_context(self._module_prefix, self._module_state)

        if self._module_state:
            lines.append("// Module state")
            for var_name in sorted(self._module_state):
                var_type = self.get_inferred_type(var_name)
                cpp_type = self._get_cpp_type_name(var_type.kind)
                # Exported symbols are non-static so other modules can use them
            lines.append(f"{cpp_type} {self._module_prefix}_{var_name};")
            lines.append("")

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

        # Add includes after header comment
        includes: List[str] = []
        includes.append('#include "../runtime/l2c_runtime.hpp"')
        if self._has_g_table:
            includes.append('#include "../runtime/globals.hpp"')
        if self._has_love:
            includes.append('#include "../runtime/love_mock.hpp"')

        for module_path in sorted(self._module_deps):
            if input_file:
                current_dir = input_file.parent
                module_parts = module_path.split('/')
                module_name = module_parts[-1]
                if len(module_parts) > 1:
                    # Multi-part module (e.g., "engine/event")
                    if current_dir.name == "nonred":
                        # At root, need full path
                        include_path = f"{module_path}.hpp"
                    else:
                        # In subdirectory, check if same subdir or different
                        current_subdir = current_dir.name
                        module_subdir = module_parts[0] if len(module_parts) > 1 else ""
                        if current_subdir == module_subdir:
                            include_path = f"{module_name}.hpp"
                        else:
                            include_path = f"../{module_path}.hpp"
                else:
                    # Single name module (e.g., "card", "game")
                    if current_dir.name == module_name:
                        include_path = f"{module_name}.hpp"
                    elif current_dir.name == "nonred" or "nonred" not in current_dir.parts:
                        include_path = f"{module_name}.hpp"
                    else:
                        include_path = f"../{module_name}.hpp"
                includes.append(f'#include "{include_path}"')
            else:
                module_name = module_path.split('/')[-1]
                includes.append(f'#include "{module_name}.hpp"')

        insert_pos = 1 if input_file else 0
        for i, inc in enumerate(includes):
            lines.insert(insert_pos + i, inc)

        extern_pos = insert_pos + len(includes)
        if self._has_g_table or self._module_externs:
            lines.insert(extern_pos, "")
            if self._has_g_table:
                lines.insert(extern_pos + 1, "extern TABLE G;")
                extern_pos += 1
            for cpp_var in sorted(self._module_externs):
                # Skip extern for our own module's symbols
                if not cpp_var.startswith(self._module_prefix + "_"):
                    lines.insert(extern_pos + 1, f"extern TABLE {cpp_var};")
                    extern_pos += 1

            for cpp_var in sorted(self._module_externs):
                if cpp_var.startswith(self._module_prefix + "_"):
                    continue
                for symbol_name, (_, var) in self._module_export_map.items():
                    if var == cpp_var:
                        lines.insert(extern_pos + 1, f"#define {symbol_name} {cpp_var}")
                        extern_pos += 1
                        break

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

        for stmt in (chunk.body.body if isinstance(chunk.body.body, list) else [chunk.body.body]):
            if isinstance(stmt, (astnodes.LocalFunction, astnodes.Function)):
                func_name = stmt.name.id if hasattr(stmt.name, 'id') else "anonymous"
                mangled_name = self._mangle_if_main(func_name)

                # Get return type
                return_type = "auto"
                type_info = ASTAnnotationStore.get_type(stmt)
                if type_info is not None:
                    return_type = type_info.cpp_type()

                # Skip forward declaration for auto return type - C++ can't deduce auto from decl
                if return_type == "auto":
                    if isinstance(stmt, astnodes.LocalFunction):
                        declarations.append(f"// Local function: {func_name}")
                    continue

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

        for stmt in (chunk.body.body if isinstance(chunk.body.body, list) else [chunk.body.body]):
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

        for stmt in (chunk.body.body if isinstance(chunk.body.body, list) else [chunk.body.body]):
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

    def _get_cpp_type_name(self, type_kind) -> str:
        """Map TypeKind to C++ type name for module state declarations.

        Args:
            type_kind: TypeKind enum value

        Returns:
            C++ type name string (NUMBER, STRING, TABLE, etc.)
        """
        from ..core.types import TypeKind
        
        type_map = {
            TypeKind.NUMBER: "NUMBER",
            TypeKind.STRING: "STRING",
            TypeKind.BOOLEAN: "BOOLEAN",
            TypeKind.TABLE: "TABLE",
            TypeKind.FUNCTION: "TABLE",  # Functions stored as table references
            TypeKind.ANY: "TABLE",
            TypeKind.VARIANT: "TABLE",
            TypeKind.UNKNOWN: "TABLE",
        }
        return type_map.get(type_kind, "TABLE")

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

    def _detect_love_usage(self, chunk: astnodes.Chunk) -> bool:
        def find_love(node: astnodes.Node) -> bool:
            if node is None:
                return False

            node_type = type(node).__name__

            if node_type == "Index" and hasattr(node, 'value'):
                value_type = type(node.value).__name__
                if value_type == "Name" and hasattr(node.value, 'id') and node.value.id == "love":
                    return True

            if node_type == "Invoke" and hasattr(node, 'source'):
                source_type = type(node.source).__name__
                if source_type == "Name" and hasattr(node.source, 'id') and node.source.id == "love":
                    return True

            for attr_name in dir(node):
                if not attr_name.startswith('_') and attr_name not in ('fields', 'key'):
                    attr = getattr(node, attr_name, None)
                    if attr is not None:
                        if isinstance(attr, astnodes.Node):
                            if find_love(attr):
                                return True
                        elif isinstance(attr, (list, tuple)):
                            for item in attr:
                                if isinstance(item, astnodes.Node):
                                    if find_love(item):
                                        return True

            return False

        return find_love(chunk)

    def _detect_g_table_usage(self, chunk: astnodes.Chunk) -> bool:
        def find_g(node: astnodes.Node) -> bool:
            if node is None:
                return False

            node_type = type(node).__name__

            if node_type == "Name" and hasattr(node, 'id') and node.id == "G":
                return True

            if node_type == "Index" and hasattr(node, 'value'):
                value_type = type(node.value).__name__
                if value_type == "Name" and hasattr(node.value, 'id') and node.value.id == "G":
                    return True

            for attr_name in dir(node):
                if not attr_name.startswith('_') and attr_name not in ('fields', 'key'):
                    attr = getattr(node, attr_name, None)
                    if attr is not None:
                        if isinstance(attr, astnodes.Node):
                            if find_g(attr):
                                return True
                        elif isinstance(attr, (list, tuple)):
                            for item in attr:
                                if isinstance(item, astnodes.Node):
                                    if find_g(item):
                                        return True

            return False

        return find_g(chunk)

    def _detect_module_dependencies(self, chunk: astnodes.Chunk) -> None:
        def find_deps(node: astnodes.Node) -> None:
            if node is None:
                return

            node_type = type(node).__name__

            if node_type == "Name" and hasattr(node, 'id'):
                if node.id in self._module_export_map:
                    module_path, cpp_var = self._module_export_map[node.id]
                    self._module_deps.add(module_path)
                    self._module_externs.add(cpp_var)

            for attr_name in dir(node):
                if not attr_name.startswith('_') and attr_name not in ('fields', 'key'):
                    attr = getattr(node, attr_name, None)
                    if attr is not None:
                        if isinstance(attr, astnodes.Node):
                            find_deps(attr)
                        elif isinstance(attr, (list, tuple)):
                            for item in attr:
                                if isinstance(item, astnodes.Node):
                                    find_deps(item)

        find_deps(chunk)

    def _collect_global_variables(self, chunk: astnodes.Chunk) -> List[str]:
        """Collect names of global variables from Assign nodes in module body

        Returns global variables that need TABLE declarations.
        - LocalAssign nodes are excluded (they generate auto declarations)
        - Variables that shadow LocalAssign declarations are excluded
        - Assign nodes inside functions are excluded
        """
        # First, collect all variables declared via LocalAssign at module level
        local_declared = set()
        for stmt in (chunk.body.body if isinstance(chunk.body.body, list) else [chunk.body.body]):
            if type(stmt).__name__ == "LocalAssign" and hasattr(stmt, 'targets'):
                for target in stmt.targets:
                    if hasattr(target, 'id'):
                        local_declared.add(target.id)

        # Then collect global Assign targets, excluding those already declared locally
        global_vars = []
        for stmt in (chunk.body.body if isinstance(chunk.body.body, list) else [chunk.body.body]):
            if type(stmt).__name__ == "Assign" and hasattr(stmt, 'targets'):
                # Skip if inside a function
                if self._is_inside_function(stmt, chunk):
                    continue

                for target in stmt.targets:
                    target_type = type(target).__name__
                    if target_type == "Name" and hasattr(target, 'id'):
                        # Skip if already declared via LocalAssign
                        if target.id not in local_declared:
                            global_vars.append(target.id)
        return global_vars

    def _collect_module_state(self, chunk: astnodes.Chunk) -> Set[str]:
        """Collect all module-level state variables (locals + implicit globals)

        Returns set of variable names that need static file-scope declarations.
        Includes both LocalAssign targets and Assign nodes at module level
        that aren't already declared as local.
        """
        module_state = set()

        # Track all local declarations (both regular and library refs)
        local_declared = set()

        # 1. Collect module-level LocalAssign targets (exclude function refs)
        for stmt in (chunk.body.body if isinstance(chunk.body.body, list) else [chunk.body.body]):
            if type(stmt).__name__ == "LocalAssign" and hasattr(stmt, 'targets'):
                for i, target in enumerate(stmt.targets):
                    if hasattr(target, 'id'):
                        is_lib_ref = False
                        if hasattr(stmt, 'values') and i < len(stmt.values):
                            val = stmt.values[i]
                            if hasattr(val, 'value') and hasattr(val.value, 'id'):
                                lib_names = {'math', 'io', 'string', 'table', 'os'}
                                if val.value.id in lib_names:
                                    is_lib_ref = True

                        if not is_lib_ref:
                            module_state.add(target.id)
                        # Always add to local_declared to prevent collection as implicit global
                        local_declared.add(target.id)

        # 2. Collect implicit globals (Assign at module level, not already local)
        for stmt in (chunk.body.body if isinstance(chunk.body.body, list) else [chunk.body.body]):
            if type(stmt).__name__ == "Assign" and hasattr(stmt, 'targets'):
                if self._is_inside_function(stmt, chunk):
                    continue
                for target in stmt.targets:
                    if hasattr(target, 'id') and target.id not in local_declared:
                        module_state.add(target.id)

        # 3. Scan function bodies for implicit globals
        for stmt in (chunk.body.body if isinstance(chunk.body.body, list) else [chunk.body.body]):
            stmt_type = type(stmt).__name__
            if stmt_type in ("Function", "LocalFunction"):
                func_globals = self._collect_implicit_globals_in_function(stmt, local_declared)
                module_state.update(func_globals)

        # Store in instance variable for use by code generation
        self._module_state = module_state
        return module_state

    def _collect_implicit_globals_in_function(self, func_node, local_declared: Set[str]) -> Set[str]:
        """Scan function body for implicit globals (Assign without local declaration)"""
        implicit_globals = set()
        
        # Get function parameters
        func_locals = set()
        if hasattr(func_node, 'args'):
            for arg in func_node.args:
                if hasattr(arg, 'id'):
                    func_locals.add(arg.id)
        
        # Recursively walk function body
        def walk_stmts(stmts):
            for stmt in stmts:
                stmt_type = type(stmt).__name__
                
                # Collect LocalAssign targets as function-local
                if stmt_type == "LocalAssign" and hasattr(stmt, 'targets'):
                    for target in stmt.targets:
                        if hasattr(target, 'id'):
                            func_locals.add(target.id)
                
                # Check Assign nodes for implicit globals
                if stmt_type == "Assign" and hasattr(stmt, 'targets'):
                    for target in stmt.targets:
                        if hasattr(target, 'id'):
                            name = target.id
                            if name not in func_locals and name not in local_declared:
                                implicit_globals.add(name)
                
                # Recurse into nested blocks
                if hasattr(stmt, 'body'):
                    if hasattr(stmt.body, 'body'):
                        if isinstance(stmt.body.body, list):
                            walk_stmts(stmt.body.body)
                        else:
                            walk_stmts([stmt.body.body])
                if hasattr(stmt, 'orelse') and stmt.orelse:
                    orelse = stmt.orelse
                    if hasattr(orelse, 'body') and isinstance(orelse.body, list):
                        walk_stmts(orelse.body)
                    else:
                        walk_stmts([orelse])
        
        # Start walking from function body
        if hasattr(func_node, 'body') and hasattr(func_node.body, 'body'):
            if isinstance(func_node.body.body, list):
                walk_stmts(func_node.body.body)
            else:
                walk_stmts([func_node.body.body])
        
        return implicit_globals

    def _is_inside_function(self, node: astnodes.Node, chunk: astnodes.Chunk) -> bool:
        """Check if an AST node is inside a function body

        Traverses the tree to find if node is in the body of any function.
        """
        from luaparser import astnodes

        # Recursively check all function bodies
        def is_in_function_body(check_node, func_node):
            """Check if check_node is in func_node's body"""
            if not hasattr(func_node, 'body'):
                return False

            body = func_node.body
            if not hasattr(body, 'body'):
                return False

            for stmt in (body.body if isinstance(body.body, list) else [body.body]):
                # Check if this statement is the check_node
                if stmt is check_node:
                    return True

                # Recursively check if the check_node is in nested structures
                stmt_type = type(stmt).__name__
                if stmt_type in ("Fornum", "If", "While", "Forin", "Repeat"):
                    if is_in_function_body(check_node, stmt):
                        return True

            return False

        # Check all function nodes in the chunk
        for stmt in (chunk.body.body if isinstance(chunk.body.body, list) else [chunk.body.body]):
            stmt_type = type(stmt).__name__
            if stmt_type in ("Function", "LocalFunction"):
                if is_in_function_body(node, stmt):
                    return True

        return False
