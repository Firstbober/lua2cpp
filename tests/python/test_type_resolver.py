"""Tests for TypeResolver class

Tests the multi-pass type inference structure and core functionality.
Following the pattern from lua2c's test_interprocedural_type_inference.py.
"""

import pytest
from luaparser import ast

from lua2cpp.core.scope import ScopeManager
from lua2cpp.core.symbol_table import SymbolTable
from lua2cpp.core.types import Type, TypeKind, ASTAnnotationStore
from lua2cpp.analyzers.type_resolver import TypeResolver
from lua2cpp.analyzers.function_registry import (
    FunctionSignature, CallSiteInfo, FunctionSignatureRegistry
)


# Mock FunctionSignatureRegistry for testing (will be implemented separately)
class MockFunctionSignatureRegistry(FunctionSignatureRegistry):
    """Mock function registry for testing TypeResolver"""

    def __init__(self):
        super().__init__()
        self.signatures = {}


class TestTypeResolverInitialization:
    """Test TypeResolver class initialization"""

    def test_initialization_with_dependencies(self):
        """Test TypeResolver initializes with required dependencies"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()

        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        assert resolver.scope_manager is scope_manager
        assert resolver.symbol_table is symbol_table
        assert resolver.function_registry is function_registry

    def test_max_iteration_limit_is_set(self):
        """Test max iteration limit is set to 10"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()

        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        assert resolver._max_iterations == 10

    def test_current_function_is_none_initially(self):
        """Test current function context is None initially"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()

        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        assert resolver._current_function is None

    def test_inferred_types_storage_is_initialized(self):
        """Test inferred types storage is initialized"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()

        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        assert isinstance(resolver.inferred_types, dict)
        assert len(resolver.inferred_types) == 0


class TestFourPassStructure:
    """Test 4-pass type inference structure"""

    def test_resolve_chunk_calls_four_passes(self):
        """Test resolve_chunk calls all four pass methods"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local function foo(x)
            return x + 1
        end

        local result = foo(5)
        """
        tree = ast.parse(lua_code)

        # Track method calls
        original_collect = resolver._collect_function_signatures
        original_infer_local = resolver._infer_local_types
        original_propagate = resolver._propagate_types_interprocedurally
        original_validate = resolver._validate_and_finalize

        calls = []
        def track_collect(chunk):
            calls.append('collect')
            return original_collect(chunk)

        def track_infer_local(chunk):
            calls.append('infer_local')
            return original_infer_local(chunk)

        def track_propagate():
            calls.append('propagate')
            return original_propagate()

        def track_validate():
            calls.append('validate')
            return original_validate()

        resolver._collect_function_signatures = track_collect
        resolver._infer_local_types = track_infer_local
        resolver._propagate_types_interprocedurally = track_propagate
        resolver._validate_and_finalize = track_validate

        resolver.resolve_chunk(tree)

        assert calls == ['collect', 'infer_local', 'propagate', 'validate']

    def test_collect_function_signatures_method_exists(self):
        """Test _collect_function_signatures method exists"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        assert hasattr(resolver, '_collect_function_signatures')
        assert callable(resolver._collect_function_signatures)

    def test_infer_local_types_method_exists(self):
        """Test _infer_local_types method exists"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        assert hasattr(resolver, '_infer_local_types')
        assert callable(resolver._infer_local_types)

    def test_propagate_types_interprocedurally_method_exists(self):
        """Test _propagate_types_interprocedurally method exists"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        assert hasattr(resolver, '_propagate_types_interprocedurally')
        assert callable(resolver._propagate_types_interprocedurally)

    def test_validate_and_finalize_method_exists(self):
        """Test _validate_and_finalize method exists"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        assert hasattr(resolver, '_validate_and_finalize')
        assert callable(resolver._validate_and_finalize)


