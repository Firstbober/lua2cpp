"""Naming scheme for Lua2C transpiler

Implements a naming convention:
- Modules: _l2c__<dir>__<file>_export
- Functions: _l2c__<dir>__<file>_<method>
- C++ Keywords: mangled by appending _lua suffix

Handles C identifier sanitization and keyword collision avoidance.
"""

from pathlib import Path
import re

class NamingScheme:
    """Handles C identifier generation for Lua constructs"""

    PREFIX = "_l2c__"
    MODULE_EXPORT_SUFFIX = "_export"

    # C++ reserved keywords that need mangling
    CPP_KEYWORDS = {
        'alignas', 'and', 'and_eq', 'asm', 'auto', 'bitand', 'bitor',
        'bitxor', 'bool', 'break', 'case', 'catch', 'char', 'char8_t',
        'char16_t', 'class', 'compl', 'const', 'const_cast', 'consteval',
        'constexpr', 'continue', 'decltype', 'default', 'delete', 'do', 'double',
        'dynamic_cast', 'else', 'enum', 'explicit', 'export', 'extern',
        'false', 'float', 'for', 'friend', 'goto', 'if', 'inline', 'int',
        'long', 'long double', 'mutable', 'namespace', 'new', 'noexcept',
        'not', 'nullptr', 'operator', 'or', 'or_eq', 'private', 'protected',
        'public', 'register', 'reinterpret_cast', 'return', 'short', 'signed',
        'sizeof', 'static', 'static_assert', 'struct', 'switch', 'template',
        'this', 'thread_local', 'throw', 'true', 'try', 'typedef', 'typeid',
        'typename', 'union', 'unsigned', 'using', 'virtual', 'void', 'volatile',
        'wchar_t', 'while', 'xor', 'xor_eq',
        'main',  # Special case for Lua main() functions
    }

    @staticmethod
    def sanitize_path(path: str, add_prefix: bool = False) -> str:
        """Convert filesystem path to C identifier-safe string

        Args:
            path: Filesystem path (e.g., "src/core/utils")
            add_prefix: If True, add __ prefix for path-separated inputs

        Returns:
            Sanitized string (e.g., "__src__core__utils" or "spectral-norm")
        """
        if not path:
            return ""

        # First replace path separators with a temporary marker
        temp = path.replace("/", "\x00").replace("\\", "\x00")
        # Replace dashes with single underscores
        temp = temp.replace("-", "_")
        # Convert path separators back to double underscores
        normalized = temp.replace("\x00", "__")
        # Strip leading/trailing underscores
        normalized = normalized.strip("_")
        # Collapse multiple consecutive underscores, preserving path separators
        # Replace 3+ consecutive underscores with __ (for path separators like ___ -> __)
        normalized = re.sub(r"(_)\1{2,}", "__", normalized)

        # Add __ prefix if input had path separators OR explicitly requested
        had_path_separator = "\x00" in temp
        if normalized and (had_path_separator or add_prefix):
            return f"__{normalized}"
        return normalized

    @staticmethod
    def module_export_name(module_path: str) -> str:
        """Generate export function name for a module

        Args:
            module_path: Module filesystem path or module name

        Returns:
            C function name (e.g., "_l2c__utils_export")
        """
        sanitized = NamingScheme.sanitize_path(module_path)
        return f"{NamingScheme.PREFIX}{sanitized}{NamingScheme.MODULE_EXPORT_SUFFIX}"

    @staticmethod
    def mangle_function_name(func_name: str, is_local: bool = True) -> str:
        """Mangle function name if it conflicts with C++ keywords

        Args:
            func_name: Original Lua function name
            is_local: Whether this is a local function (not the main entry point)

        Returns:
            Mangled function name (with _lua suffix if needed)
        """
        # Local functions don't need mangling unless it's 'main' at module level
        # For module-level main functions, we always mangle to avoid C++ keyword
        if not is_local and func_name.lower() == 'main':
            return f"{func_name}_lua"
        
        # For other C++ keywords, add _lua suffix
        if func_name.lower() in NamingScheme.CPP_KEYWORDS:
            return f"{func_name}_lua"
        
        return func_name

    @staticmethod
    def variable_name(scope_path: str, var_name: str) -> str:
        """Generate a variable name (with optional scope prefix)

        Args:
            scope_path: Scope path for uniqueness
            var_name: Variable name

        Returns:
            C variable name
        """
        if not scope_path:
            return var_name
        sanitized_scope = NamingScheme.sanitize_path(scope_path)
        return f"{NamingScheme.PREFIX}{sanitized_scope}_{var_name}"

    @staticmethod
    def string_literal_name(index: int) -> str:
        """Generate name for a string literal in the string pool

        Args:
            index: Index in the string pool

        Returns:
            C identifier name (e.g., "_l2c_string_42")
        """
        return f"{NamingScheme.PREFIX}_string_{index}"

    @staticmethod
    def is_valid_identifier(name: str) -> bool:
        """Check if a string is a valid C identifier

        Args:
            name: String to check

        Returns:
            True if valid C identifier
        """
        if not name or name[0].isdigit():
            return False
        return all(c.isalnum() or c == "_" for c in name)
