"""Header generator for state.h API declarations

Generates C++ header file with struct definitions and function declarations
for Lua standard library functions used in transpiled code.
"""

from typing import List, Set, Optional
from lua2cpp.core.library_registry import LibraryFunctionRegistry, LibraryFunction
from lua2cpp.core.library_call_collector import LibraryCall


class HeaderGenerator:
    """Generates state.h header file with library API declarations

    Creates C++ header file containing:
    - Struct definitions for each Lua library module (io, string, math, etc.)
    - Function declarations for global functions (print, tonumber, etc.)
    - Template function definitions inline (header-only pattern)

    Usage:
        collector = LibraryCallCollector()
        collector.visit(chunk)
        library_calls = collector.get_library_calls()

        global_functions = {"print", "tonumber"}  # collected separately

        gen = HeaderGenerator()
        header = gen.generate_header(library_calls, global_functions)
        with open("state.h", "w") as f:
            f.write(header)
    """

    def __init__(self, registry: Optional[LibraryFunctionRegistry] = None) -> None:
        """Initialize header generator

        Args:
            registry: LibraryFunctionRegistry to use for type information
                      (default: None creates new registry)
        """
        self._registry = registry if registry is not None else LibraryFunctionRegistry()

    def generate_header(
        self,
        library_calls: List[LibraryCall],
        global_functions: Set[str]
    ) -> str:
        """Generate complete state.h header file

        Args:
            library_calls: List of LibraryCall objects found in AST
            global_functions: Set of global function names used (print, tonumber, etc.)

        Returns:
            Complete C++ header file content as string
        """
        lines: List[str] = []

        # Add pragma once guard
        lines.append(self._generate_pragma_once())
        lines.append("")

        # Add struct definitions for libraries
        struct_defs = self._generate_struct_definitions(library_calls)
        if struct_defs:
            lines.append("// Library struct definitions")
            lines.extend(struct_defs)
            lines.append("")

        # Add global function declarations
        global_decls = self._generate_global_function_declarations(global_functions)
        if global_decls:
            lines.append("// Global function declarations")
            lines.extend(global_decls)
            lines.append("")

        return "\n".join(lines)

    def _generate_pragma_once(self) -> str:
        """Generate pragma once include guard

        Returns:
            #pragma once directive as string
        """
        return "#pragma once"

    def _generate_struct_definitions(
        self,
        library_calls: List[LibraryCall]
    ) -> List[str]:
        """Generate struct definitions for each library module

        Creates struct definitions for each library (io, string, math, etc.)
        with function declarations for all functions used in library_calls.

        Structs use exact Lua names without namespace.

        Args:
            library_calls: List of LibraryCall objects

        Returns:
            List of struct definition strings
        """
        lines: List[str] = []

        # Group library calls by module name
        modules_used: Set[str] = set()
        for call in library_calls:
            modules_used.add(call.module)

        # Generate struct definition for each module
        for module_name in sorted(modules_used):
            lines.extend(self._generate_module_struct(module_name, library_calls))

        return lines

    def _generate_module_struct(
        self,
        module_name: str,
        library_calls: List[LibraryCall]
    ) -> List[str]:
        """Generate struct definition for a single library module

        Creates struct with exact Lua name (no namespace) containing
        function declarations for all calls to this module.

        Args:
            module_name: Library module name (e.g., "io", "math")
            library_calls: List of all library calls

        Returns:
            List of struct definition strings
        """
        lines: List[str] = []

        # Filter calls for this module
        module_calls = [c for c in library_calls if c.module == module_name]

        # Get unique functions used
        functions_used: Set[str] = set(call.func for call in module_calls)

        # Start struct definition
        lines.append(f"struct {module_name} {{")

        # Add function declarations
        for func_name in sorted(functions_used):
            func_info = self._registry.get_library_info(module_name, func_name)

            if func_info is None:
                # Unknown function - add comment instead
                lines.append(f"    // {module_name}.{func_name} - unknown function signature")
                continue

            # Generate function declaration
            return_type = self._type_kind_to_cpp_type(func_info.return_type)
            cpp_name = func_info.cpp_name

            # Build parameter list
            params = self._build_parameter_list(func_info.params)

            # Generate template function for variadic functions
            from lua2cpp.core.types import TypeKind
            if len(func_info.params) > 0 and func_info.params[-1] == TypeKind.VARIANT:
                # Variadic function - use template
                lines.append(f"    template <typename... Args>")
                lines.append(f"    static {return_type} {cpp_name}(State* state, Args&&... args);")
            else:
                # Non-variadic function
                lines.append(f"    static {return_type} {cpp_name}({params});")

        # End struct definition
        lines.append("};")

        return lines

    def _generate_global_function_declarations(
        self,
        global_functions: Set[str]
    ) -> List[str]:
        """Generate global function declarations

        Generates free function declarations in lua2c:: namespace for
        global Lua functions (print, tonumber, tostring, etc.).

        Args:
            global_functions: Set of global function names used

        Returns:
            List of function declaration strings
        """
        lines: List[str] = []

        # Start namespace
        lines.append("namespace lua2c {")

        # Generate declarations for each function
        for func_name in sorted(global_functions):
            # Get function signature from registry if available
            func_info = self._get_global_function_info(func_name)

            if func_info is None:
                # Unknown function - add comment
                lines.append(f"    // {func_name} - unknown function signature")
                continue

            # Generate function declaration
            return_type = self._type_kind_to_cpp_type(func_info.return_type)
            params = self._build_parameter_list(func_info.params)

            lines.append(f"    {return_type} {func_name}({params});")

        # End namespace
        lines.append("}  // namespace lua2c")

        return lines

    def _type_kind_to_cpp_type(self, type_kind) -> str:
        """Convert TypeKind to C++ type name

        Args:
            type_kind: TypeKind enum value

        Returns:
            C++ type name as string
        """
        from lua2cpp.core.types import TypeKind

        if type_kind == TypeKind.UNKNOWN:
            return "auto"
        elif type_kind == TypeKind.VARIANT:
            return "std::variant<...>"
        elif type_kind == TypeKind.BOOLEAN:
            return "bool"
        elif type_kind == TypeKind.NUMBER:
            return "double"
        elif type_kind == TypeKind.STRING:
            return "std::string"
        elif type_kind == TypeKind.TABLE:
            return "TABLE"
        elif type_kind == TypeKind.FUNCTION:
            return "auto"
        elif type_kind == TypeKind.ANY:
            return "std::variant<...>"
        else:
            return "auto"

    def _build_parameter_list(self, param_types: List) -> str:
        """Build parameter list string for function declaration

        Args:
            param_types: List of TypeKind values

        Returns:
            Parameter list as string (e.g., "State* state, double x, std::string s")
        """
        from lua2cpp.core.types import TypeKind

        params = ["State* state"]

        for param_type in param_types:
            cpp_type = self._type_kind_to_cpp_type(param_type)
            params.append(f"{cpp_type} /* param */")

        return ", ".join(params)

    def _get_global_function_info(self, func_name: str):
        """Get information about a global function

        Returns None for now - global function signatures are not
        yet defined in LibraryFunctionRegistry.

        Args:
            func_name: Global function name

        Returns:
            LibraryFunction object or None
        """
        # Global function signatures are not yet in registry
        # This is a placeholder for future implementation
        return None