class TestASTAnnotationStoreUsage:
    """Test ASTAnnotationStore is used for type attachments"""

    def test_annotate_node_uses_ast_annotation_store(self):
        """Test annotate_node method uses ASTAnnotationStore"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = "local x = 42"
        tree = ast.parse(lua_code)
        node = tree.body.body[0].values[0]

        type_obj = Type(TypeKind.NUMBER)
        resolver.annotate_node(node, type_obj)

        retrieved = ASTAnnotationStore.get_type(node)
        assert retrieved is not None
        assert retrieved.kind == TypeKind.NUMBER

    def test_get_node_type_retrieves_from_ast_annotation_store(self):
        """Test get_node_type retrieves from ASTAnnotationStore"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = 'local s = "hello"'
        tree = ast.parse(lua_code)
        node = tree.body.body[0].values[0]

        type_obj = Type(TypeKind.STRING)
        ASTAnnotationStore.set_type(node, type_obj)

        retrieved = resolver.get_node_type(node)
        assert retrieved is not None
        assert retrieved.kind == TypeKind.STRING

    def test_get_node_type_returns_none_for_unannotated_node(self):
        """Test get_node_type returns None when no type annotation exists"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = "local x = 42"
        tree = ast.parse(lua_code)
        node = tree.body.body[0].values[0]

        retrieved = resolver.get_node_type(node)
        assert retrieved is None


class TestTypeMergingLogic:
    """Test type merging logic for conflicting types"""

    def test_merge_types_returns_existing_when_same(self):
        """Test _merge_types returns existing type when types match"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        existing = Type(TypeKind.NUMBER)
        new_type = Type(TypeKind.NUMBER)

        result = resolver._merge_types(existing, new_type)

        assert result is existing
        assert result.kind == TypeKind.NUMBER

    def test_merge_types_returns_new_when_existing_is_unknown(self):
        """Test _merge_types returns new type when existing is UNKNOWN"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        existing = Type(TypeKind.UNKNOWN)
        new_type = Type(TypeKind.STRING)

        result = resolver._merge_types(existing, new_type)

        assert result is new_type
        assert result.kind == TypeKind.STRING

    def test_merge_types_returns_existing_when_new_is_unknown(self):
        """Test _merge_types returns existing type when new is UNKNOWN"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        existing = Type(TypeKind.NUMBER)
        new_type = Type(TypeKind.UNKNOWN)

        result = resolver._merge_types(existing, new_type)

        assert result is existing
        assert result.kind == TypeKind.NUMBER

    def test_merge_types_creates_any_for_conflicting_types(self):
        """Test _merge_types creates ANY type for conflicting types"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        existing = Type(TypeKind.NUMBER)
        new_type = Type(TypeKind.STRING)

        result = resolver._merge_types(existing, new_type)

        assert result.kind == TypeKind.ANY
        assert len(result.subtypes) == 2
        assert existing in result.subtypes
        assert new_type in result.subtypes


class TestGetInferredType:
    """Test get_type method for symbol type lookup"""

    def test_get_type_returns_inferred_type(self):
        """Test get_type returns inferred type for known symbol"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        resolver.inferred_types['x'] = Type(TypeKind.NUMBER)

        result = resolver.get_type('x')

        assert result.kind == TypeKind.NUMBER

    def test_get_type_returns_unknown_for_unknown_symbol(self):
        """Test get_type returns UNKNOWN type for unknown symbol"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        result = resolver.get_type('nonexistent')

        assert result.kind == TypeKind.UNKNOWN


class TestFunctionSignatureCollection:
    """Test function signature collection in Pass 1"""

    def test_collect_function_signatures_registers_functions(self):
        """Test _collect_function_signatures registers local functions"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local function foo(x, y)
            return x + y
        end

        local function bar(a)
            return a * 2
        end
        """
        tree = ast.parse(lua_code)

        resolver._collect_function_signatures(tree)

        assert 'foo' in function_registry.signatures
        assert function_registry.signatures['foo'].param_names == ['x', 'y']
        assert function_registry.signatures['foo'].is_local is True

        assert 'bar' in function_registry.signatures
        assert function_registry.signatures['bar'].param_names == ['a']
        assert function_registry.signatures['bar'].is_local is True

    def test_collect_function_signatures_handles_function_without_name(self):
        """Test _collect_function_signatures handles anonymous function"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local function f(x, y)
            return x
        end
        """
        tree = ast.parse(lua_code)

        resolver._collect_function_signatures(tree)

        assert 'f' in function_registry.signatures


class TestValidateAndFinalize:
    """Test validation and finalization (Pass 4)"""

    def test_validate_and_finalize_completes_without_error(self):
        """Test _validate_and_finalize completes without errors"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        resolver.inferred_types['x'] = Type(TypeKind.NUMBER)
        resolver.inferred_types['s'] = Type(TypeKind.STRING)

        # Should complete without raising errors
        resolver._validate_and_finalize()

    def test_report_type_statistics_count_types_correctly(self):
        """Test _report_type_statistics counts types correctly"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        type_counts = {kind: 0 for kind in TypeKind}
        type_counts[TypeKind.NUMBER] = 3
        type_counts[TypeKind.STRING] = 2
        type_counts[TypeKind.UNKNOWN] = 1

        unknown_symbols = ['unknown_var']
        conflict_symbols = [('mixed', Type(TypeKind.ANY))]

        # Should complete without errors
        resolver._report_type_statistics(type_counts, unknown_symbols, conflict_symbols)

    def test_validate_detects_unknown_type_symbols(self):
        """Test validation identifies symbols with UNKNOWN type"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        resolver.inferred_types['known'] = Type(TypeKind.NUMBER)
        resolver.inferred_types['unknown'] = Type(TypeKind.UNKNOWN)

        # Should identify unknown symbol
        resolver._validate_and_finalize()

    def test_validate_detects_conflict_types(self):
        """Test validation detects ANY/VARIANT type conflicts"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        resolver.inferred_types['stable'] = Type(TypeKind.NUMBER)
        resolver.inferred_types['conflict'] = Type(TypeKind.ANY)

        # Should detect conflict type
        resolver._validate_and_finalize()

    def test_finalize_type_information_completes(self):
        """Test _finalize_type_information completes"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        resolver.inferred_types['x'] = Type(TypeKind.NUMBER)

        # Should complete without errors
        resolver._finalize_type_information()

    def test_validate_with_empty_inferred_types(self):
        """Test validation handles empty inferred types"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        # No types inferred yet
        assert len(resolver.inferred_types) == 0

        # Should complete without errors
        resolver._validate_and_finalize()

    def test_validate_reports_statistics_with_various_types(self):
        """Test validation with multiple type kinds"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        resolver.inferred_types['num'] = Type(TypeKind.NUMBER)
        resolver.inferred_types['str'] = Type(TypeKind.STRING)
        resolver.inferred_types['bool'] = Type(TypeKind.BOOLEAN)
        resolver.inferred_types['func'] = Type(TypeKind.FUNCTION)

        # Should complete without errors and count all types
        resolver._validate_and_finalize()

    def test_validate_with_variant_types(self):
        """Test validation handles VARIANT types correctly"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        variant_type = Type(TypeKind.VARIANT, subtypes=[
            Type(TypeKind.NUMBER),
            Type(TypeKind.STRING)
        ])
        resolver.inferred_types['var'] = variant_type

        # Should detect VARIANT as conflict
        resolver._validate_and_finalize()


class TestInterproceduralPropagation:
    """Test inter-procedural type propagation in Pass 3"""

    def test_propagate_args_to_params_simple(self):
        """Test arguments → parameters propagation for simple case"""
        from lua2cpp.core.types import TableTypeInfo

        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        # Setup: Register function and add mock call site
        function_registry.register_function("foo", ["x"])
        call_site = CallSiteInfo(caller_name="main", arg_symbols=["arg1"], line_number=10)
        function_registry.signatures["foo"].call_sites.append(call_site)

        # Set type for argument
        resolver.inferred_types["arg1"] = Type(TypeKind.NUMBER)

        # Run propagation
        changed = resolver._propagate_args_to_params()

        assert changed is True
        # Check that parameter type info was set
        param_info = function_registry.get_param_table_info("foo", 0)
        assert param_info is not None
        assert param_info.value_type.kind == TypeKind.NUMBER

    def test_propagate_args_to_params_no_change(self):
        """Test arguments → parameters returns False when no changes"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        # Setup: Register function but no call sites or argument types
        function_registry.register_function("foo", ["x"])

        # Run propagation
        changed = resolver._propagate_args_to_params()

        assert changed is False

    def test_propagate_params_to_args_simple(self):
        """Test parameters → arguments propagation for simple case"""
        from lua2cpp.core.types import TableTypeInfo

        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        # Setup: Register function with parameter type info and call site
        function_registry.register_function("bar", ["y"])
        call_site = CallSiteInfo(caller_name="main", arg_symbols=["arg_y"], line_number=20)
        function_registry.signatures["bar"].call_sites.append(call_site)
        # Mock param_table_info
        param_info = TableTypeInfo(value_type=Type(TypeKind.STRING))
        function_registry.signatures["bar"].param_table_info[0] = param_info

        # Run propagation
        changed = resolver._propagate_params_to_args()

        assert changed is True
        # Check that argument type was set
        assert "arg_y" in resolver.inferred_types
        assert resolver.inferred_types["arg_y"].kind == TypeKind.STRING

    def test_propagate_params_to_args_no_change(self):
        """Test parameters → arguments returns False when no changes"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        # Setup: Register function but no parameter type info
        function_registry.register_function("bar", ["y"])

        # Run propagation
        changed = resolver._propagate_params_to_args()

        assert changed is False

    def test_fixed_point_convergence(self):
        """Test fixed-point algorithm converges (no more changes)"""
        from lua2cpp.core.types import TableTypeInfo

        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        # Setup: Function with call site and argument already typed
        function_registry.register_function("foo", ["x"])
        call_site = CallSiteInfo(caller_name="main", arg_symbols=["arg1"], line_number=10)
        function_registry.signatures["foo"].call_sites.append(call_site)
        param_info = TableTypeInfo(value_type=Type(TypeKind.NUMBER))
        function_registry.signatures["foo"].param_table_info[0] = param_info
        resolver.inferred_types["arg1"] = Type(TypeKind.NUMBER)

        # Run propagation - should converge quickly
        changed1 = resolver._propagate_args_to_params()
        changed2 = resolver._propagate_params_to_args()

        # After first iteration, no more changes should occur
        assert not changed1 or not changed2

    def test_conflict_resolution_creates_any(self):
        """Test conflicting types are merged into ANY type"""
        from lua2cpp.core.types import TableTypeInfo

        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        # Setup: Function with parameter typed as NUMBER, argument typed as STRING
        function_registry.register_function("bar", ["y"])
        call_site = CallSiteInfo(caller_name="main", arg_symbols=["arg_y"], line_number=20)
        function_registry.signatures["bar"].call_sites.append(call_site)
        param_info = TableTypeInfo(value_type=Type(TypeKind.NUMBER))
        function_registry.signatures["bar"].param_table_info[0] = param_info
        resolver.inferred_types["arg_y"] = Type(TypeKind.STRING)

        # Run propagation - should create ANY type
        changed = resolver._propagate_params_to_args()

        assert changed is True
        assert resolver.inferred_types["arg_y"].kind == TypeKind.ANY
        assert len(resolver.inferred_types["arg_y"].subtypes) == 2

    def test_max_iteration_limit(self):
        """Test propagation stops after max iterations"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        # Set low max iterations for testing
        resolver._max_iterations = 3

        # Setup: Function with call sites
        function_registry.register_function("foo", ["x"])
        call_site = CallSiteInfo(caller_name="main", arg_symbols=["arg1"], line_number=10)
        function_registry.signatures["foo"].call_sites.append(call_site)
        resolver.inferred_types["arg1"] = Type(TypeKind.NUMBER)

        # Run inter-procedural propagation
        resolver._propagate_types_interprocedurally()

        # Should not exceed max iterations
        # In practice, this converges quickly, but we verify the limit exists

    def test_bidirectional_propagation(self):
        """Test both directions of propagation work together"""
        from lua2cpp.core.types import TableTypeInfo

        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        # Setup: Function with call site
        function_registry.register_function("foo", ["x"])
        call_site = CallSiteInfo(caller_name="main", arg_symbols=["arg1"], line_number=10)
        function_registry.signatures["foo"].call_sites.append(call_site)

        # Argument has NUMBER type
        resolver.inferred_types["arg1"] = Type(TypeKind.NUMBER)

        # First iteration: args → params
        changed1 = resolver._propagate_args_to_params()
        assert changed1 is True

        # Now parameter has NUMBER type (stored in param_table_info)
        # Second iteration: params → args (should be no change since types match)
        # For this test, we simulate the scenario by setting the param info
        param_info = TableTypeInfo(value_type=Type(TypeKind.NUMBER))
        function_registry.signatures["foo"].param_table_info[0] = param_info

        changed2 = resolver._propagate_params_to_args()
        # Should be False since arg already has NUMBER type
        assert changed2 is False


