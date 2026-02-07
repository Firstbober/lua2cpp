"""Main file generator for Lua2C multi-file projects

Generates main.cpp for projects with module initialization, library function pointers,
and command-line argument handling.
"""

from typing import Set, List, Optional
from pathlib import Path
from lua2c.core.global_type_registry import GlobalTypeRegistry
from lua2c.generators.naming import NamingScheme


class MainGenerator:
    """Generates main.cpp for multi-file Lua2C projects"""

    def __init__(self) -> None:
        """Initialize main generator"""
        self.naming = NamingScheme()
        self.registry = GlobalTypeRegistry()

    def generate_main_file(
        self,
        project_name: str,
        main_file_path: Path,
        globals: Set[str],
        dependency_order: List[str],
        used_libraries: Optional[Set[str]] = None,
    ) -> str:
        """Generate main.cpp with module initialization

        Args:
            project_name: Name of project (e.g., "myproject")
            main_file_path: Path to main.lua file
            globals: Set of global variable names used
            dependency_order: List of module names in topological order
            used_libraries: Set of library modules used (io, math, etc.)

        Returns:
            Generated C++ code as string

        Output example (myproject_main.cpp):
            #include "l2c_runtime.hpp"
            #include "myproject_state.hpp"

            // Forward declarations for all modules
            luaValue _l2c__main_export(myproject_lua_State* state);
            luaValue _l2c__utils_export(myproject_lua_State* state);

            int main(int argc, char* argv[]) {
                // Auto-generated main for myproject

                // Create project state
                myproject_lua_State state;

                // Set command line arguments
                state.arg = luaArray<luaValue>{{}};
                for (int i = 1; i < argc; ++i) {
                    state.arg.set(i - 1, luaValue(argv[i]));
                }

                // Initialize library function pointers
                state.io.write = &l2c::io_write;
                state.math.sqrt = &l2c::math_sqrt;
                state.print = &l2c::print;

                // Initialize modules (in dependency order)
                state.modules["utils"] = &_l2c__utils_export;
                state.modules["main"] = &_l2c__main_export;

                // Call main module entry point
                luaValue result = _l2c__main_export(&state);

                return 0;
            }
        """
        if used_libraries is None:
            used_libraries = self._detect_used_libraries_from_globals(globals)

        # Extract main module name from main file path
        main_module_name = self._extract_main_module_name(main_file_path)

        lines = []

        # Generate includes
        lines.extend(self._generate_includes(project_name))

        # Generate forward declarations
        lines.extend(self._generate_forward_declarations(project_name, dependency_order))

        # Generate main function
        lines.append(f"int main(int argc, char* argv[]) {{")
        lines.append(f"    // Auto-generated main for {project_name}")
        lines.append("")

        # Create project state
        state_type = f"{project_name}_lua_State"
        lines.append(f"    // Create project state")
        lines.append(f"    {state_type} state;")
        lines.append("")

        # Initialize command line arguments
        lines.extend(self._generate_arg_initialization())

        # Initialize library function pointers
        lines.extend(self._generate_library_initialization(used_libraries))

        # Register modules in dependency order
        lines.extend(self._generate_module_registration(project_name, dependency_order))

        # Call main module entry point
        lines.extend(self._generate_main_entry(project_name, main_module_name))

        return "\n".join(lines)

    def _generate_includes(self, project_name: str) -> List[str]:
        """Generate #include statements

        Args:
            project_name: Name of project

        Returns:
            List of C++ include lines
        """
        return [
            '#include "l2c_runtime.hpp"',
            f'#include "{project_name}_state.hpp"',
            "",
        ]

    def _generate_forward_declarations(
        self, project_name: str, dependency_order: List[str]
    ) -> List[str]:
        """Generate forward declarations for all modules

        Args:
            project_name: Name of project
            dependency_order: List of module names in dependency order

        Returns:
            List of C++ forward declaration lines
        """
        state_type = f"{project_name}_lua_State"
        lines = ["// Forward declarations for all modules"]
        for module_name in dependency_order:
            export_name = self.naming.module_export_name(module_name)
            lines.append(f"luaValue {export_name}({state_type}* state);")
        return lines + [""]

    def _generate_arg_initialization(self) -> List[str]:
        """Generate command-line argument initialization (1-based indexing)

        Returns:
            List of C++ code lines for arg initialization
        """
        return [
            "    // Set command line arguments",
            "    state.arg = luaArray<luaValue>{{}};",
            "    for (int i = 1; i < argc; ++i) {",
            "        state.arg.set(i - 1, luaValue(argv[i]));",
            "    }",
            "",
        ]

    def _generate_library_initialization(self, used_libraries: Set[str]) -> List[str]:
        """Initialize library function pointers

        Args:
            used_libraries: Set of library module names used (io, math, etc.)

        Returns:
            List of C++ code lines for library initialization
        """
        lines = ["    // Initialize library function pointers"]

        # Library modules (io, math, string, table, os)
        for lib_name in sorted(used_libraries):
            functions = self.registry.get_module_functions(lib_name)
            if functions:
                for func_name in sorted(functions):
                    full_name = f"{lib_name}.{func_name}"
                    sig = self.registry.get_function_signature(full_name)
                    if sig:
                        lines.append(
                            f"    state.{lib_name}.{func_name} = &l2c::{lib_name}_{func_name};"
                        )

        # Standalone functions (print, tonumber)
        for func_name in ["print", "tonumber"]:
            sig = self.registry.get_function_signature(func_name)
            if sig:
                lines.append(f"    state.{func_name} = &l2c::{func_name};")

        return lines + [""]

    def _generate_module_registration(
        self, project_name: str, dependency_order: List[str]
    ) -> List[str]:
        """Register modules in dependency order

        Args:
            project_name: Name of project
            dependency_order: List of module names in dependency order

        Returns:
            List of C++ code lines for module registration
        """
        order_str = " → ".join(dependency_order)
        lines = [f"    // Initialize modules (in dependency order: {order_str})"]

        for module_name in dependency_order:
            export_name = self.naming.module_export_name(module_name)
            lines.append(f'    state.modules["{module_name}"] = &{export_name};')

        return lines + [""]

    def _generate_main_entry(self, project_name: str, main_module_name: str) -> List[str]:
        """Generate call to main module entry point

        Args:
            project_name: Name of project
            main_module_name: Name of main module

        Returns:
            List of C++ code lines for main entry point call
        """
        export_name = self.naming.module_export_name(main_module_name)
        return [
            "    // Call main module entry point",
            f"    luaValue result = {export_name}(&state);",
            "",
            "    return 0;",
            "}",
        ]

    def _extract_main_module_name(self, main_file_path: Path) -> str:
        """Extract main module name from file path

        Args:
            main_file_path: Path to main.lua file

        Returns:
            Module name (filename without extension)
        """
        return main_file_path.stem

    def _detect_used_libraries_from_globals(self, globals: Set[str]) -> Set[str]:
        """Detect used libraries from globals (fallback method)

        Args:
            globals: Set of global variable names

        Returns:
            Set of library module names
        """
        used_libs: Set[str] = set()
        for lib in ["io", "math", "string", "table", "os"]:
            if lib in globals or any(g.startswith(f"{lib}.") for g in globals):
                used_libs.add(lib)
        return used_libs
