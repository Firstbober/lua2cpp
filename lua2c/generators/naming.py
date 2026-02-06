"""Naming scheme for Lua2C transpiler

Implements the naming convention:
- Modules: _l2c__<dir>__<file>_export
- Functions: _l2c__<dir>__<file>_<method>
"""

from pathlib import Path
import re


class NamingScheme:
    """Handles C identifier generation for Lua constructs"""

    PREFIX = "_l2c"
    MODULE_EXPORT_SUFFIX = "_export"

    @staticmethod
    def sanitize_path(path: str) -> str:
        """Convert filesystem path to C identifier-safe string

        Args:
            path: Filesystem path (e.g., "src/core/utils")

        Returns:
            Sanitized string (e.g., "__src__core__utils")
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
        # Replace 3+ underscores with __
        normalized = re.sub(r"_{3,}", "__", normalized)

        return f"__{normalized}" if normalized else ""

    @staticmethod
    def module_export_name(module_path: str) -> str:
        """Generate the export function name for a module

        Args:
            module_path: Module filesystem path relative to project root

        Returns:
            C function name (e.g., "_l2c__src__core__utils_export")
        """
        sanitized = NamingScheme.sanitize_path(module_path)
        return f"{NamingScheme.PREFIX}{sanitized}{NamingScheme.MODULE_EXPORT_SUFFIX}"

    @staticmethod
    def function_name(module_path: str, function_name: str) -> str:
        """Generate a function name

        Args:
            module_path: Module filesystem path
            function_name: Lua function name

        Returns:
            C function name (e.g., "_l2c__src__core__utils_myFunction")
        """
        sanitized = NamingScheme.sanitize_path(module_path)
        sanitized_function = function_name.replace("-", "_")
        return f"{NamingScheme.PREFIX}{sanitized}_{sanitized_function}"

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
