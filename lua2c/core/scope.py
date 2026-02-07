"""Scope management for Lua2C transpiler

Manages variable scoping following Lua's scoping rules:
- Local variables have block scope
- Variables are accessible in their declaring block and nested blocks
- Inner blocks shadow outer block variables with same name
- Global variables are implicitly in the outermost scope
"""

from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from lua2c.core.type_system import Type, TableTypeInfo


class Symbol:
    """Represents a variable or function symbol"""

    def __init__(
        self,
        name: str,
        scope_id: int,
        is_global: bool = False,
        is_function: bool = False,
        param_index: int = -1,
        inferred_type: Optional['Type'] = None,
        table_info: Optional['TableTypeInfo'] = None,
    ) -> None:
        """Initialize symbol

        Args:
            name: Symbol name
            scope_id: Scope where symbol is defined
            is_global: True if this is a global variable
            is_function: True if this is a function definition
            param_index: Parameter index (if function parameter)
            inferred_type: Inferred type information
            table_info: Table type information (for tables)
        """
        self.name = name
        self.scope_id = scope_id
        self.is_global = is_global
        self.is_function = is_function
        self.param_index = param_index
        self.inferred_type = inferred_type
        self.table_info = table_info

    def __repr__(self) -> str:
        type_str = f", type={self.inferred_type.kind.name}" if self.inferred_type else ""
        return (
            f"Symbol(name={self.name!r}, scope_id={self.scope_id}, "
            f"is_global={self.is_global}, is_function={self.is_function}{type_str})"
        )


class Scope:
    """Represents a lexical scope"""

    def __init__(self, parent: Optional["Scope"] = None) -> None:
        """Initialize scope

        Args:
            parent: Parent scope (None for global scope)
        """
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self._next_child_id = 0

    def define(self, name: str, **kwargs) -> Symbol:
        """Define a symbol in this scope

        Args:
            name: Symbol name
            **kwargs: Additional symbol properties (is_global, is_function, param_index)

        Returns:
            Created symbol
        """
        if name in self.symbols:
            raise NameError(f"Symbol '{name}' already defined in scope")
        symbol = Symbol(name, id(self), **kwargs)
        self.symbols[name] = symbol
        return symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up a symbol, checking parent scopes

        Args:
            name: Symbol name

        Returns:
            Symbol if found, None otherwise
        """
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look up a symbol only in this scope

        Args:
            name: Symbol name

        Returns:
            Symbol if found, None otherwise
        """
        return self.symbols.get(name)

    def has(self, name: str) -> bool:
        """Check if symbol exists in this scope

        Args:
            name: Symbol name

        Returns:
            True if symbol exists in this scope
        """
        return name in self.symbols

    def get_depth(self) -> int:
        """Get nesting depth of this scope

        Returns:
            Depth (0 for global scope)
        """
        depth = 0
        current = self
        while current.parent:
            depth += 1
            current = current.parent
        return depth

    def is_global(self) -> bool:
        """Check if this is the global scope

        Returns:
            True if no parent scope
        """
        return self.parent is None


class ScopeManager:
    """Manages lexical scopes during transpilation"""

    def __init__(self) -> None:
        """Initialize scope manager with global scope"""
        self._global_scope = Scope()
        self._current_scope: Scope = self._global_scope
        self._scope_stack: list[Scope] = [self._global_scope]

    @property
    def current_scope(self) -> Scope:
        """Get current scope"""
        return self._current_scope

    @property
    def global_scope(self) -> Scope:
        """Get global scope"""
        return self._global_scope

    def push_scope(self) -> Scope:
        """Push a new scope

        Returns:
            New scope
        """
        new_scope = Scope(self._current_scope)
        self._scope_stack.append(new_scope)
        self._current_scope = new_scope
        return new_scope

    def pop_scope(self) -> Scope:
        """Pop current scope

        Returns:
            Popped scope

        Raises:
            RuntimeError: If trying to pop global scope
        """
        if len(self._scope_stack) == 1:
            raise RuntimeError("Cannot pop global scope")
        popped = self._scope_stack.pop()
        self._current_scope = self._scope_stack[-1]
        return popped

    def define_local(self, name: str, **kwargs) -> Symbol:
        """Define a local variable

        Args:
            name: Variable name
            **kwargs: Additional symbol properties (including inferred_type)

        Returns:
            Created symbol
        """
        return self._current_scope.define(name, is_global=False, **kwargs)

    def define_global(self, name: str, **kwargs) -> Symbol:
        """Define a global variable

        Args:
            name: Variable name
            **kwargs: Additional symbol properties

        Returns:
            Created symbol
        """
        return self._global_scope.define(name, is_global=True, **kwargs)

    def define_function_param(self, name: str, param_index: int) -> Symbol:
        """Define a function parameter

        Args:
            name: Parameter name
            param_index: Parameter index

        Returns:
            Created symbol
        """
        return self._current_scope.define(
            name, is_global=False, is_function=True, param_index=param_index
        )

    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up a symbol

        Args:
            name: Symbol name

        Returns:
            Symbol if found, None otherwise
        """
        return self._current_scope.lookup(name)

    def is_local(self, name: str) -> bool:
        """Check if name is a local variable

        Args:
            name: Variable name

        Returns:
            True if defined in local scope
        """
        symbol = self.lookup(name)
        return symbol is not None and not symbol.is_global

    def is_global(self, name: str) -> bool:
        """Check if name is a global variable

        Args:
            name: Variable name

        Returns:
            True if defined in global scope
        """
        symbol = self.lookup(name)
        return symbol is not None and symbol.is_global

    def current_depth(self) -> int:
        """Get current nesting depth

        Returns:
            Nesting depth (0 for global scope)
        """
        return self._current_scope.get_depth()

    def in_function_scope(self) -> bool:
        """Check if currently in a function scope

        Returns:
            True if depth > 0 (inside a function)
        """
        return self.current_depth() > 0