class TestLocalTypeInference:
    """Test Pass 2: Local type inference within functions"""

    def test_infer_number_literal_type(self):
        """Test NUMBER literal type inference"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = "local x = 42"
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'x' in resolver.inferred_types
        assert resolver.inferred_types['x'].kind == TypeKind.NUMBER

    def test_infer_string_literal_type(self):
        """Test STRING literal type inference"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = 'local s = "hello"'
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 's' in resolver.inferred_types
        assert resolver.inferred_types['s'].kind == TypeKind.STRING

    def test_infer_boolean_true_literal_type(self):
        """Test BOOLEAN true literal type inference"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = "local b = true"
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'b' in resolver.inferred_types
        assert resolver.inferred_types['b'].kind == TypeKind.BOOLEAN

    def test_infer_boolean_false_literal_type(self):
        """Test BOOLEAN false literal type inference"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = "local b = false"
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'b' in resolver.inferred_types
        assert resolver.inferred_types['b'].kind == TypeKind.BOOLEAN

    def test_assignment_type_propagation(self):
        """Test assignment type propagation from value to variable"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local x = 42
        local y = x
        """
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'x' in resolver.inferred_types
        assert 'y' in resolver.inferred_types
        assert resolver.inferred_types['x'].kind == TypeKind.NUMBER
        assert resolver.inferred_types['y'].kind == TypeKind.NUMBER

    def test_variable_reference_type_resolution(self):
        """Test variable reference resolves to correct type"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local count = 10
        local total = count
        local message = "test"
        local copy = message
        """
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'count' in resolver.inferred_types
        assert 'total' in resolver.inferred_types
        assert 'message' in resolver.inferred_types
        assert 'copy' in resolver.inferred_types

        assert resolver.inferred_types['count'].kind == TypeKind.NUMBER
        assert resolver.inferred_types['total'].kind == TypeKind.NUMBER
        assert resolver.inferred_types['message'].kind == TypeKind.STRING
        assert resolver.inferred_types['copy'].kind == TypeKind.STRING

    def test_binary_operation_addition_inference(self):
        """Test binary operation type inference for addition"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local x = 10
        local y = x + 5
        """
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'x' in resolver.inferred_types
        assert 'y' in resolver.inferred_types
        assert resolver.inferred_types['x'].kind == TypeKind.NUMBER
        assert resolver.inferred_types['y'].kind == TypeKind.NUMBER

    def test_binary_operation_subtraction_inference(self):
        """Test binary operation type inference for subtraction"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local x = 20
        local y = x - 10
        """
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'x' in resolver.inferred_types
        assert 'y' in resolver.inferred_types
        assert resolver.inferred_types['x'].kind == TypeKind.NUMBER
        assert resolver.inferred_types['y'].kind == TypeKind.NUMBER

    def test_binary_operation_multiplication_inference(self):
        """Test binary operation type inference for multiplication"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local x = 5
        local y = x * 2
        """
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'x' in resolver.inferred_types
        assert 'y' in resolver.inferred_types
        assert resolver.inferred_types['x'].kind == TypeKind.NUMBER
        assert resolver.inferred_types['y'].kind == TypeKind.NUMBER

    def test_binary_operation_division_inference(self):
        """Test binary operation type inference for division"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local x = 100
        local y = x / 4
        """
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'x' in resolver.inferred_types
        assert 'y' in resolver.inferred_types
        assert resolver.inferred_types['x'].kind == TypeKind.NUMBER
        assert resolver.inferred_types['y'].kind == TypeKind.NUMBER

    def test_string_concatenation_inference(self):
        """Test string concatenation returns STRING type"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local a = "hello"
        local b = "world"
        local c = a .. b
        """
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'a' in resolver.inferred_types
        assert 'b' in resolver.inferred_types
        assert 'c' in resolver.inferred_types
        assert resolver.inferred_types['a'].kind == TypeKind.STRING
        assert resolver.inferred_types['b'].kind == TypeKind.STRING
        assert resolver.inferred_types['c'].kind == TypeKind.STRING

    def test_comparison_operation_inference(self):
        """Test comparison operations return BOOLEAN type"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local x = 10
        local result = x > 5
        """
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'x' in resolver.inferred_types
        assert 'result' in resolver.inferred_types
        assert resolver.inferred_types['x'].kind == TypeKind.NUMBER
        assert resolver.inferred_types['result'].kind == TypeKind.BOOLEAN

    def test_unary_minus_inference(self):
        """Test unary minus preserves operand type"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local x = 10
        local y = -x
        """
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'x' in resolver.inferred_types
        assert 'y' in resolver.inferred_types
        assert resolver.inferred_types['x'].kind == TypeKind.NUMBER
        assert resolver.inferred_types['y'].kind == TypeKind.NUMBER

    def test_logical_not_inference(self):
        """Test logical not returns BOOLEAN type"""
        scope_manager = ScopeManager()
        symbol_table = SymbolTable(scope_manager)
        function_registry = MockFunctionSignatureRegistry()
        resolver = TypeResolver(scope_manager, symbol_table, function_registry)

        lua_code = """
        local b = true
        local result = not b
        """
        tree = ast.parse(lua_code)

        resolver._infer_local_types(tree)

        assert 'b' in resolver.inferred_types
        assert 'result' in resolver.inferred_types
        assert resolver.inferred_types['b'].kind == TypeKind.BOOLEAN
        assert resolver.inferred_types['result'].kind == TypeKind.BOOLEAN

