"""Tests for inter-procedural type inference

Tests the multi-pass type inference system that propagates
types across function boundaries using bidirectional analysis.

Test Coverage:
- Argument to parameter type propagation
- Parameter to argument type propagation
- Empty tables inheriting types from function parameters
- Multiple call sites with variant types
- Circular dependencies
"""

import pytest
import tempfile
from pathlib import Path
from luaparser import ast

from lua2c.core.context import TranslationContext
from lua2c.analyzers.type_inference import TypeInference
from lua2c.analyzers.function_registry import FunctionSignatureRegistry
from lua2c.core.type_system import Type, TypeKind, TableTypeInfo


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


class TestInterproceduralTypePropagation:
    """Test inter-procedural type propagation system"""

    def _create_test_context(self, lua_code: str) -> TranslationContext:
        """Helper to create test context and parse code"""
        tree = ast.parse(lua_code)
        context = TranslationContext(Path.cwd(), "")
        return context, tree

    def test_empty_table_gets_param_type(self):
        """Empty table should inherit type from function parameter"""
        lua_code = """
        local function foo(x)
            return x[1] + 1
        end

        local y = {}
        local result = foo(y)
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        # Check that y was inferred as array with NUMBER elements
        assert "y" in inferencer.table_info
        table_info = inferencer.table_info["y"]
        assert table_info.is_array is True
        assert table_info.value_type is not None
        assert table_info.value_type.kind == TypeKind.NUMBER

    def test_spectral_norm_case(self):
        """Test the specific spectral-norm.lua case"""
        lua_code = """
        local function Av(x, y, N)
            for i=1,N do
                local a = 0
                for j=1,N do
                    a = a + x[j]
                end
                y[i] = a
            end
        end

        local u = {}
        local v = {}
        local N = 100

        Av(u, v, N)
        Av(v, u, N)
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        # u and v should be typed as NUMBER arrays (t is not passed to any function)
        for var_name in ["u", "v"]:
            assert var_name in inferencer.table_info, f"{var_name} should have table info"
            table_info = inferencer.table_info[var_name]
            assert table_info.is_array is True, f"{var_name} should be array"
            assert table_info.value_type is not None, f"{var_name} should have element type"
            assert table_info.value_type.kind == TypeKind.NUMBER, f"{var_name} should be NUMBER array"

    def test_bidirectional_propagation(self):
        """Test both directions of type propagation"""
        lua_code = """
        local function process(arr)
            arr[1] = arr[1] + 1
        end

        local data = {}
        process(data)
        local value = data[1]
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        # data should be typed as NUMBER array
        assert "data" in inferencer.table_info
        table_info = inferencer.table_info["data"]
        assert table_info.is_array is True
        assert table_info.value_type is not None

    def test_multiple_call_sites_same_type(self):
        """Multiple call sites with same type should not create variant"""
        lua_code = """
        local function foo(x)
            return x[1]
        end

        local a = {1, 2}
        local b = {3, 4}
        foo(a)
        foo(b)
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        # Check parameter x has NUMBER type, not VARIANT
        param_info = inferencer.func_registry.get_param_table_info("foo", 0)
        assert param_info is not None
        assert param_info.value_type is not None
        # Should be NUMBER, not VARIANT (both call sites use NUMBER)
        assert param_info.value_type.kind == TypeKind.NUMBER

    def test_multiple_call_sites_different_types(self):
        """Multiple call sites with different types should create VARIANT"""
        lua_code = """
        local function foo(x)
            return x[1]
        end

        local a = {1, 2}
        local b = {"hello", "world"}
        foo(a)
        foo(b)
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        # Parameter x should have VARIANT type
        param_info = inferencer.func_registry.get_param_table_info("foo", 0)
        assert param_info is not None
        assert param_info.value_type is not None
        # Should be VARIANT combining NUMBER and STRING
        assert param_info.value_type.kind == TypeKind.VARIANT

        # Check subtypes
        subtypes = param_info.value_type.subtypes
        subtype_kinds = {t.kind for t in subtypes}
        assert TypeKind.NUMBER in subtype_kinds
        assert TypeKind.STRING in subtype_kinds

    def test_call_site_logging(self):
        """Test that call sites are properly logged"""
        lua_code = """
        local function bar(x) end

        local function foo()
            bar({1, 2})
            bar({"a", "b"})
        end

        foo()
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        # Check call sites for bar
        signature = inferencer.func_registry.get_signature("bar")
        assert signature is not None
        assert len(signature.call_sites) == 2

    def test_propagation_convergence(self):
        """Test that propagation converges within max iterations"""
        lua_code = """
        local function f1(x) return x end
        local function f2(y) return y end

        local a = {}
        f1(f2(a))
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        # Should converge without warnings
        stats = inferencer.propagation_logger.get_statistics()
        assert stats["iterations"] <= inferencer._max_iterations

    def test_empty_function_no_propagation(self):
        """Empty function should not cause propagation issues"""
        lua_code = """
        local function empty() end

        local x = {}
        empty(x)
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        # x should not have array type (empty function doesn't use it)
        assert "x" in inferencer.table_info
        table_info = inferencer.table_info["x"]
        # Empty table - array decision depends on finalization
        # but no element type should be inferred
        assert table_info.value_type is None

    def test_nested_function_calls(self):
        """Test type propagation through nested function calls"""
        lua_code = """
        local function inner(x)
            return x[1]
        end

        local function outer(y)
            return inner(y)
        end

        local data = {1, 2, 3}
        local result = outer(data)
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        # data should be typed as NUMBER array
        assert "data" in inferencer.table_info
        table_info = inferencer.table_info["data"]
        assert table_info.is_array is True
        assert table_info.value_type is not None
        assert table_info.value_type.kind == TypeKind.NUMBER


class TestPropagationLogger:
    """Test propagation logger functionality"""

    def test_log_propagation(self):
        """Test logging propagation events"""
        from lua2c.analyzers.propagation_logger import (
            PropagationLogger, PropagationDirection
        )

        logger = PropagationLogger(verbose=True)
        logger.start_iteration(1)

        table_info = TableTypeInfo(is_array=True, value_type=Type(TypeKind.NUMBER))
        logger.log_propagation(
            from_symbol="arg",
            to_symbol="param",
            table_info=table_info,
            direction=PropagationDirection.ARGS_TO_PARAMS
        )

        assert len(logger.propagations) == 1
        assert logger.propagations[0].from_symbol == "arg"
        assert logger.propagations[0].to_symbol == "param"

    def test_log_conflict(self):
        """Test logging type conflicts"""
        from lua2c.analyzers.propagation_logger import PropagationLogger

        logger = PropagationLogger()
        logger.log_conflict(
            symbol="x",
            existing_type=Type(TypeKind.NUMBER),
            new_type=Type(TypeKind.STRING),
            result_type=Type(TypeKind.VARIANT, subtypes=[
                Type(TypeKind.NUMBER), Type(TypeKind.STRING)
            ])
        )

        assert len(logger.conflicts) == 1
        assert len(logger.warnings) == 1
        assert "Type conflict for 'x'" in logger.warnings[0]

    def test_statistics(self):
        """Test logger statistics"""
        from lua2c.analyzers.propagation_logger import (
            PropagationLogger, PropagationDirection
        )

        logger = PropagationLogger()
        logger.start_iteration(1)

        table_info = TableTypeInfo(is_array=True, value_type=Type(TypeKind.NUMBER))

        logger.log_propagation("arg1", "param1", table_info,
                            PropagationDirection.ARGS_TO_PARAMS)
        logger.log_propagation("param1", "arg1", table_info,
                            PropagationDirection.PARAMS_TO_ARGS)

        stats = logger.get_statistics()
        assert stats["total_propagations"] == 2
        assert stats["args_to_params"] == 1
        assert stats["params_to_args"] == 1
        assert stats["iterations"] == 1

    def test_print_summary(self):
        """Test summary printing"""
        from lua2c.analyzers.propagation_logger import PropagationLogger

        logger = PropagationLogger(verbose=False)
        logger.log_warning("Test warning")

        summary = logger.print_summary()
        assert "Test warning" in summary
        assert "Type Propagation Summary" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
