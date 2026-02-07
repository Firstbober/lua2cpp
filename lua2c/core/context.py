"""Translation context for Lua2C transpiler

Maintains state during transpilation including:
- Scope management
- Symbol table
- String pool
- File and module information
- Generated code fragments
- Optimization logging
"""

from pathlib import Path
from typing import Optional
from lua2c.core.scope import ScopeManager
from lua2c.core.symbol_table import SymbolTable
from lua2c.core.optimization_logger import OptimizationLogger


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
        self.optimization_logger = OptimizationLogger()
        self._type_inferencer = None

        self._current_function_depth = 0
        self._mode = 'single'
        self._project_name = None

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

    def define_local(self, name: str, inferred_type: Optional['Type'] = None) -> None:
        """Define a local variable

        Args:
            name: Variable name
            inferred_type: Optional inferred type information
        """
        self.symbol_table.add_local(name, inferred_type=inferred_type)

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

    def get_optimization_logger(self) -> OptimizationLogger:
        """Get optimization logger

        Returns:
            Optimization logger instance
        """
        return self.optimization_logger

    def set_type_inferencer(self, type_inferencer) -> None:
        """Set type inferencer for context

        Args:
            type_inferencer: TypeInference instance
        """
        self._type_inferencer = type_inferencer

    def get_type_inferencer(self):
        """Get type inferencer from context

        Returns:
            TypeInference instance or None
        """
        return self._type_inferencer

    def set_project_mode(self, project_name: str) -> None:
        """Enable project mode with custom state type

        Args:
            project_name: Name of project (e.g., "myproject")
        """
        self._mode = 'project'
        self._project_name = project_name

    def get_mode(self) -> str:
        """Get current transpilation mode

        Returns:
            'single' for single-file mode, 'project' for project mode
        """
        return self._mode

    def get_project_name(self) -> Optional[str]:
        """Get project name if in project mode

        Returns:
            Project name or None if in single-file mode
        """
        return self._project_name

    def set_single_file_mode(self, module_name: str, as_library: bool = False) -> None:
        """Set single-file mode with custom state

        Args:
            module_name: Name of module (e.g., "simple")
            as_library: If True, generate as library (no main.cpp, no arg)
        """
        self._mode = 'single_standalone' if not as_library else 'single_library'
        self._project_name = module_name
        self._as_library = as_library

    def is_library_mode(self) -> bool:
        """Check if generating as library (no main.cpp, no arg member)

        Returns:
            True if in library mode
        """
        return self._mode == 'single_library'

    def get_state_type(self) -> str:
        """Get C++ state type name based on mode

        Returns:
            '{project_name}_lua_State*' for custom state modes
            'luaState*' for legacy (should never be used after migration)
        """
        if self._mode in ('project', 'single_standalone', 'single_library'):
            return f"{self._project_name}_lua_State*"
        return "luaState*"
