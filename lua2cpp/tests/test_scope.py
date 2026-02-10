"""Tests for scope management"""

import pytest
from lua2cpp.core.scope import Scope, ScopeManager, Symbol


class TestSymbol:
    """Test suite for Symbol"""

    def test_symbol_creation(self):
        """Test basic symbol creation"""
        symbol = Symbol("x", 123)
        assert symbol.name == "x"
        assert symbol.scope_id == 123
        assert symbol.is_global is False
        assert symbol.is_function is False
        assert symbol.param_index == -1

    def test_symbol_with_flags(self):
        """Test symbol with various flags"""
        symbol = Symbol("foo", 456, is_global=True, is_function=True, param_index=2)
        assert symbol.name == "foo"
        assert symbol.scope_id == 456
        assert symbol.is_global is True
        assert symbol.is_function is True
        assert symbol.param_index == 2

    def test_symbol_repr(self):
        """Test symbol representation"""
        symbol = Symbol("test", 789, is_global=True)
        repr_str = repr(symbol)
        assert "name='test'" in repr_str
        assert "scope_id=789" in repr_str
        assert "is_global=True" in repr_str


class TestScope:
    """Test suite for Scope"""

    def test_global_scope_creation(self):
        """Test creating global scope"""
        scope = Scope()
        assert scope.parent is None
        assert scope.is_global() is True
        assert scope.get_depth() == 0

    def test_child_scope_creation(self):
        """Test creating child scope"""
        parent = Scope()
        child = Scope(parent)
        assert child.parent is parent
        assert child.is_global() is False
        assert child.get_depth() == 1

    def test_define_symbol(self):
        """Test defining a symbol"""
        scope = Scope()
        symbol = scope.define("x")
        assert symbol.name == "x"
        assert scope.has("x") is True

    def test_define_duplicate_raises(self):
        """Test that defining duplicate raises error"""
        scope = Scope()
        scope.define("x")
        with pytest.raises(NameError):
            scope.define("x")

    def test_lookup_found(self):
        """Test looking up existing symbol"""
        scope = Scope()
        symbol = scope.define("test")
        result = scope.lookup("test")
        assert result is symbol

    def test_lookup_not_found(self):
        """Test looking up non-existent symbol"""
        scope = Scope()
        result = scope.lookup("nonexistent")
        assert result is None

    def test_lookup_parent_scope(self):
        """Test lookup finds symbol in parent scope"""
        parent = Scope()
        child = Scope(parent)
        parent.define("x")
        result = child.lookup("x")
        assert result is not None
        assert result.name == "x"

    def test_lookup_local_only(self):
        """Test local lookup doesn't check parent"""
        parent = Scope()
        child = Scope(parent)
        parent.define("x")
        result = child.lookup_local("x")
        assert result is None

    def test_shadowing(self):
        """Test child scope shadows parent symbol"""
        parent = Scope()
        child = Scope(parent)
        parent_symbol = parent.define("x")
        child_symbol = child.define("x")
        assert parent_symbol.scope_id != child_symbol.scope_id
        assert child.lookup("x") is child_symbol

    def test_get_depth_nested(self):
        """Test depth calculation for nested scopes"""
        root = Scope()
        child1 = Scope(root)
        child2 = Scope(child1)
        child3 = Scope(child2)
        assert root.get_depth() == 0
        assert child1.get_depth() == 1
        assert child2.get_depth() == 2
        assert child3.get_depth() == 3


class TestScopeManager:
    """Test suite for ScopeManager"""

    def test_initial_state(self):
        """Test initial state has global scope"""
        manager = ScopeManager()
        assert manager.current_depth() == 0
        assert manager.in_function_scope() is False
        assert manager.current_scope.is_global() is True

    def test_push_scope(self):
        """Test pushing a new scope"""
        manager = ScopeManager()
        manager.push_scope()
        assert manager.current_depth() == 1
        assert manager.in_function_scope() is True
        assert manager.current_scope.is_global() is False

    def test_pop_scope(self):
        """Test popping a scope"""
        manager = ScopeManager()
        manager.push_scope()
        manager.pop_scope()
        assert manager.current_depth() == 0
        assert manager.current_scope.is_global() is True

    def test_pop_global_scope_raises(self):
        """Test that popping global scope raises error"""
        manager = ScopeManager()
        with pytest.raises(RuntimeError):
            manager.pop_scope()

    def test_define_local(self):
        """Test defining local variable"""
        manager = ScopeManager()
        symbol = manager.define_local("x")
        assert symbol.name == "x"
        assert symbol.is_global is False

    def test_define_global(self):
        """Test defining global variable"""
        manager = ScopeManager()
        manager.push_scope()
        symbol = manager.define_global("g")
        assert symbol.name == "g"
        assert symbol.is_global is True
        assert manager.global_scope.has("g")

    def test_define_function_param(self):
        """Test defining function parameter"""
        manager = ScopeManager()
        symbol = manager.define_function_param("arg", 0)
        assert symbol.name == "arg"
        assert symbol.is_function is True
        assert symbol.param_index == 0

    def test_lookup_found_local(self):
        """Test lookup finds local variable"""
        manager = ScopeManager()
        manager.define_local("x")
        assert manager.lookup("x") is not None

    def test_lookup_found_in_parent(self):
        """Test lookup finds variable in parent scope"""
        manager = ScopeManager()
        manager.define_local("x")
        manager.push_scope()
        assert manager.lookup("x") is not None

    def test_is_local(self):
        """Test is_local check"""
        manager = ScopeManager()
        manager.push_scope()
        manager.define_local("x")
        assert manager.is_local("x") is True
        assert manager.is_global("x") is False

    def test_is_global(self):
        """Test is_global check"""
        manager = ScopeManager()
        manager.define_global("g")
        assert manager.is_global("g") is True
        assert manager.is_local("g") is False

    def test_nested_scopes(self):
        """Test multiple nested scopes"""
        manager = ScopeManager()
        assert manager.current_depth() == 0

        manager.push_scope()
        assert manager.current_depth() == 1
        manager.define_local("x")

        manager.push_scope()
        assert manager.current_depth() == 2
        manager.define_local("y")

        manager.push_scope()
        assert manager.current_depth() == 3

        # All symbols should be accessible
        assert manager.lookup("x") is not None
        assert manager.lookup("y") is not None

        manager.pop_scope()
        assert manager.current_depth() == 2

        manager.pop_scope()
        assert manager.current_depth() == 1

        manager.pop_scope()
        assert manager.current_depth() == 0

    def test_shadowing_in_manager(self):
        """Test shadowing behavior in manager"""
        manager = ScopeManager()
        manager.define_local("x")
        outer_symbol = manager.lookup("x")

        manager.push_scope()
        manager.define_local("x")
        inner_symbol = manager.lookup("x")

        assert outer_symbol is not inner_symbol
        assert manager.lookup("x") is inner_symbol
