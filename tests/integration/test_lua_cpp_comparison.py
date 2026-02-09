"""Integration tests comparing C++ and Lua outputs for various Lua tests.

This test ensures the transpiler produces C++ code that produces the same
output as the original Lua code when executed.
"""

import pytest
import subprocess
from pathlib import Path


# Test configurations: (lua_script, cpp_executable, description)
TEST_CONFIGS = [
    ("simple.lua", "simple_test", "Simple addition test"),
    ("ack.lua", "ack_test", "Ackermann function test"),
    ("test_array.lua", "test_array_test", "Array operations test"),
    ("test_assign.lua", "test_assign_test", "Assignment test"),
    ("test_func.lua", "test_func_test", "Function definition test"),
    ("comparisons.lua", "comparisons_test", "Comparison operators test"),
]


@pytest.mark.parametrize("lua_script,cpp_executable,description", TEST_CONFIGS)
def test_lua_cpp_outputs_match(lua_script, cpp_executable, description):
    """Test that C++ and Lua outputs match.

    Runs Lua script with Lua interpreter and transpiled C++ executable,
    then compares their outputs.

    Args:
        lua_script: Path to Lua test file
        cpp_executable: Name of compiled C++ executable
        description: Description of what is being tested
    """
    lua_file = Path("tests/cpp/lua") / lua_script
    cpp_exe = Path("tests/cpp/build") / cpp_executable

    if not lua_file.exists():
        pytest.skip(f"Lua script not found: {lua_file}")

    if not cpp_exe.exists():
        pytest.skip(f"C++ executable not found: {cpp_exe}. Build it first with make {cpp_executable}")

    # Run Lua script
    lua_result = subprocess.run(
        ["lua", str(lua_file)],
        capture_output=True,
        text=True,
        check=True
    )
    lua_output = lua_result.stdout.strip()

    # Run C++ executable
    cpp_result = subprocess.run(
        [str(cpp_exe)],
        capture_output=True,
        text=True
    )

    if cpp_result.returncode != 0:
        pytest.fail(
            f"C++ executable failed with exit code {cpp_result.returncode}.\n"
            f"stderr: {cpp_result.stderr}"
        )

    # Filter C++ output: Remove test wrapper messages, keep only actual Lua script output
    cpp_output_lines = [
        line for line in cpp_result.stdout.strip().split('\n')
        if not line.startswith("Testing transpiled ")
        and not line.startswith("Running ")
        and not line.startswith("Test completed successfully!")
        and line.strip()
    ]
    # Normalize numeric output: C++ print() outputs "12.000000" while Lua outputs "12"
    cpp_output_normalized = '\n'.join([
        line.rstrip('0').rstrip('.') if line.replace('.', '', 1).isdigit() else line
        for line in cpp_output_lines
    ]).strip()
    cpp_output = cpp_output_normalized

    # Compare outputs
    assert lua_output == cpp_output, (
        f"C++ and Lua outputs differ for {description}:\n"
        f"  Lua output:\n{lua_output}\n"
        f"  C++ output:\n{cpp_output}"
    )

    print(f"\n{description} - PASSED:")
    print(f"  Lua:   {repr(lua_output)}")
    print(f"  C++:   {repr(cpp_output)}")


def test_spectral_norm_outputs_match():
    """Test spectral-norm separately (has different comparison logic with float values)"""
    lua_script = Path("tests/cpp/lua/spectral-norm.lua")
    cpp_executable = Path("tests/cpp/build/spectralnorm_test")

    if not lua_script.exists():
        pytest.skip(f"Lua script not found: {lua_script}")

    if not cpp_executable.exists():
        pytest.skip(f"C++ executable not found: {cpp_executable}. Build it first with make spectralnorm_test")

    n_value = "100"

    lua_result = subprocess.run(
        ["lua", str(lua_script), n_value],
        capture_output=True,
        text=True,
        check=True
    )
    lua_output = lua_result.stdout.strip()

    cpp_result = subprocess.run(
        [str(cpp_executable), n_value],
        capture_output=True,
        text=True
    )

    if cpp_result.returncode != 0:
        pytest.fail(
            f"C++ executable failed with exit code {cpp_result.returncode}.\n"
            f"stderr: {cpp_result.stderr}"
        )

    cpp_output = cpp_result.stdout.strip()

    # Compare float values with tolerance
    try:
        lua_value = float(lua_output)
        cpp_value = float(cpp_output)
    except ValueError as e:
        pytest.fail(f"Failed to parse outputs as floats. Lua: '{lua_output}', C++: '{cpp_output}'. Error: {e}")

    epsilon = 1e-9
    tolerance = 1e-6

    absolute_diff = abs(lua_value - cpp_value)
    relative_diff = absolute_diff / max(abs(lua_value), abs(cpp_value))

    if absolute_diff < epsilon:
        pass
    else:
        assert relative_diff < tolerance, (
            f"C++ and Lua outputs differ beyond tolerance:\n"
            f"  Lua output:   {lua_output} ({lua_value})\n"
            f"  C++ output:   {cpp_output} ({cpp_value})\n"
            f"  Abs diff:     {absolute_diff}\n"
            f"  Rel diff:     {relative_diff:.2%}\n"
            f"  Max allowed:  {tolerance:.2%}"
        )

    print(f"\nSpectral-norm comparison (N={n_value}):")
    print(f"  Lua:   {lua_output}")
    print(f"  C++:   {cpp_output}")
    print(f"  Diff:  {absolute_diff:.2e}")
