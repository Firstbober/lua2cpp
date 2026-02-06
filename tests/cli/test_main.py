"""Test CLI main module"""

import pytest
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

        assert "auto add" in c_code
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
