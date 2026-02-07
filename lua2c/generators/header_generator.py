"""Module header generator for Lua2C transpiler

Generates .hpp files with forward declarations for each module.
Used in multi-file project mode.
"""

from pathlib import Path
from typing import Optional
from lua2c.generators.naming import NamingScheme


class HeaderGenerator:
    """Generates C++ header files for Lua modules"""

    def __init__(self) -> None:
        """Initialize header generator"""
        self.naming = NamingScheme()

    def generate_module_header(self, module_name: str, project_name: str) -> str:
        """Generate .hpp forward declaration for a module

        Args:
            module_name: Module name (e.g., "utils", "subdir_helper")
            project_name: Project name (e.g., "myproject")

        Returns:
            C++ header file content as string

        Output example (utils_module.hpp):
            #pragma once
            #include "l2c_runtime.hpp"
            #include "myproject_state.hpp"

            luaValue _l2c__utils_module_export(myproject_lua_State* state);
        """
        state_type = f"{project_name}_lua_State"
        export_name = self.naming.module_export_name(module_name)

        lines = [
            "#pragma once",
            "",
            '#include "l2c_runtime.hpp"',
            f'#include "{project_name}_state.hpp"',
            "",
            f"luaValue {export_name}({state_type}* state);",
        ]

        return "\n".join(lines)
