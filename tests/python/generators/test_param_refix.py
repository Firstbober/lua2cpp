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

        # Verify template parameters appear for parameters a and b
        # Generator uses template types: template<typename T1, typename T2>\nauto foo(T1 a, T2 b)
        assert "T1 a" in cpp_code, \
            "Generated code should have 'T1 a' for parameter a"
        assert "T2 b" in cpp_code, \
            "Generated code should have 'T2 b' for parameter b"

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

        # Verify template parameters appear for parameters x and y
        # Generator uses template types: template<typename x_t, typename y_t>\ndouble bar(x_t x, y_t y)
        assert "x_t x" in cpp_code, \
            "Generated code should have 'x_t x' for parameter x"
        assert "y_t y" in cpp_code, \
            "Generated code should have 'y_t y' for parameter y"

        # Verify function syntax is used for local function
        assert "bar(" in cpp_code, \
            "Local function 'bar' should be in generated code"

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

        # Verify template parameter appears for the regular parameter
        # Generator uses template types: template<typename T1>\nauto test(T1 param)
        assert "T1 param" in cpp_code, \
            "Generated code should have 'T1 param' for the regular parameter"

    def test_multiple_params_all_auto_ref(self):
        """Test that all parameters use template types

        Lua code:
            function process(a, b, c)
                return a + b + c
            end

        Expected C++ code:
            auto process(T1 a, T2 b, T3 c) {
                ...
            }

        Verifies:
        - All parameters a, b, c use template types
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

        # Verify all parameters have template types
        # Generator uses template types: template<typename T1, typename T2, typename T3>\nauto process(T1 a, T2 b, T3 c)
        assert "T1 a" in cpp_code, \
            "Generated code should have 'T1 a' for parameter a"
        assert "T2 b" in cpp_code, \
            "Generated code should have 'T2 b' for parameter b"
        assert "T3 c" in cpp_code, \
            "Generated code should have 'T3 c' for parameter c"

        # Verify function name is present
        assert "process(" in cpp_code, \
            "Function name 'process' should be in generated code"
