"""Project state generator for Lua2C transpiler

Generates ONE custom state class per project with typed members.
Replaces generic luaState with per-project typed state.
"""

from typing import Set, Dict, List, Optional, Any, TYPE_CHECKING
import re
from pathlib import Path
from lua2c.core.global_type_registry import GlobalTypeRegistry

if TYPE_CHECKING:
    from lua2c.core.type_system import Type


class ProjectStateGenerator:
    """Generates project-specific state class"""

    def __init__(self, project_name: str) -> None:
        """Initialize state generator

        Args:
            project_name: Project name (e.g., "myproject")
        """
        self.project_name = project_name
        self.registry = GlobalTypeRegistry()

    def generate_state_class(
        self, globals: Set[str], modules: Set[str], library_modules: Optional[Set[str]] = None,
        include_module_registry: bool = True, include_arg: bool = True,
        inferred_types: Optional[Dict[str, 'Type']] = None
    ) -> str:
        """Generate custom state class for project

        Args:
            globals: Set of global variable names used across project
            modules: Set of module names in the project
            library_modules: Set of library modules used (io, math, etc.)
            include_module_registry: If False, skip module registry (for single-file mode)
            include_arg: If False, skip arg member (for library mode)
            inferred_types: Optional dict of global name -> inferred Type

        Returns:
            C++ struct definition as string

        Output example (myproject_state.hpp):
            #pragma once

            #include "l2c_runtime.hpp"
            #include <unordered_map>

            struct myproject_lua_State {
                // Command-line arguments array
                luaArray<luaValue> arg;

                // IO library
                struct {
                    void(*)(const std::vector<luaValue>&)* write;
                } io;

                // Math library
                struct {
                    double(*)(double)* sqrt;
                } math;

                // Module registry (for require() dispatch)
                std::unordered_map<std::string,
                    luaValue(*)(myproject_lua_State*)> modules;
            };
        """
        if library_modules is None:
            library_modules = set()

        state_type = f"{self.project_name}_lua_State"
        lines = [
            "#pragma once",
            "",
            '#include "l2c_runtime.hpp"',
            "#include <unordered_map>",
            "",
            f"struct {state_type} {{",
        ]

        # Add special globals (arg, _G) - only if include_arg
        if include_arg:
            global_lines = self._generate_special_globals(globals, inferred_types)
            if global_lines:
                lines.extend(["    // Special globals"] + global_lines + [""])

        # Add standalone function pointers (print, tonumber)
        standalone_lines = self._generate_standalone_functions()
        if standalone_lines:
            lines.extend(["    // Standalone functions"] + standalone_lines + [""])

        # Add library function pointers
        for lib_name in sorted(library_modules):
            lib_lines = self._generate_library_struct(lib_name)
            if lib_lines:
                lines.extend(lib_lines + [""])

        # Add module registry (only for project mode with multiple modules)
        if include_module_registry and modules:
            lines.extend(self._generate_module_registry(modules))

        lines.extend(
            [
                "};",
                "",
            ]
        )

        return "\n".join(lines)

    def _generate_special_globals(
        self, used_globals: Set[str], inferred_types: Optional[Dict[str, 'Type']] = None
    ) -> List[str]:
        """Generate C++ members for special globals

        Args:
            used_globals: Set of global names used in project
            inferred_types: Optional dict of global name -> inferred Type

        Returns:
            List of C++ member declaration lines
        """
        from lua2c.core.type_system import TypeKind

        lines = []
        for global_name in sorted(used_globals):
            c_type = self.registry.get_global_type(global_name)
            if c_type:
                # Special global (arg, _G) - use registered type
                comment = f"    // {global_name}"
                declaration = f"    {c_type} {global_name};"
                lines.append(comment)
                lines.append(declaration)
            else:
                # User-defined global - use inferred type or default to luaValue
                inferred_type = None
                if inferred_types and global_name in inferred_types:
                    inferred_type = inferred_types[global_name]

                comment = f"    // {global_name} (user-defined)"
                if inferred_type and inferred_type.can_specialize() and inferred_type.kind != TypeKind.TABLE:
                    cpp_type = inferred_type.cpp_type()
                    declaration = f"    {cpp_type} {global_name};"
                else:
                    declaration = f"    luaValue {global_name};"
                lines.append(comment)
                lines.append(declaration)

        return lines

    def _generate_standalone_functions(self) -> List[str]:
        """Generate C++ members for standalone Lua functions (print, tonumber, module-level main)
        
        Returns:
            List of C++ member declaration lines
        """
        lines = []
        standalone_funcs = ["print", "tonumber", "assert", "l2c_pow"]

        for func_name in sorted(standalone_funcs):
            sig = self.registry.get_function_signature(func_name)
            if sig:
                # Parse cpp_signature and reformat with function name
                match = re.search(r'\(\*\)\((.*)\)', sig.cpp_signature)
                if match:
                    param_type = match.group(1)
                    return_type = sig.cpp_signature.split('(*)')[0]
                    declaration = f"    {return_type}(*{func_name})({param_type});"
                else:
                    declaration = f"    {sig.cpp_signature} {func_name};"
                lines.append(declaration)

        # Detect module-level main() functions by checking symbol table
        module_main_funcs = []
        if hasattr(self, 'symbol_table'):
            for symbol in self.symbol_table.get_all_symbols():
                if hasattr(symbol, 'name') and symbol.name.lower() == 'main':
                    func_name = symbol.name
                    # Check if not a local function by checking body
                    # Functions with body are defined; module-level functions are just references
                    if not symbol.is_local:
                        module_main_funcs.append(func_name)
        
        # Add function pointer declarations for module-level main() functions
        for func_name in sorted(module_main_funcs):
            sig = self.registry.get_function_signature(func_name)
            if sig:
                # Parse cpp_signature and reformat with function name
                match = re.search(r'\(\*\)\((.*)\)', sig.cpp_signature)
                if match:
                    param_type = match.group(1)
                    return_type = sig.cpp_signature.split('(*)')[0]
                    declaration = f"        luaValue (*{func_name})({param_type});"
                else:
                    declaration = f"        luaValue (*{func_name}){sig.cpp_signature};"
                lines.append(declaration)
            else:
                print(f"DEBUG: Skipping function pointer for {func_name} - no signature found")
        
        return lines

    def _generate_library_struct(self, lib_name: str) -> List[str]:
        """Generate C++ struct for library function pointers

        Args:
            lib_name: Library name (e.g., "io", "math", "string")

        Returns:
            List of C++ lines including comment and struct
        """
        functions = self.registry.get_module_functions(lib_name)
        if not functions:
            return []

        lines = [
            f"    // {lib_name.capitalize()} library",
            f"    struct {{",
        ]

        for func_name in sorted(functions):
            sig = self.registry.get_function_signature(f"{lib_name}.{func_name}")
            if sig:
                # Format: return_type(*func_name)(params); for struct members
                # Parse cpp_signature which is like "void(*)(const std::vector<luaValue>&)"
                # and reformat to "void(*func_name)(const std::vector<luaValue>&);"
                # Parse cpp_signature which is like "void(*)(const std::vector<luaValue>&)"
                # and reformat to "void(*func_name)(const std::vector<luaValue>&);"
                # Use regex to extract parameter type
                match = re.search(r'\(\*\)\((.*)\)', sig.cpp_signature)
                if match:
                    param_type = match.group(1)
                    return_type = sig.cpp_signature.split('(*)')[0]
                    declaration = f"        {return_type}(*{func_name})({param_type});"
                else:
                    # Fallback: just use as-is (shouldn't happen)
                    declaration = f"        {sig.cpp_signature} {func_name};"
                lines.append(declaration)

        lines.append(f"    }} {lib_name};")

        return lines

    def _generate_module_registry(self, modules: Set[str]) -> List[str]:
        """Generate module registry for require() dispatch

        Args:
            modules: Set of module names

        Returns:
            List of C++ lines for module registry
        """
        state_type = f"{self.project_name}_lua_State"
        lines = [
            "    // Module registry (for require() dispatch)",
            f"    std::unordered_map<std::string, ",
            f"        luaValue(*)({state_type}*)> modules;",
        ]
        return lines

    def detect_used_libraries(self, lua_files: List[Path], project_root: Path) -> Set[str]:
        """Detect which library modules are used in the project

        Args:
            lua_files: List of .lua file paths
            project_root: Project root directory

        Returns:
            Set of library module names used (io, math, string, etc.)

        Note: This is a helper for CLI transpile_project() to call
        """
        from luaparser import ast

        used_libs: Set[str] = set()

        for lua_file in lua_files:
            file_path = project_root / lua_file
            if not file_path.exists():
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            try:
                tree = ast.parse(source)
                self._collect_library_usage(tree, used_libs)
            except Exception:
                # If parsing fails, skip file
                continue

        return used_libs

    def _collect_library_usage(self, chunk: Any, used_libs: Set[str]) -> None:
        """Recursively collect library module usage from AST

        Args:
            chunk: AST node (chunk, statement, or expression)
            used_libs: Set to populate with used library names
        """
        # Check if node is an Index expression like io.write or math.sqrt
        if hasattr(chunk, "value") and hasattr(chunk, "idx"):
            if hasattr(chunk.value, "id"):
                lib_name = chunk.value.id
                if self.registry.is_library_module(lib_name):
                    used_libs.add(lib_name.lower())

        # Recursively visit child nodes
        child_fields = []
        if hasattr(chunk, "body"):
            if hasattr(chunk.body, "body"):
                child_fields.extend(chunk.body.body)
            elif isinstance(chunk.body, list):
                child_fields.extend(chunk.body)
            else:
                child_fields.append(chunk.body)

        if hasattr(chunk, "left") and chunk.left:
            child_fields.append(chunk.left)
        if hasattr(chunk, "right") and chunk.right:
            child_fields.append(chunk.right)
        if hasattr(chunk, "operand") and chunk.operand:
            child_fields.append(chunk.operand)
        if hasattr(chunk, "func") and chunk.func:
            child_fields.append(chunk.func)
        if hasattr(chunk, "args") and chunk.args:
            child_fields.extend(chunk.args)
        if hasattr(chunk, "targets") and chunk.targets:
            child_fields.extend(chunk.targets)
        if hasattr(chunk, "values") and chunk.values:
            child_fields.extend(chunk.values)
        if hasattr(chunk, "test") and chunk.test:
            child_fields.append(chunk.test)
        if hasattr(chunk, "orelse") and chunk.orelse:
            if isinstance(chunk.orelse, list):
                child_fields.extend(chunk.orelse)
            else:
                child_fields.append(chunk.orelse)

        for child in child_fields:
            if isinstance(child, list):
                for item in child:
                    if hasattr(item, "__class__"):
                        self._collect_library_usage(item, used_libs)
            elif hasattr(child, "__class__"):
                self._collect_library_usage(child, used_libs)
