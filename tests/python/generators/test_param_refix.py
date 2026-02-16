"""Tests for auto& parameter generation

Tests for:
1. visit_Function generates auto& for non-State parameters
2. visit_LocalFunction generates auto& for non-State parameters
3. State* state parameter remains unchanged (no &)
4. Generated code includes auto& pattern for function parameters

Test Coverage:
- Global function parameter generation
- Local function parameter generation
- State* state parameter unchanged
- Multiple function parameters with auto&
"""

import unittest
import pytest

try:
    from luaparser import ast
except ImportError:
    pytest.skip("luaparser is required. Install with: pip install luaparser", allow_module_level=True)

from lua2cpp.generators.stmt_generator import StmtGenerator
from lua2cpp.core.types import Type, TypeKind, ASTAnnotationStore


class TestParamRefGeneration(unittest.TestCase):
    """Test suite for auto& parameter generation in StmtGenerator"""

    def test_visit_function_auto_ref(self):
        """Test that visit_Function generates auto& for non-State parameters

        Lua code:
            function foo(a, b)
                return a + b
            end

        Expected C++ code:
            auto foo(State* state, auto& a, auto& b) {
                ...
            }

        Verifies:
        - auto& appears for parameters a and b
        - State* state is first parameter (no & on state)
        - Function signature is correct
        """
        lua_code = """
        function foo(a, b)
            return a + b
        end
        """
        chunk = ast.parse(lua_code)
        assert chunk is not None

        # Get the Function node from the parsed AST
        func_node = chunk.body.body[0]
        assert isinstance(func_node, ast.Function)

        # Use StmtGenerator to generate C++ code
        generator = StmtGenerator()
        cpp_code = generator.generate(func_node)

        # Verify auto& appears for parameters a and b
        assert "auto& a" in cpp_code, \
            "Generated code should have 'auto& a' for parameter a"
        assert "auto& b" in cpp_code, \
            "Generated code should have 'auto& b' for parameter b"

        # Verify State* state appears first without & on state
        assert "State* state" in cpp_code, \
            "Generated code should have 'State* state' as first parameter"
        assert "State* state, auto&" in cpp_code or \
               "State* state,\n    auto&" in cpp_code, \
            "State* state should be followed by auto& parameter(s)"

        # Verify function name is present
        assert "foo(" in cpp_code, \
            "Function name 'foo' should be in generated code"

    def test_visit_local_function_auto_ref(self):
        """Test that visit_LocalFunction generates auto& for non-State parameters

        Lua code:
            local function bar(x, y)
                return x * y
            end

        Expected C++ code:
            auto bar = [](State* state, auto& x, auto& y) -> auto {
                ...
            };

        Verifies:
        - auto& appears for parameters x and y
        - State* state is first parameter (no & on state)
        - Lambda syntax is used for local function
        """
        lua_code = """
        local function bar(x, y)
            return x * y
        end
        """
        chunk = ast.parse(lua_code)
        assert chunk is not None

        # Get the LocalFunction node from the parsed AST
        func_node = chunk.body.body[0]
        assert isinstance(func_node, ast.LocalFunction)

        # Use StmtGenerator to generate C++ code
        generator = StmtGenerator()
        cpp_code = generator.generate(func_node)

        # Verify auto& appears for parameters x and y
        assert "auto& x" in cpp_code, \
            "Generated code should have 'auto& x' for parameter x"
        assert "auto& y" in cpp_code, \
            "Generated code should have 'auto& y' for parameter y"

        # Verify State* state appears first without & on state
        assert "State* state" in cpp_code, \
            "Generated code should have 'State* state' as first parameter"
        assert "State* state, auto&" in cpp_code or \
               "State* state,\n    auto&" in cpp_code, \
            "State* state should be followed by auto& parameter(s)"

        # Verify lambda syntax is used for local function
        assert "auto bar = [](" in cpp_code, \
            "Local function should use lambda syntax 'auto bar = []('"
        assert "-> auto" in cpp_code, \
            "Lambda should have return type annotation '-> auto'"

    def test_state_param_no_ref(self):
        """Test that State* state parameter does not have & appended

        Lua code:
            function test(param)
                return param
            end

        Expected C++ code:
            auto test(State* state, auto& param) {
                ...
            }

        Verifies:
        - State* state appears without & appended
        - No "State*&" in generated code
        - Only "State* state" appears as parameter
        """
        lua_code = """
        function test(param)
            return param
        end
        """
        chunk = ast.parse(lua_code)
        assert chunk is not None

        # Get the Function node from the parsed AST
        func_node = chunk.body.body[0]
        assert isinstance(func_node, ast.Function)

        # Use StmtGenerator to generate C++ code
        generator = StmtGenerator()
        cpp_code = generator.generate(func_node)

        # Verify State* state appears without &
        assert "State* state" in cpp_code, \
            "Generated code should have 'State* state' as first parameter"

        # Verify State*& does NOT appear
        assert "State*&" not in cpp_code, \
            "Generated code should NOT have 'State*&' (State* should not have &)"

        # Verify State* state is followed by auto& parameter
        # This ensures only the State parameter has no &
        assert "auto& param" in cpp_code, \
            "Generated code should have 'auto& param' for the regular parameter"

    def test_multiple_params_all_auto_ref(self):
        """Test that all non-State parameters have auto&

        Lua code:
            function process(a, b, c)
                return a + b + c
            end

        Expected C++ code:
            auto process(State* state, auto& a, auto& b, auto& c) {
                ...
            }

        Verifies:
        - All parameters a, b, c have auto&
        - State* state is first parameter without &
        """
        lua_code = """
        function process(a, b, c)
            return a + b + c
        end
        """
        chunk = ast.parse(lua_code)
        assert chunk is not None

        # Get the Function node from the parsed AST
        func_node = chunk.body.body[0]
        assert isinstance(func_node, ast.Function)

        # Use StmtGenerator to generate C++ code
        generator = StmtGenerator()
        cpp_code = generator.generate(func_node)

        # Verify all parameters have auto&
        assert "auto& a" in cpp_code, \
            "Generated code should have 'auto& a' for parameter a"
        assert "auto& b" in cpp_code, \
            "Generated code should have 'auto& b' for parameter b"
        assert "auto& c" in cpp_code, \
            "Generated code should have 'auto& c' for parameter c"

        # Verify State* state appears first
        assert "State* state" in cpp_code, \
            "Generated code should have 'State* state' as first parameter"
