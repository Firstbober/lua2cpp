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

        symbols = self.context.get_all_symbols()
        for symbol in symbols:
            if hasattr(symbol, 'symbol_type') and symbol.symbol_type == 'function':
                func_name = symbol.name
                decl = f"static luaValue {func_name}(luaState* state);"
                declarations.append(decl)

        return declarations

    def generate_string_pool(self) -> str:
        """Generate string pool declarations

        Returns:
            C++ code for string pool
        """
        pool = self.context.get_string_pool()
        strings = pool.all_strings()

        if not strings:
            return "static const char* string_pool[] = {nullptr};"

        lines = ["static const char* string_pool[] = {"]
        for i, s in enumerate(strings):
            escaped = s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            lines.append(f'    "{escaped}",  /* {i} */')
        lines.append("    nullptr")
        lines.append("};")

        return "\n".join(lines)

    def generate_module_export(self, module_path: str) -> str:
        """Generate module export function declaration

        Args:
            module_path: Module path

        Returns:
            C++ function signature
        """
        export_name = self.naming.module_export_name(module_path)
        return f"luaValue {export_name}(luaState* state)"

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
            "",
        ]
