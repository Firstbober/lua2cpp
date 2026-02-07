"""Symbol table for Lua2C transpiler

Provides unified symbol resolution and management across all scopes.
Works with ScopeManager to track variables, functions, and their attributes.
"""

from typing import Optional, List
from lua2c.core.scope import ScopeManager, Symbol


class SymbolTable:
    """Unified symbol table for transpilation"""

    def __init__(self, scope_manager: ScopeManager) -> None:
        """Initialize symbol table

        Args:
            scope_manager: Scope manager to use for tracking symbols
        """
        self._scope_manager = scope_manager
        self._all_symbols: List[Symbol] = []

    def add_local(self, name: str, inferred_type: Optional['Type'] = None, **kwargs) -> Symbol:
        """Add a local variable

        Args:
            name: Variable name
            inferred_type: Optional inferred type information
            **kwargs: Additional symbol properties

        Returns:
            Created symbol
        """
        if inferred_type is not None:
            kwargs['inferred_type'] = inferred_type
        symbol = self._scope_manager.define_local(name, **kwargs)
        self._all_symbols.append(symbol)
        return symbol

    def add_global(self, name: str, **kwargs) -> Symbol:
        """Add a global variable

        Args:
            name: Variable name
            **kwargs: Additional symbol properties

        Returns:
            Created symbol
        """
        symbol = self._scope_manager.define_global(name, **kwargs)
        self._all_symbols.append(symbol)
        return symbol

    def add_function(self, name: str, is_global: bool = False) -> Symbol:
        """Add a function definition

        Args:
            name: Function name
            is_global: True if global function

        Returns:
            Created symbol
        """
        if is_global:
            return self.add_global(name, is_function=True)
        return self.add_local(name, is_function=True)

    def add_parameter(self, name: str, param_index: int) -> Symbol:
        """Add a function parameter

        Args:
            name: Parameter name
            param_index: Parameter position

        Returns:
            Created symbol
        """
        symbol = self._scope_manager.define_function_param(name, param_index)
        self._all_symbols.append(symbol)
        return symbol

    def resolve(self, name: str) -> Optional[Symbol]:
        """Resolve a symbol by name

        Args:
            name: Symbol name

        Returns:
            Symbol if found, None otherwise
        """
        return self._scope_manager.lookup(name)

    def resolve_required(self, name: str) -> Symbol:
        """Resolve a symbol, raising if not found

        Args:
            name: Symbol name

        Returns:
            Symbol

        Raises:
            NameError: If symbol not found
        """
        symbol = self.resolve(name)
        if symbol is None:
            raise NameError(f"Symbol '{name}' not found")
        return symbol

    def get_all_symbols(self) -> List[Symbol]:
        """Get all symbols added to table

        Returns:
            List of all symbols
        """
        return list(self._all_symbols)

    def get_symbols_in_scope(self, scope_id: int) -> List[Symbol]:
        """Get all symbols defined in a specific scope

        Args:
            scope_id: Scope ID

        Returns:
            List of symbols in that scope
        """
        return [s for s in self._all_symbols if s.scope_id == scope_id]

    def get_global_symbols(self) -> List[Symbol]:
        """Get all global symbols

        Returns:
            List of global symbols
        """
        return [s for s in self._all_symbols if s.is_global]

    def get_function_symbols(self) -> List[Symbol]:
        """Get all function symbols

        Returns:
            List of function symbols
        """
        return [s for s in self._all_symbols if s.is_function]

    def get_local_symbols(self) -> List[Symbol]:
        """Get all local symbols

        Returns:
            List of local symbols
        """
        return [s for s in self._all_symbols if not s.is_global]

    def is_defined(self, name: str) -> bool:
        """Check if name is defined

        Args:
            name: Symbol name

        Returns:
            True if symbol exists
        """
        return self.resolve(name) is not None

    def is_local(self, name: str) -> bool:
        """Check if name is a local variable

        Args:
            name: Variable name

        Returns:
            True if defined locally
        """
        return self._scope_manager.is_local(name)

    def is_global(self, name: str) -> bool:
        """Check if name is a global variable

        Args:
            name: Variable name

        Returns:
            True if defined globally
        """
        return self._scope_manager.is_global(name)

    def is_function(self, name: str) -> bool:
        """Check if name is a function

        Args:
            name: Function name

        Returns:
            True if symbol is a function
        """
        symbol = self.resolve(name)
        return symbol is not None and symbol.is_function

    def clear(self) -> None:
        """Clear all symbols (except scope structure)"""
        self._all_symbols.clear()
