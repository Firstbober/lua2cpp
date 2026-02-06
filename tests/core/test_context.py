"""Tests for translation context"""

import pytest
from pathlib import Path
from lua2c.core.context import TranslationContext


class TestTranslationContext:
    """Test suite for TranslationContext"""

    def test_initialization(self):
        """Test context initialization"""
        context = TranslationContext(Path("/project"), "module/test")
        assert context.root_dir == Path("/project")
        assert context.module_path == "module/test"
        assert context.current_function_depth == 0
        assert not context.in_function()

    def test_enter_exit_function(self):
        """Test entering and exiting function scopes"""
        context = TranslationContext(Path("/project"), "test")

        context.enter_function()
        assert context.current_function_depth == 1
        assert context.in_function()

        context.exit_function()
        assert context.current_function_depth == 0
        assert not context.in_function()

    def test_enter_exit_function_nested(self):
        """Test nested function scopes"""
        context = TranslationContext(Path("/project"), "test")

        context.enter_function()
        assert context.current_function_depth == 1

        context.enter_function()
        assert context.current_function_depth == 2

        context.exit_function()
        assert context.current_function_depth == 1

        context.exit_function()
        assert context.current_function_depth == 0

    def test_exit_function_when_not_in_function(self):
        """Test exiting function when not in one raises error"""
        context = TranslationContext(Path("/project"), "test")
        with pytest.raises(RuntimeError):
            context.exit_function()

    def test_enter_exit_block(self):
        """Test entering and exiting block scopes"""
        context = TranslationContext(Path("/project"), "test")

        context.enter_block()
        depth = context.get_scope_manager().current_depth()
        assert depth == 1

        context.exit_block()
        depth = context.get_scope_manager().current_depth()
        assert depth == 0

    def test_string_literal_add(self):
        """Test adding string literals"""
        context = TranslationContext(Path("/project"), "test")

        idx1 = context.add_string_literal("hello")
        idx2 = context.add_string_literal("world")
        idx3 = context.add_string_literal("hello")  # Duplicate

        assert idx1 == 0
        assert idx2 == 1
        assert idx3 == 0  # Same as idx1

    def test_string_literal_get(self):
        """Test getting string literals"""
        context = TranslationContext(Path("/project"), "test")

        context.add_string_literal("test")
        assert context.get_string_literal(0) == "test"

    def test_define_local(self):
        """Test defining local variable"""
        context = TranslationContext(Path("/project"), "test")

        context.define_local("x")
        assert context.is_local("x") is True
        assert context.is_global("x") is False
        assert context.resolve_symbol("x") is not None

    def test_define_global(self):
        """Test defining global variable"""
        context = TranslationContext(Path("/project"), "test")

        context.define_global("g")
        assert context.is_global("g") is True
        assert context.is_local("g") is False
        assert context.resolve_symbol("g") is not None

    def test_define_function_local(self):
        """Test defining local function"""
        context = TranslationContext(Path("/project"), "test")

        context.enter_function()
        context.define_function("foo", is_global=False)
        symbol = context.resolve_symbol("foo")

        assert symbol is not None
        assert symbol.is_function is True
        assert symbol.is_global is False

    def test_define_function_global(self):
        """Test defining global function"""
        context = TranslationContext(Path("/project"), "test")

        context.define_function("bar", is_global=True)
        symbol = context.resolve_symbol("bar")

        assert symbol is not None
        assert symbol.is_function is True
        assert symbol.is_global is True

    def test_define_parameter(self):
        """Test defining function parameter"""
        context = TranslationContext(Path("/project"), "test")

        context.enter_function()
        context.define_parameter("arg", 0)
        symbol = context.resolve_symbol("arg")

        assert symbol is not None
        assert symbol.param_index == 0
        assert symbol.is_function is True

    def test_resolve_symbol_not_found(self):
        """Test resolving non-existent symbol"""
        context = TranslationContext(Path("/project"), "test")
        assert context.resolve_symbol("nonexistent") is None

    def test_get_all_symbols(self):
        """Test getting all symbols"""
        context = TranslationContext(Path("/project"), "test")

        context.define_local("x")
        context.define_global("g")
        context.enter_function()
        context.define_parameter("arg", 0)

        symbols = context.get_all_symbols()
        assert len(symbols) == 3

    def test_get_string_pool(self):
        """Test getting string pool"""
        context = TranslationContext(Path("/project"), "test")
        pool = context.get_string_pool()
        assert pool is not None
        assert pool.size() == 0

    def test_get_scope_manager(self):
        """Test getting scope manager"""
        context = TranslationContext(Path("/project"), "test")
        manager = context.get_scope_manager()
        assert manager is not None
        assert manager.current_depth() == 0

    def test_get_symbol_table(self):
        """Test getting symbol table"""
        context = TranslationContext(Path("/project"), "test")
        table = context.get_symbol_table()
        assert table is not None
        assert len(table.get_all_symbols()) == 0

    def test_scope_isolation_between_functions(self):
        """Test that function scopes are isolated"""
        context = TranslationContext(Path("/project"), "test")

        context.enter_function()
        context.define_local("x")
        assert context.resolve_symbol("x") is not None

        context.exit_function()

        context.enter_function()
        assert context.resolve_symbol("x") is None
        context.define_local("y")
        assert context.resolve_symbol("y") is not None

    def test_nested_blocks_inside_function(self):
        """Test nested blocks within function scope"""
        context = TranslationContext(Path("/project"), "test")

        context.enter_function()
        context.define_local("x")

        context.enter_block()
        context.define_local("y")
        assert context.resolve_symbol("x") is not None
        assert context.resolve_symbol("y") is not None

        context.exit_block()
        assert context.resolve_symbol("x") is not None
        assert context.resolve_symbol("y") is None

        context.exit_function()
