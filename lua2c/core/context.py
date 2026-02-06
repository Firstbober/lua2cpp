"""Translation context for Lua2C transpiler

Maintains state during transpilation including:
- Scope management
- Symbol table
- String pool
- File and module information
- Generated code fragments
"""

from pathlib import Path
from typing import Optional
from lua2c.core.scope import ScopeManager
from lua2c.core.symbol_table import SymbolTable
from lua2c.generators.string_pool import StringPool


class TranslationContext:
    """Context for transpilation session"""

    def __init__(self, root_dir: Path, module_path: str) -> None:
        """Initialize translation context

        Args:
            root_dir: Project root directory
            module_path: Module filesystem path relative to root
        """
        self.root_dir = root_dir
        self.module_path = module_path

        self.scope_manager = ScopeManager()
        self.symbol_table = SymbolTable(self.scope_manager)
        self.string_pool = StringPool()

        self._current_function_depth = 0

    @property
    def current_function_depth(self) -> int:
        """Get current function nesting depth"""
        return self._current_function_depth

    def enter_function(self) -> None:
        """Enter a new function scope"""
        self._current_function_depth += 1
        self.scope_manager.push_scope()

    def exit_function(self) -> None:
        """Exit current function scope"""
        if self._current_function_depth <= 0:
            raise RuntimeError("Not in a function scope")
        self._current_function_depth -= 1
        self.scope_manager.pop_scope()

    def enter_block(self) -> None:
        """Enter a new block scope (if, while, etc.)"""
        self.scope_manager.push_scope()

    def exit_block(self) -> None:
        """Exit current block scope"""
        self.scope_manager.pop_scope()

    def in_function(self) -> bool:
        """Check if currently in a function"""
        return self._current_function_depth > 0

    def add_string_literal(self, literal: str) -> int:
        """Add a string literal to the pool

        Args:
            literal: String literal

        Returns:
            Index in string pool
        """
        return self.string_pool.add(literal)

    def get_string_literal(self, index: int) -> str:
        """Get string literal by index

        Args:
            index: String pool index

        Returns:
            String literal
        """
        return self.string_pool.get(index)

    def define_local(self, name: str) -> None:
        """Define a local variable

        Args:
            name: Variable name
        """
        self.symbol_table.add_local(name)

    def define_global(self, name: str) -> None:
        """Define a global variable

        Args:
            name: Variable name
        """
        self.symbol_table.add_global(name)

    def define_function(self, name: str, is_global: bool = False) -> None:
        """Define a function

        Args:
            name: Function name
            is_global: True if global function
        """
        self.symbol_table.add_function(name, is_global)

    def define_parameter(self, name: str, param_index: int) -> None:
        """Define a function parameter

        Args:
            name: Parameter name
            param_index: Parameter position
        """
        self.symbol_table.add_parameter(name, param_index)

    def resolve_symbol(self, name: str):
        """Resolve a symbol

        Args:
            name: Symbol name

        Returns:
            Symbol or None
        """
        return self.symbol_table.resolve(name)

    def is_local(self, name: str) -> bool:
        """Check if name is a local variable

        Args:
            name: Variable name

        Returns:
            True if local
        """
        return self.symbol_table.is_local(name)

    def is_global(self, name: str) -> bool:
        """Check if name is a global variable

        Args:
            name: Variable name

        Returns:
            True if global
        """
        return self.symbol_table.is_global(name)

    def get_all_symbols(self) -> list:
        """Get all symbols

        Returns:
            List of all symbols
        """
        return self.symbol_table.get_all_symbols()

    def get_string_pool(self) -> StringPool:
        """Get string pool

        Returns:
            String pool instance
        """
        return self.string_pool

    def get_scope_manager(self) -> ScopeManager:
        """Get scope manager

        Returns:
            Scope manager instance
        """
        return self.scope_manager

    def get_symbol_table(self) -> SymbolTable:
        """Get symbol table

        Returns:
            Symbol table instance
        """
        return self.symbol_table
