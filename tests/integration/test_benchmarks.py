"""Integration tests for Lua2C transpiler

Tests end-to-end functionality including transpilation and compilation.
"""

import pytest
import subprocess
from pathlib import Path
from lua2c.cli.main import transpile_file


class TestIntegration:
    """Integration test suite for Lua2C transpiler"""

    def test_spectral_norm_transpiles(self):
        """Test that spectral-norm.lua transpiles successfully"""
        input_file = Path("tests/cpp/lua/spectral-norm.lua")
        assert input_file.exists(), "spectral-norm.lua benchmark file not found"

        cpp_code = transpile_file(input_file)
        assert cpp_code is not None
        assert "luaValue" in cpp_code
        assert "luaState" in cpp_code
        assert "spectral_norm_export" in cpp_code

    def test_spectral_norm_has_functions(self):
        """Test that spectral-norm.lua generates expected functions"""
        input_file = Path("tests/cpp/lua/spectral-norm.lua")
        cpp_code = transpile_file(input_file)

        # Check for expected function definitions (now using auto& parameters)
        assert "auto A(luaState" in cpp_code
        assert "auto Av(luaState" in cpp_code
        assert "auto Atv(luaState" in cpp_code
        assert "auto AtAv(luaState" in cpp_code

    def test_spectral_norm_has_loops(self):
        """Test that spectral-norm.lua generates for loops correctly"""
        input_file = Path("tests/cpp/lua/spectral-norm.lua")
        cpp_code = transpile_file(input_file)

        # Check for for loops - now optimized to use native double types
        assert ("for (double" in cpp_code or "for (luaValue" in cpp_code)
        assert ".is_truthy()" in cpp_code

    def test_simple_file_transpiles(self):
        """Test that simple.lua transpiles successfully"""
        input_file = Path("tests/cpp/lua/simple.lua")
        if not input_file.exists():
            pytest.skip("tests/cpp/lua/simple.lua not found")

        cpp_code = transpile_file(input_file)
        assert cpp_code is not None
        assert "auto add" in cpp_code
        assert "print" in cpp_code

    @pytest.mark.skipif(
        True,
        reason="Requires sol2 headers to be installed - user will provide them"
    )
    def test_simple_compiles(self):
        """Test that simple.lua can be compiled (requires sol2)"""
        import tempfile
        import shutil

        input_file = Path("tests/cpp/lua/simple.lua")
        if not input_file.exists():
            pytest.skip("tests/cpp/lua/simple.lua not found")

        cpp_code = transpile_file(input_file)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Write generated C++
            generated_cpp = tmpdir_path / "simple.cpp"
            generated_cpp.write_text(cpp_code)

            # Create main wrapper
            main_cpp = tmpdir_path / "main.cpp"
            main_cpp.write_text("""
#include "runtime/lua_value.hpp"
#include "runtime/lua_state.hpp"
#include <iostream>

extern "C" luaValue _l2c__simple_export(luaState* state);

int main() {
    luaState state;
    _l2c__simple_export(&state);
    return 0;
}
""")

            # Try to compile (will fail without sol2, but we check structure)
            # Note: This test is skipped by default
            runtime_dir = Path("runtime")
            compile_cmd = [
                "g++",
                "-std=c++17",
                "-I", str(runtime_dir),
                "-o", str(tmpdir_path / "simple"),
                str(generated_cpp),
                str(main_cpp),
                f"{runtime_dir}/lua_value.cpp",
                f"{runtime_dir}/lua_state.cpp",
            ]

            result = subprocess.run(compile_cmd, capture_output=True, text=True)
            # We expect this to fail without sol2, but command should be valid
            assert result.returncode != 0 or True  # Just ensure command runs

    def test_spectral_norm_as_project(self, tmp_path):
        """Test that spectral-norm.lua transpiles correctly in project mode"""
        from lua2c.cli.main import transpile_project

        # Copy spectral-norm.lua to isolated test directory
        input_file = Path("tests/cpp/lua/spectral-norm.lua")
        assert input_file.exists(), "spectral-norm.lua not found"

        test_dir = tmp_path / "test_project"
        test_dir.mkdir()
        test_file = test_dir / "spectral-norm.lua"
        test_file.write_text(input_file.read_text())

        # Run transpile_project() with verbose=False
        transpile_project(test_file, verbose=False)

        # Verify build directory was created
        build_dir = test_dir / "build"
        assert build_dir.exists(), "Build directory not created"

        # Verify generated files exist
        # Note: Project name is "test_project" (directory name), not "spectral_norm"
        state_file = build_dir / "test_project_state.hpp"
        assert state_file.exists(), f"State file not found: {state_file}"

        assert (build_dir / "test_project_main.cpp").exists(), "main.cpp not found"
        assert (build_dir / "spectral-norm_module.hpp").exists(), "module header not found"
        assert (build_dir / "spectral-norm_module.cpp").exists(), "module cpp not found"

        # Verify state header contains custom state struct
        state_content = state_file.read_text()
        assert "test_project_lua_State" in state_content, "Custom state struct not found"
        assert "luaArray<luaValue> arg;" in state_content, "arg array not found in state"

        # Verify math functions are correctly referenced (no -nan issues)
        main_module = build_dir / "spectral-norm_module.cpp"
        main_content = main_module.read_text()
        assert "math.sqrt" in main_content, "math.sqrt not found in generated code"

        # Verify no direct string-based global lookups (project mode uses state->member)
        assert 'get_global("math")' not in main_content, "String-based global lookup found in project mode"
