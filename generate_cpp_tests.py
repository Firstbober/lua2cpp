#!/usr/bin/env python3
"""
Generate C++ test files for all Lua benchmarks.
This script creates main.cpp files and updates CMakeLists.txt.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

# Directory structure
CPP_DIR = Path("tests/cpp")
LUA_DIR = CPP_DIR / "lua"
GENERATED_DIR = CPP_DIR / "generated"

# C++ main file template
CPP_MAIN_TEMPLATE = '''#include "lua_state.hpp"
#include "lua_value.hpp"
#include <iostream>

// Forward declarations for generated modules
luaValue _l2c__{module_name}_export(luaState* state);

int main(int argc, char* argv[]) {{
    std::cout << "Testing transpiled {lua_file}..." << std::endl;

    // Create Lua state
    luaState state;

    // Set command line arguments (Lua's arg table)
    // Note: We skip argv[0] (program name) as Lua's arg[1] is the first script argument
    std::vector<luaValue> args;
    for (int i = 1; i < argc; ++i) {{
        args.push_back(luaValue(argv[i]));
    }}
    state.set_arg(args);

{default_values}

    // Call the transpiled {lua_file} module
    luaValue result = _l2c__{module_name}_export(&state);

    std::cout << "Test completed!" << std::endl;
    return 0;
}}
'''

# Argument patterns for each benchmark
# Key: lua filename without extension
# Value: dict with 'num_args' and optionally 'defaults' list
ARGUMENT_PATTERNS: Dict[str, Dict] = {
    "simple": {
        "num_args": 0,
        "description": "No arguments"
    },
    "comparisons": {
        "num_args": 0,
        "description": "No arguments"
    },
    "spectral-norm": {
        "num_args": 1,
        "defaults": [100],
        "description": "N (default: 100)"
    },
    "fannkuch-redux": {
        "num_args": 1,
        "defaults": [7],
        "description": "n (default: 7)"
    },
    "queen": {
        "num_args": 1,
        "defaults": [8],
        "description": "N (default: 8)"
    },
    "fasta": {
        "num_args": 1,
        "defaults": [1000],
        "description": "N (default: 1000)"
    },
    "heapsort": {
        "num_args": 2,
        "defaults": [4, 10000],
        "description": "num_iterations N (defaults: 4, 10000)"
    },
    "mandel": {
        "num_args": 1,
        "defaults": [256],
        "description": "N (default: 256)"
    },
    "sieve": {
        "num_args": 2,
        "defaults": [100, 8192],
        "description": "num_iterations limit (defaults: 100, 8192)"
    },
    "binary-trees": {
        "num_args": 1,
        "defaults": [0],
        "description": "N (default: 0)"
    },
    "ack": {
        "num_args": 2,
        "defaults": [3, 8],
        "description": "N M (defaults: 3, 8)"
    },
    "n-body": {
        "num_args": 1,
        "defaults": [1000],
        "description": "N (default: 1000)"
    },
    "fixpoint-fact": {
        "num_args": 1,
        "defaults": [100],
        "description": "N (default: 100)"
    },
    "k-nucleotide": {
        "num_args": 0,
        "description": "No arguments (reads from stdin)"
    },
    "qt": {
        "num_args": 0,
        "description": "No arguments"
    },
    "regex-dna": {
        "num_args": 0,
        "description": "No arguments (reads from stdin)"
    },
    "scimark": {
        "num_args": 0,
        "description": "No arguments"
    },
}


def module_name_from_lua_file(lua_filename: str) -> str:
    """Convert Lua filename to module name (e.g., 'spectral-norm.lua' -> 'spectral_norm')"""
    name = lua_filename.replace(".lua", "")
    return name.replace("-", "_")


def generate_default_values(pattern: Dict) -> str:
    """Generate C++ code for default argument values"""
    if not pattern.get("defaults"):
        return "    // No default arguments needed"

    defaults = pattern["defaults"]
    code_lines = []

    for i, default in enumerate(defaults):
        var_name = f"arg{i + 1}"
        if isinstance(default, int):
            code_lines.append(f"    // Set default for arg[{i+1}]")
            code_lines.append(f"    if (argc <= {i+1}) {{")
            code_lines.append(f"        args.push_back(luaValue({default}));")
            code_lines.append(f"        state.set_arg(args);")
            code_lines.append(f"    }}")

    return "\n".join(code_lines)


def generate_cpp_main(lua_file: str, pattern: Dict) -> str:
    """Generate C++ main file content"""
    module_name = module_name_from_lua_file(lua_file)
    default_values = generate_default_values(pattern)

    return CPP_MAIN_TEMPLATE.format(
        module_name=module_name,
        lua_file=lua_file,
        default_values=default_values
    )


def generate_cmake_entries(lua_files: List[str]) -> str:
    """Generate CMakeLists.txt entries for all tests"""
    lines = []
    lines.append("")
    lines.append("# Auto-generated test targets")
    lines.append("")

    for lua_file in sorted(lua_files):
        module_name = module_name_from_lua_file(lua_file)
        test_name = f"{module_name}_test"
        # Use CMake variables for relative paths
        lua_path = f"${{CMAKE_CURRENT_SOURCE_DIR}}/lua/{lua_file}"
        generated_path = f"${{CMAKE_CURRENT_SOURCE_DIR}}/generated/{module_name}.cpp"

        lines.append(f"# Test for {lua_file}")
        lines.append(f"add_custom_command(")
        lines.append(f"    OUTPUT {generated_path}")
        lines.append(f"    COMMAND python -m lua2c.cli.main {lua_path} -o {generated_path}")
        lines.append(f"    DEPENDS {lua_path}")
        lines.append(f"    VERBATIM")
        lines.append(f")")
        lines.append("")
        lines.append(f"add_executable({test_name} {module_name}_main.cpp {generated_path})")
        lines.append(f"target_link_libraries({test_name} lua2c_runtime)")
        lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point"""
    # Ensure directories exist
    GENERATED_DIR.mkdir(exist_ok=True)

    # Get all Lua files
    lua_files = sorted([f.name for f in LUA_DIR.glob("*.lua")])

    print(f"Found {len(lua_files)} Lua files:")
    for lua_file in lua_files:
        pattern = ARGUMENT_PATTERNS.get(lua_file.replace(".lua", ""), {})
        desc = pattern.get("description", "Unknown")
        print(f"  - {lua_file}: {desc}")

    # Generate C++ main files
    print("\nGenerating C++ main files...")
    for lua_file in lua_files:
        base_name = lua_file.replace(".lua", "")
        pattern = ARGUMENT_PATTERNS.get(base_name, {"num_args": 0, "description": "Unknown"})

        cpp_main_content = generate_cpp_main(lua_file, pattern)
        module_name = module_name_from_lua_file(lua_file)
        cpp_main_path = CPP_DIR / f"{module_name}_main.cpp"

        with open(cpp_main_path, "w") as f:
            f.write(cpp_main_content)

        print(f"  Created: {cpp_main_path}")

    # Generate CMakeLists.txt entries
    print("\nGenerating CMakeLists.txt entries...")
    cmake_entries = generate_cmake_entries(lua_files)

    # Read existing CMakeLists.txt
    cmake_path = CPP_DIR / "CMakeLists.txt"
    with open(cmake_path, "r") as f:
        cmake_content = f.read()

    # Remove old auto-generated section if it exists
    cmake_content = re.sub(
        r"# Auto-generated test targets[\s\S]*",
        "",
        cmake_content,
        flags=re.DOTALL
    )

    # Append new entries
    with open(cmake_path, "w") as f:
        f.write(cmake_content.rstrip() + "\n")
        f.write(cmake_entries)

    print(f"  Updated: {cmake_path}")

    # Generate documentation
    print("\nGenerating test documentation...")
    doc_path = CPP_DIR / "TESTS.md"
    with open(doc_path, "w") as f:
        f.write("# C++ Tests for Lua Benchmarks\n\n")
        f.write("This directory contains C++ test executables for all Lua benchmarks.\n\n")
        f.write("## Test List\n\n")

        for lua_file in sorted(lua_files):
            base_name = lua_file.replace(".lua", "")
            pattern = ARGUMENT_PATTERNS.get(base_name, {"num_args": 0, "description": "Unknown"})
            module_name = module_name_from_lua_file(lua_file)
            test_name = f"{module_name}_test"

            f.write(f"### {lua_file}\n")
            f.write(f"- **Test executable**: `{test_name}`\n")
            f.write(f"- **C++ main file**: `{module_name}_main.cpp`\n")
            f.write(f"- **Lua source**: `lua/{lua_file}`\n")
            f.write(f"- **Arguments**: {pattern.get('description', 'Unknown')}\n")
            f.write(f"- **Usage**:\n```bash\n./{test_name}\n")

            if pattern.get("defaults"):
                for i, default in enumerate(pattern["defaults"]):
                    f.write(f"# with argument {i+1}={default}\n")
                    f.write(f"./{test_name} {default}\n")

            f.write("```\n\n")

        f.write("## Build Instructions\n\n")
        f.write("```bash\n")
        f.write("cd tests/cpp/build\n")
        f.write("cmake ..\n")
        f.write("make\n")
        f.write("```\n\n")
        f.write("## Run All Tests\n\n")
        f.write("```bash\n")
        f.write("cd tests/cpp/build\n")
        f.write("for test in *_test; do echo \"=== Running $test ===\"; ./$test; echo; done\n")
        f.write("```\n")

    print(f"  Created: {doc_path}")

    print("\n" + "="*60)
    print("Generation complete!")
    print("="*60)
    print(f"\nNext steps:")
    print(f"1. cd tests/cpp/build")
    print(f"2. cmake ..")
    print(f"3. make")
    print(f"4. Run tests")


if __name__ == "__main__":
    main()
