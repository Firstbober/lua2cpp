"""Tests for function signature registry

Tests the FunctionSignatureRegistry class that tracks function signatures,
parameter types, and call sites for inter-procedural type analysis.

Test Coverage:
- Function registration and retrieval
- Parameter table info tracking
- Call site recording and query
- Call graph tracking
- Registry statistics
"""

import pytest

from lua2cpp.analyzers.function_registry import (
    FunctionSignatureRegistry,
    CallSiteInfo,
    FunctionSignature
)
from lua2cpp.core.types import Type, TypeKind, TableTypeInfo


class TestFunctionSignatureRegistry:
    """Test function signature registry functionality"""

    def test_register_function(self):
        """Test registering a function signature"""
        registry = FunctionSignatureRegistry()

        signature = registry.register_function("foo", ["x", "y"], is_local=True)

        assert registry.has_function("foo")
        assert signature.name == "foo"
        assert signature.param_names == ["x", "y"]
        assert signature.is_local is True

    def test_duplicate_parameter_names_raises_error(self):
        """Test that duplicate parameter names raise error"""
        registry = FunctionSignatureRegistry()

        with pytest.raises(ValueError, match="duplicate parameter"):
            registry.register_function("foo", ["x", "x"])

    def test_register_function_no_params(self):
        """Test registering function with no parameters"""
        registry = FunctionSignatureRegistry()

        signature = registry.register_function("no_params", [])

        assert registry.has_function("no_params")
        assert signature.param_names == []

    def test_register_function_overwrites_existing(self):
        """Test that registering same function overwrites existing"""
        registry = FunctionSignatureRegistry()

        registry.register_function("foo", ["x"])
        new_signature = registry.register_function("foo", ["a", "b", "c"])

        assert registry.get_signature("foo") == new_signature
        assert registry.get_signature("foo").param_names == ["a", "b", "c"]

    def test_has_function(self):
        """Test checking if function exists in registry"""
        registry = FunctionSignatureRegistry()

        assert registry.has_function("foo") is False

        registry.register_function("foo", ["x"])
        assert registry.has_function("foo") is True

    def test_get_signature(self):
        """Test getting function signature by name"""
        registry = FunctionSignatureRegistry()

        registry.register_function("foo", ["x", "y"])

        signature = registry.get_signature("foo")
        assert signature is not None
        assert signature.name == "foo"
        assert signature.param_names == ["x", "y"]

    def test_get_signature_nonexistent(self):
        """Test getting signature for non-existent function"""
        registry = FunctionSignatureRegistry()

        signature = registry.get_signature("nonexistent")
        assert signature is None

    def test_update_param_table_info(self):
        """Test updating parameter table info"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", ["arr"])

        table_info = TableTypeInfo(is_array=True, value_type=Type(TypeKind.NUMBER))
        result = registry.update_param_table_info("foo", 0, table_info)

        assert result is True
        retrieved = registry.get_param_table_info("foo", 0)
        assert retrieved is not None
        assert retrieved.is_array is True
        assert retrieved.value_type.kind == TypeKind.NUMBER

    def test_update_param_table_info_nonexistent_function(self):
        """Test updating param info for non-existent function"""
        registry = FunctionSignatureRegistry()

        table_info = TableTypeInfo(is_array=True)
        result = registry.update_param_table_info("foo", 0, table_info)

        assert result is False

    def test_update_param_table_info_invalid_index(self):
        """Test updating param info with invalid index"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", ["x"])

        table_info = TableTypeInfo(is_array=True)

        # Negative index
        result = registry.update_param_table_info("foo", -1, table_info)
        assert result is False

        # Index out of bounds
        result = registry.update_param_table_info("foo", 5, table_info)
        assert result is False

    def test_get_param_table_info(self):
        """Test getting parameter table info"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", ["arr"])

        table_info = TableTypeInfo(is_array=True, value_type=Type(TypeKind.STRING))
        registry.update_param_table_info("foo", 0, table_info)

        retrieved = registry.get_param_table_info("foo", 0)
        assert retrieved is not None
        assert retrieved.is_array is True
        assert retrieved.value_type.kind == TypeKind.STRING

    def test_get_param_table_info_none(self):
        """Test getting param info when not set"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", ["x"])

        info = registry.get_param_table_info("foo", 0)
        assert info is None

    def test_get_param_name(self):
        """Test getting parameter name by index"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", ["a", "b", "c"])

        assert registry.get_param_name("foo", 0) == "a"
        assert registry.get_param_name("foo", 1) == "b"
        assert registry.get_param_name("foo", 2) == "c"

    def test_get_param_name_invalid_index(self):
        """Test getting param name with invalid index"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", ["x"])

        assert registry.get_param_name("foo", -1) is None
        assert registry.get_param_name("foo", 5) is None

    def test_record_call_site(self):
        """Test recording a function call site"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", ["x", "y"])

        registry.record_call_site("main", "foo", ["arg1", "arg2"], line=42)

        signature = registry.get_signature("foo")
        assert len(signature.call_sites) == 1
        call_site = signature.call_sites[0]
        assert call_site.caller_name == "main"
        assert call_site.arg_symbols == ["arg1", "arg2"]
        assert call_site.line_number == 42

    def test_record_call_site_auto_register_callee(self):
        """Test that recording call auto-registers callee if not exists"""
        registry = FunctionSignatureRegistry()

        # Record call to function that hasn't been registered yet
        registry.record_call_site("main", "unregistered", ["arg1"])

        assert registry.has_function("unregistered")
        signature = registry.get_signature("unregistered")
        assert signature.param_names == []
        assert signature.is_local is False

    def test_record_call_site_none_arg_symbols(self):
        """Test recording call site with None arg symbols"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", ["x"])

        registry.record_call_site("main", "foo", [None], line=10)

        signature = registry.get_signature("foo")
        assert len(signature.call_sites) == 1
        assert signature.call_sites[0].arg_symbols == [None]

    def test_call_graph_tracking(self):
        """Test call graph tracking"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", [])
        registry.register_function("bar", [])

        registry.record_call_site("main", "foo", [], line=1)
        registry.record_call_site("foo", "bar", [], line=5)

        callers_of_bar = registry.get_callers_of_function("bar")
        assert "foo" in callers_of_bar

        callers_of_foo = registry.get_callers_of_function("foo")
        assert "main" in callers_of_foo

    def test_get_callers_of_function(self):
        """Test getting callers of a function"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", [])

        registry.record_call_site("main", "foo", [])
        registry.record_call_site("helper", "foo", [])
        registry.record_call_site("main", "foo", [])

        callers = registry.get_callers_of_function("foo")
        assert "main" in callers
        assert "helper" in callers
        # main should not appear twice
        assert callers.count("main") == 1

    def test_get_callers_nonexistent_function(self):
        """Test getting callers for non-existent function"""
        registry = FunctionSignatureRegistry()

        callers = registry.get_callers_of_function("nonexistent")
        assert callers == []

    def test_get_call_sites_for_function(self):
        """Test getting all call sites for a function"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", ["x"])

        registry.record_call_site("caller1", "foo", ["arg1"], line=10)
        registry.record_call_site("caller2", "foo", ["arg2"], line=20)

        call_sites = registry.get_call_sites_for_function("foo")
        assert len(call_sites) == 2

    def test_get_call_sites_nonexistent_function(self):
        """Test getting call sites for non-existent function"""
        registry = FunctionSignatureRegistry()

        call_sites = registry.get_call_sites_for_function("nonexistent")
        assert call_sites == []

    def test_get_all_functions(self):
        """Test getting all registered functions"""
        registry = FunctionSignatureRegistry()

        registry.register_function("foo", [])
        registry.register_function("bar", [])
        registry.register_function("baz", [])

        functions = registry.get_all_functions()
        assert set(functions) == {"foo", "bar", "baz"}

    def test_get_functions_with_param_info(self):
        """Test getting functions with parameter type info"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", ["x"])
        registry.register_function("bar", ["y", "z"])
        registry.register_function("baz", ["w"])

        # Add param info to foo and baz
        table_info = TableTypeInfo(is_array=True, value_type=Type(TypeKind.NUMBER))
        registry.update_param_table_info("foo", 0, table_info)
        registry.update_param_table_info("baz", 0, table_info)

        functions = registry.get_functions_with_param_info()
        assert set(functions) == {"foo", "baz"}
        assert "bar" not in functions

    def test_statistics(self):
        """Test registry statistics"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", ["x"])
        registry.register_function("bar", ["a", "b"])

        # Add some type info
        table_info = TableTypeInfo(is_array=True, value_type=Type(TypeKind.NUMBER))
        registry.update_param_table_info("foo", 0, table_info)

        # Record some calls
        registry.record_call_site("main", "foo", ["arg1"])
        registry.record_call_site("main", "bar", ["arg1", "arg2"])

        stats = registry.get_statistics()
        assert stats["total_functions"] == 2
        assert stats["total_parameters"] == 3
        assert stats["typed_parameters"] == 1
        assert stats["untyped_parameters"] == 2
        assert stats["total_call_sites"] == 2

    def test_print_statistics(self):
        """Test printing formatted statistics"""
        registry = FunctionSignatureRegistry()
        registry.register_function("foo", ["x"])
        registry.register_function("bar", ["y"])

        table_info = TableTypeInfo(is_array=True)
        registry.update_param_table_info("foo", 0, table_info)

        output = registry.print_statistics()

        assert "Function Signature Registry Statistics" in output
        assert "Total functions: 2" in output
        assert "Total parameters: 2" in output
        assert "Typed parameters: 1" in output
        assert "Untyped parameters: 1" in output
        assert "Functions with typed parameters" in output
        assert "foo: params [0]" in output


class TestCallSiteInfo:
    """Test CallSiteInfo dataclass"""

    def test_get_arg_symbol(self):
        """Test getting arg symbol by index"""
        call_site = CallSiteInfo(
            caller_name="main",
            arg_symbols=["arg1", "arg2", None, "arg4"],
            line_number=42
        )

        assert call_site.get_arg_symbol(0) == "arg1"
        assert call_site.get_arg_symbol(1) == "arg2"
        assert call_site.get_arg_symbol(2) is None
        assert call_site.get_arg_symbol(3) == "arg4"

    def test_get_arg_symbol_out_of_bounds(self):
        """Test getting arg symbol with out of bounds index"""
        call_site = CallSiteInfo(
            caller_name="main",
            arg_symbols=["arg1"]
        )

        assert call_site.get_arg_symbol(-1) is None
        assert call_site.get_arg_symbol(5) is None


class TestFunctionSignature:
    """Test FunctionSignature dataclass"""

    def test_get_param_index(self):
        """Test getting parameter index by name"""
        signature = FunctionSignature(
            name="foo",
            param_names=["a", "b", "c"]
        )

        assert signature.get_param_index("a") == 0
        assert signature.get_param_index("b") == 1
        assert signature.get_param_index("c") == 2

    def test_get_param_index_not_found(self):
        """Test getting param index for non-existent param"""
        signature = FunctionSignature(
            name="foo",
            param_names=["a", "b"]
        )

        assert signature.get_param_index("z") is None

    def test_get_num_params(self):
        """Test getting number of parameters"""
        signature1 = FunctionSignature(name="foo", param_names=["a", "b"])
        assert signature1.get_num_params() == 2

        signature2 = FunctionSignature(name="bar", param_names=[])
        assert signature2.get_num_params() == 0

    def test_has_param_info(self):
        """Test checking if parameter has type info"""
        signature = FunctionSignature(name="foo", param_names=["a", "b"])

        assert signature.has_param_info(0) is False

        table_info = TableTypeInfo(is_array=True)
        signature.param_table_info[0] = table_info

        assert signature.has_param_info(0) is True
        assert signature.has_param_info(1) is False

    def test_get_all_call_sites(self):
        """Test getting all call sites"""
        signature = FunctionSignature(name="foo", param_names=["x"])

        call_site1 = CallSiteInfo(caller_name="main", arg_symbols=["arg1"])
        call_site2 = CallSiteInfo(caller_name="helper", arg_symbols=["arg2"])

        signature.call_sites.append(call_site1)
        signature.call_sites.append(call_site2)

        all_sites = signature.get_all_call_sites()

        assert len(all_sites) == 2
        assert call_site1 in all_sites
        assert call_site2 in all_sites

    def test_get_all_call_sites_returns_copy(self):
        """Test that get_all_call_sites returns a copy"""
        signature = FunctionSignature(name="foo", param_names=["x"])
        call_site = CallSiteInfo(caller_name="main", arg_symbols=["arg1"])
        signature.call_sites.append(call_site)

        all_sites = signature.get_all_call_sites()
        all_sites.clear()

        assert len(signature.call_sites) == 1
