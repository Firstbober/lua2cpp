"""Integration tests for Lua file parsing and type inference

Tests all 20 Lua test files from tests/cpp/lua/ to ensure:
- All files parse successfully with luaparser
- Type inference completes without errors using TypeResolver
- Inferred types are correct for representative files
"""

import os
import pytest
from pathlib import Path
from luaparser import ast

from lua2cpp.core.scope import ScopeManager
from lua2cpp.core.symbol_table import SymbolTable
from lua2cpp.core.types import Type, TypeKind
from lua2cpp.analyzers.function_registry import FunctionSignatureRegistry
from lua2cpp.analyzers.type_resolver import TypeResolver


LUA_TEST_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "cpp" / "lua"

LUA_TEST_FILES = [
    "ack.lua",
    "binary-trees.lua",
    "comparisons.lua",
    "fannkuch-redux.lua",
    "fasta.lua",
    "fixpoint-fact.lua",
    "heapsort.lua",
    "k-nucleotide.lua",
    "mandel.lua",
    "n-body.lua",
    "qt.lua",
    "queen.lua",
    "regex-dna.lua",
    "scimark.lua",
    "sieve.lua",
    "simple.lua",
    "spectral-norm.lua",
    "test_array.lua",
    "test_assign.lua",
    "test_func.lua",
]


def create_type_resolver() -> TypeResolver:
    """Create a TypeResolver instance with required dependencies

    Returns:
        TypeResolver instance initialized with ScopeManager, SymbolTable, and FunctionSignatureRegistry
    """
    scope_manager = ScopeManager()
    symbol_table = SymbolTable(scope_manager)
    function_registry = FunctionSignatureRegistry()
    return TypeResolver(scope_manager, symbol_table, function_registry)


