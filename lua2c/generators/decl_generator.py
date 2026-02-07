"""Declaration generator for Lua2C transpiler

Generates C++ function and variable declarations.
Handles forward declarations for all local functions.
"""

from typing import List
from lua2c.core.context import TranslationContext
from lua2c.generators.naming import NamingScheme

try:
    from luaparser import astnodes
except ImportError:
    raise ImportError("luaparser is required. Install with: pip install luaparser")


class DeclGenerator:
    """Generates C++ declarations for Lua transpilation"""

    def __init__(self, context: TranslationContext) -> None:
        """Initialize declaration generator

        Args:
            context: Translation context
        """
        self.context = context
        self.naming = NamingScheme()

    def generate_forward_declarations(self) -> List[str]:
        """Generate forward declarations for all functions

        Returns:
            List of C++ declaration strings
        """
        declarations = []

        state_type = self.context.get_state_type()
        symbols = self.context.get_all_symbols()
        for symbol in symbols:
            if hasattr(symbol, 'is_function') and symbol.is_function:
                func_name = symbol.name
                decl = f"static luaValue {func_name}({state_type} state);"
                declarations.append(decl)

        return declarations

    def generate_module_export(self, module_path: str) -> str:
        """Generate module export function declaration

        Args:
            module_path: Module path

        Returns:
            C++ function signature
        """
        export_name = self.naming.module_export_name(module_path)
        state_type = self.context.get_state_type()
        # Add 'state' as parameter name
        return f"luaValue {export_name}({state_type} state)"

    def generate_includes(self) -> List[str]:
        """Generate C++ include directives

        Returns:
            List of include statements
        """
        return [
            "#include \"lua_value.hpp\"",
            "#include \"lua_state.hpp\"",
            "#include \"lua_table.hpp\"",
            "#include <vector>",
            "#include <string>",
            "#include <deque>",
            "#include <unordered_map>",
            "#include <variant>",
            "",
        ]
