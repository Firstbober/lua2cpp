"""Tests for symbol table"""

import pytest
from lua2c.core.scope import ScopeManager
from lua2c.core.symbol_table import SymbolTable


class TestSymbolTable:
    """Test suite for SymbolTable"""

    def test_initial_state(self):
        """Test initial empty state"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        assert table.get_all_symbols() == []
        assert table.is_defined("x") is False

    def test_add_local(self):
        """Test adding local variable"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        symbol = table.add_local("x")
        assert symbol.name == "x"
        assert symbol.is_global is False
        assert table.is_defined("x") is True

    def test_add_global(self):
        """Test adding global variable"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        symbol = table.add_global("g")
        assert symbol.name == "g"
        assert symbol.is_global is True
        assert table.is_defined("g") is True

    def test_add_function_local(self):
        """Test adding local function"""
        manager = ScopeManager()
        manager.push_scope()
        table = SymbolTable(manager)
        symbol = table.add_function("foo", is_global=False)
        assert symbol.name == "foo"
        assert symbol.is_function is True
        assert symbol.is_global is False

    def test_add_function_global(self):
        """Test adding global function"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        symbol = table.add_function("bar", is_global=True)
        assert symbol.name == "bar"
        assert symbol.is_function is True
        assert symbol.is_global is True

    def test_add_parameter(self):
        """Test adding function parameter"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        symbol = table.add_parameter("arg", 0)
        assert symbol.name == "arg"
        assert symbol.param_index == 0
        assert symbol.is_function is True

    def test_resolve_found(self):
        """Test resolving existing symbol"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        added = table.add_local("x")
        resolved = table.resolve("x")
        assert resolved is added

    def test_resolve_not_found(self):
        """Test resolving non-existent symbol"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        assert table.resolve("nonexistent") is None

    def test_resolve_required_found(self):
        """Test resolve_required with existing symbol"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        added = table.add_local("x")
        resolved = table.resolve_required("x")
        assert resolved is added

    def test_resolve_required_not_found(self):
        """Test resolve_required raises for non-existent symbol"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        with pytest.raises(NameError):
            table.resolve_required("nonexistent")

    def test_get_all_symbols(self):
        """Test getting all symbols"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        table.add_local("x")
        table.add_local("y")
        table.add_global("g")

        symbols = table.get_all_symbols()
        assert len(symbols) == 3
        names = [s.name for s in symbols]
        assert "x" in names
        assert "y" in names
        assert "g" in names

    def test_get_symbols_in_scope(self):
        """Test getting symbols in specific scope"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        sym1 = table.add_local("x")
        scope_id = sym1.scope_id

        manager.push_scope()
        table.add_local("y")

        scope_symbols = table.get_symbols_in_scope(scope_id)
        assert len(scope_symbols) == 1
        assert scope_symbols[0].name == "x"

    def test_get_global_symbols(self):
        """Test getting global symbols"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        table.add_local("x")
        table.add_global("g1")
        table.add_global("g2")

        global_symbols = table.get_global_symbols()
        assert len(global_symbols) == 2
        names = [s.name for s in global_symbols]
        assert "g1" in names
        assert "g2" in names
        assert "x" not in names

    def test_get_function_symbols(self):
        """Test getting function symbols"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        table.add_local("var")
        table.add_function("foo")
        table.add_function("bar")

        func_symbols = table.get_function_symbols()
        assert len(func_symbols) == 2
        names = [s.name for s in func_symbols]
        assert "foo" in names
        assert "bar" in names
        assert "var" not in names

    def test_get_local_symbols(self):
        """Test getting local symbols"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        table.add_local("x")
        table.add_local("y")
        table.add_global("g")

        local_symbols = table.get_local_symbols()
        assert len(local_symbols) == 2
        names = [s.name for s in local_symbols]
        assert "x" in names
        assert "y" in names
        assert "g" not in names

    def test_is_local(self):
        """Test is_local check"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        table.add_local("x")
        table.add_global("g")
        assert table.is_local("x") is True
        assert table.is_local("g") is False

    def test_is_global(self):
        """Test is_global check"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        table.add_local("x")
        table.add_global("g")
        assert table.is_global("g") is True
        assert table.is_global("x") is False

    def test_is_function(self):
        """Test is_function check"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        table.add_local("var")
        table.add_function("func")
        assert table.is_function("func") is True
        assert table.is_function("var") is False

    def test_clear(self):
        """Test clearing symbols"""
        manager = ScopeManager()
        table = SymbolTable(manager)
        table.add_local("x")
        table.add_global("g")
        assert len(table.get_all_symbols()) == 2

        table.clear()
        assert len(table.get_all_symbols()) == 0

    def test_nested_scopes(self):
        """Test symbols across nested scopes"""
        manager = ScopeManager()
        table = SymbolTable(manager)

        table.add_global("g1")
        table.add_local("x")

        manager.push_scope()
        table.add_local("y")

        manager.push_scope()
        table.add_local("z")

        # All should be defined
        assert table.is_defined("g1")
        assert table.is_defined("x")
        assert table.is_defined("y")
        assert table.is_defined("z")

        # All accessible
        assert table.resolve("g1") is not None
        assert table.resolve("x") is not None
        assert table.resolve("y") is not None
        assert table.resolve("z") is not None

    def test_symbols_track_modifications(self):
        """Test that get_all_symbols returns current state"""
        manager = ScopeManager()
        table = SymbolTable(manager)

        symbols1 = table.get_all_symbols()
        assert len(symbols1) == 0

        table.add_local("x")

        symbols2 = table.get_all_symbols()
        assert len(symbols2) == 1

        # First reference should not be updated
        assert len(symbols1) == 0