@pytest.mark.integration
class TestLuaFilesIntegration:
    """Integration tests for all 20 Lua test files"""

    @pytest.mark.parametrize("filename", LUA_TEST_FILES)
    def test_lua_file_parses_successfully(self, filename):
        """Test that all 20 Lua files parse successfully

        Args:
            filename: Name of the Lua file to test
        """
        filepath = LUA_TEST_DIR / filename
        assert filepath.exists(), f"Lua test file not found: {filepath}"

        with open(filepath, 'r', encoding='utf-8') as f:
            lua_code = f.read()

        chunk = ast.parse(lua_code)
        assert chunk is not None, f"Failed to parse {filename}"
        assert hasattr(chunk, 'body'), f"Chunk has no body: {filename}"

    @pytest.mark.parametrize("filename", LUA_TEST_FILES)
    def test_lua_file_type_inference_completes(self, filename):
        """Test that type inference completes without errors for all 20 files

        Args:
            filename: Name of the Lua file to test
        """
        filepath = LUA_TEST_DIR / filename
        assert filepath.exists(), f"Lua test file not found: {filepath}"

        with open(filepath, 'r', encoding='utf-8') as f:
            lua_code = f.read()

        chunk = ast.parse(lua_code)
        type_resolver = create_type_resolver()
        type_resolver.resolve_chunk(chunk)

        assert isinstance(type_resolver.inferred_types, dict)
        # Empty inferred_types is acceptable (some files have no types to infer)

    @pytest.mark.parametrize("filename", LUA_TEST_FILES)
    def test_lua_file_has_valid_ast_structure(self, filename):
        """Test that all parsed files have valid AST structure

        Args:
            filename: Name of the Lua file to test
        """
        filepath = LUA_TEST_DIR / filename
        assert filepath.exists(), f"Lua test file not found: {filepath}"

        with open(filepath, 'r', encoding='utf-8') as f:
            lua_code = f.read()

        chunk = ast.parse(lua_code)
        assert chunk is not None
        assert hasattr(chunk, 'body')
        assert hasattr(chunk.body, 'body')

        from luaparser.astnodes import Block
        assert isinstance(chunk.body, Block), f"Chunk.body is not a Block in {filename}"

    def test_simple_lua_type_inference(self):
        """Test type inference correctness for simple.lua

        simple.lua:
            local function add(a, b)
                return a + b
            end

            local x = add(5, 7)
            print(x)

        Expected types:
            - add: FUNCTION
            - x: UNKNOWN (function call return types not inferred yet)
        """
        filepath = LUA_TEST_DIR / "simple.lua"
        with open(filepath, 'r', encoding='utf-8') as f:
            lua_code = f.read()

        chunk = ast.parse(lua_code)
        type_resolver = create_type_resolver()
        type_resolver.resolve_chunk(chunk)

        add_type = type_resolver.get_type("add")
        assert add_type.kind == TypeKind.FUNCTION, f"add should be FUNCTION, got {add_type.kind}"

        x_type = type_resolver.get_type("x")
        # x is UNKNOWN because function call return types are not inferred
        assert x_type.kind == TypeKind.UNKNOWN, f"x should be UNKNOWN, got {x_type.kind}"

    def test_test_func_lua_type_inference(self):
        """Test type inference correctness for test_func.lua

        test_func.lua:
            local function A(i, j)
              local ij = i + j - 1
              return 1.0 / (ij * (ij - 1) * 0.5 + i)
            end

        Expected types:
            - A: FUNCTION
            - ij: UNKNOWN (parameters are UNKNOWN in Lua's dynamic typing)
        """
        filepath = LUA_TEST_DIR / "test_func.lua"
        with open(filepath, 'r', encoding='utf-8') as f:
            lua_code = f.read()

        chunk = ast.parse(lua_code)
        type_resolver = create_type_resolver()
        type_resolver.resolve_chunk(chunk)

        a_type = type_resolver.get_type("A")
        assert a_type.kind == TypeKind.FUNCTION, f"A should be FUNCTION, got {a_type.kind}"

        ij_type = type_resolver.get_type("ij")
        # ij is UNKNOWN because function parameters are UNKNOWN (dynamic typing)
        assert ij_type.kind == TypeKind.UNKNOWN, f"ij should be UNKNOWN, got {ij_type.kind}"

    def test_test_array_lua_type_inference(self):
        """Test type inference correctness for test_array.lua

        test_array.lua:
            local arr = {1, 2, 3}
            arr[1] = 100
            print(arr[1])

        Expected types:
            - arr: TABLE (array-like)
        """
        filepath = LUA_TEST_DIR / "test_array.lua"
        with open(filepath, 'r', encoding='utf-8') as f:
            lua_code = f.read()

        chunk = ast.parse(lua_code)
        type_resolver = create_type_resolver()
        type_resolver.resolve_chunk(chunk)

        arr_type = type_resolver.get_type("arr")
        assert arr_type.kind == TypeKind.TABLE, f"arr should be TABLE, got {arr_type.kind}"

    def test_spectral_norm_lua_type_inference(self):
        """Test type inference correctness for spectral-norm.lua

        This is a more complex file with multiple functions and arrays.
        Key functions:
            - A(i, j): FUNCTION
            - Av(x, y, N): FUNCTION
            - Atv(x, y, N): FUNCTION
            - AtAv(x, y, t, N): FUNCTION
            - u, v, t: TABLE (arrays)
        """
        filepath = LUA_TEST_DIR / "spectral-norm.lua"
        with open(filepath, 'r', encoding='utf-8') as f:
            lua_code = f.read()

        chunk = ast.parse(lua_code)
        type_resolver = create_type_resolver()
        type_resolver.resolve_chunk(chunk)

        functions = ["A", "Av", "Atv", "AtAv"]
        for func_name in functions:
            func_type = type_resolver.get_type(func_name)
            assert func_type.kind == TypeKind.FUNCTION, \
                f"{func_name} should be FUNCTION, got {func_type.kind}"

        arrays = ["u", "v", "t", "N"]
        for arr_name in arrays:
            arr_type = type_resolver.get_type(arr_name)
            # N is a NUMBER, u/v/t are TABLEs
            if arr_name == "N":
                assert arr_type.kind == TypeKind.NUMBER, \
                    f"{arr_name} should be NUMBER, got {arr_type.kind}"
            else:
                assert arr_type.kind == TypeKind.TABLE, \
                    f"{arr_name} should be TABLE, got {arr_type.kind}"

    def test_all_files_parse_count(self):
        """Verify that all 20 Lua files are tested"""
        assert len(LUA_TEST_FILES) == 20, f"Expected 20 Lua files, got {len(LUA_TEST_FILES)}"

    def test_type_resolver_has_valid_dependencies(self):
        """Test that TypeResolver can be created with valid dependencies"""
        type_resolver = create_type_resolver()
        assert type_resolver is not None
        assert hasattr(type_resolver, 'scope_manager')
        assert hasattr(type_resolver, 'symbol_table')
        assert hasattr(type_resolver, 'function_registry')
        assert hasattr(type_resolver, 'inferred_types')

    def test_function_registry_tracks_functions(self):
        """Test that function registry correctly tracks function signatures"""
        filepath = LUA_TEST_DIR / "simple.lua"
        with open(filepath, 'r', encoding='utf-8') as f:
            lua_code = f.read()

        chunk = ast.parse(lua_code)
        type_resolver = create_type_resolver()
        type_resolver.resolve_chunk(chunk)

        assert "add" in type_resolver.function_registry.signatures
        signature = type_resolver.function_registry.get_signature("add")
        assert signature is not None
        assert len(signature.param_names) == 2
        assert signature.param_names == ["a", "b"]
