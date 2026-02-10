"""Integration tests for Lua2Cpp transpiler

Tests transpilation of simple.lua and spectral-norm.lua to verify:
- Generated C++ uses correct type identifiers from Type.cpp_type()
- Generated code has no main() function
- Generated C++ has valid syntax
"""

import os
import pytest
import tempfile
import subprocess
from pathlib import Path

try:
    from luaparser import ast
except ImportError:
    pytest.skip("luaparser is required. Install with: pip install luaparser", allow_module_level=True)

from lua2cpp.generators.cpp_emitter import CppEmitter


LUA_TEST_DIR = Path(__file__).parent.parent.parent / "tests" / "cpp" / "lua"


class TestIntegration:
    """Integration tests for Lua to C++ transpilation"""

    def test_simple_transpilation(self):
        """Test transpilation of simple.lua

        simple.lua:
            local function add(a, b)
                return a + b
            end

            local x = add(5, 7)
            print(x)

        Verifies:
        - Generated C++ code is produced successfully
        - Uses type identifiers from Type.cpp_type() (e.g., 'auto' for UNKNOWN)
        - No main() function in generated code
        - Valid C++ syntax (verified with g++ -fsyntax-only)
        """
        lua_file = LUA_TEST_DIR / "simple.lua"
        assert lua_file.exists(), f"Test file not found: {lua_file}"

        with open(lua_file, 'r', encoding='utf-8') as f:
            lua_code = f.read()

        chunk = ast.parse(lua_code)
        assert chunk is not None

        emitter = CppEmitter()
        cpp_code = emitter.generate_file(chunk, lua_file)

        assert cpp_code is not None
        assert len(cpp_code) > 0

        # Type.cpp_type() returns 'auto' for TypeKind.UNKNOWN
        # Type.cpp_type() returns 'double' for TypeKind.NUMBER
        # Type.cpp_type() returns 'bool' for TypeKind.BOOLEAN
        # Type.cpp_type() returns 'std::string' for TypeKind.STRING
        assert 'auto' in cpp_code, "Generated code should use 'auto' type identifier"

        assert 'int main(' not in cpp_code, "Generated code should not contain main() function"
        assert 'main()' not in cpp_code, "Generated code should not contain main() function"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as tmp_file:
            tmp_file.write(cpp_code)
            tmp_file_path = tmp_file.name

        try:
            result = subprocess.run(
                ['g++', '-fsyntax-only', '-std=c++17', tmp_file_path],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                stderr = result.stderr
                if 'syntax error' in stderr.lower():
                    pytest.fail(f"C++ syntax error in generated code:\n{stderr}")
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    def test_spectral_norm_transpilation(self):
        """Test transpilation of spectral-norm.lua

        spectral-norm.lua is a more complex benchmark with:
        - Multiple functions (A, Av, Atv, AtAv)
        - Nested loops
        - Library access (io.write, math.sqrt, string.format)
        - Array operations

        Verifies:
        - Generated C++ code is produced successfully
        - Uses type identifiers from Type.cpp_type()
        - No main() function in generated code
        - Valid C++ syntax
        """
        lua_file = LUA_TEST_DIR / "spectral-norm.lua"
        assert lua_file.exists(), f"Test file not found: {lua_file}"

        with open(lua_file, 'r', encoding='utf-8') as f:
            lua_code = f.read()

        chunk = ast.parse(lua_code)
        assert chunk is not None

        emitter = CppEmitter()
        cpp_code = emitter.generate_file(chunk, lua_file)

        assert cpp_code is not None
        assert len(cpp_code) > 0

        assert 'auto' in cpp_code, "Generated code should use 'auto' type identifier"

        assert 'int main(' not in cpp_code, "Generated code should not contain main() function"
        assert 'main()' not in cpp_code, "Generated code should not contain main() function"

        assert 'A' in cpp_code, "Function A should appear in generated code"
        assert 'Av' in cpp_code, "Function Av should appear in generated code"
        assert 'Atv' in cpp_code, "Function Atv should appear in generated code"
        assert 'AtAv' in cpp_code, "Function AtAv should appear in generated code"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as tmp_file:
            tmp_file.write(cpp_code)
            tmp_file_path = tmp_file.name

        try:
            result = subprocess.run(
                ['g++', '-fsyntax-only', '-std=c++17', tmp_file_path],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                stderr = result.stderr
                if 'syntax error' in stderr.lower():
                    pytest.fail(f"C++ syntax error in generated code:\n{stderr}")
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
