"""Test CLI main module"""

import pytest
import subprocess
import sys
from pathlib import Path
from lua2c.cli.main import transpile_file


class TestCliMain:
    """Test suite for CLI main"""

    def test_transpile_simple_file(self, tmp_path):
        """Test transpiling a simple Lua file"""
        # Create test Lua file
        lua_file = tmp_path / "test.lua"
        lua_file.write_text("""
local x = 42
local y = x + 10
print(y)
""")

        # Transpile
        c_code = transpile_file(lua_file)

        # Verify output
        assert "luaValue" in c_code
        assert "print" in c_code
        assert "// Lua2C Transpiler" in c_code

    def test_transpile_function_definition(self, tmp_path):
        """Test transpiling function definition"""
        lua_file = tmp_path / "func.lua"
        lua_file.write_text("""
local function add(a, b)
  return a + b
end
""")

        c_code = transpile_file(lua_file)

        assert "auto&&" in c_code and "add" in c_code
        assert "return" in c_code

    def test_transpile_return_statement(self, tmp_path):
        """Test transpiling return statement"""
        lua_file = tmp_path / "return.lua"
        lua_file.write_text("return 42")

        c_code = transpile_file(lua_file)

        assert "return" in c_code
        assert "42" in c_code

    def test_missing_file_raises_error(self, tmp_path):
        """Test that missing file raises error"""
        missing_file = tmp_path / "nonexistent.lua"

        with pytest.raises(FileNotFoundError):
            transpile_file(missing_file)

    def test_header_flag_generates_state_h(self, tmp_path):
        """Test that --header flag generates state.h file"""
        # Create test Lua file with library function call
        lua_file = tmp_path / "test.lua"
        lua_file.write_text("""
local x = math.floor(4.7)
print(x)
""")

        # Run CLI with --header flag
        result = subprocess.run(
            [sys.executable, "-m", "lua2c.cli.main", str(lua_file), "--header", "--output-dir", str(tmp_path)],
            capture_output=True,
            text=True
        )

        # Verify command succeeded
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Verify state.h was generated
        state_h = tmp_path / "state.h"
        assert state_h.exists(), "state.h file was not generated"

        # Verify state.h contains expected content
        state_h_content = state_h.read_text()
        assert "namespace lua2c" in state_h_content or "lua2c" in state_h_content, "state.h should contain lua2c namespace"
        assert "math" in state_h_content.lower(), "state.h should contain math library declarations"

        # Verify other expected files were also generated
        assert (tmp_path / "test_state.hpp").exists(), "test_state.hpp should be generated"
        assert (tmp_path / "test_module.hpp").exists(), "test_module.hpp should be generated"
        assert (tmp_path / "test_module.cpp").exists(), "test_module.cpp should be generated"

    def test_header_flag_without_library_calls(self, tmp_path):
        """Test that --header flag works even without library function calls"""
        # Create test Lua file without library function calls
        lua_file = tmp_path / "simple.lua"
        lua_file.write_text("""
local x = 42
local y = x + 10
""")

        # Run CLI with --header flag
        result = subprocess.run(
            [sys.executable, "-m", "lua2c.cli.main", str(lua_file), "--header", "--output-dir", str(tmp_path)],
            capture_output=True,
            text=True
        )

        # Verify command succeeded
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Verify state.h was still generated
        state_h = tmp_path / "state.h"
        assert state_h.exists(), "state.h file should be generated even without library calls"
