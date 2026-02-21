#!/usr/bin/env python3
"""
Benchmark script to compare TABLE-based runtime vs TValue/LuaTable runtime.

This script:
1. Transpiles spectral-norm.lua to C++
2. Creates a complete test file with main() and runtime implementations
3. Compiles with each runtime
4. Runs 5 iterations each
5. Reports timing comparison
"""

import subprocess
import time
import tempfile
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
CLI_ROOT = PROJECT_ROOT / "lua2cpp"
LUA_INPUT = PROJECT_ROOT / "tests/cpp/lua/spectral-norm.lua"
RUNTIME_DIR = PROJECT_ROOT / "output/runtime"
RUNTIME_TABLE = RUNTIME_DIR / "l2c_runtime.hpp"
RUNTIME_LUATABLE = RUNTIME_DIR / "l2c_runtime_lua_table.hpp"

ITERATIONS = 5

TABLE_RUNTIME_IMPL = '''
namespace l2c {
    void print_single(const TABLE& value) {
        if (value.str.empty()) {
            std::cout << value.num;
        } else {
            std::cout << value.str;
        }
    }

    TABLE tonumber(const TABLE& value) {
        TABLE result;
        if (!value.str.empty()) {
            try {
                result.num = std::stod(value.str);
            } catch (...) {
                result.num = 0;
            }
        } else {
            result.num = value.num;
        }
        return result;
    }

    TABLE tostring(const TABLE& value) {
        TABLE result;
        if (value.str.empty()) {
            std::ostringstream oss;
            oss << value.num;
            result.str = oss.str();
        } else {
            result.str = value.str;
        }
        return result;
    }

    TABLE string_format_single(const std::string& fmt, const TABLE& value) {
        TABLE result;
        char buffer[256];
        if (fmt.find("%f") != std::string::npos || fmt.find("%0.") != std::string::npos) {
            std::snprintf(buffer, sizeof(buffer), fmt.c_str(), value.num);
            result.str = buffer;
        } else if (fmt.find("%d") != std::string::npos) {
            std::snprintf(buffer, sizeof(buffer), fmt.c_str(), static_cast<int>(value.num));
            result.str = buffer;
        } else if (fmt.find("%s") != std::string::npos) {
            std::snprintf(buffer, sizeof(buffer), fmt.c_str(), value.str.c_str());
            result.str = buffer;
        } else {
            result.str = fmt;
        }
        return result;
    }

    NUMBER math_sqrt(const TABLE& value) {
        return std::sqrt(value.num);
    }

    void io_write_single(const TABLE& value) {
        if (value.str.empty()) {
            std::cout << value.num;
        } else {
            std::cout << value.str;
        }
    }

    NUMBER math_random(NUMBER min, NUMBER max) {
        static bool seeded = false;
        if (!seeded) { std::srand(static_cast<unsigned>(std::time(nullptr))); seeded = true; }
        NUMBER scale = static_cast<NUMBER>(std::rand()) / RAND_MAX;
        return min + scale * (max - min);
    }
}
'''

def run_command(cmd, cwd=None, capture=True):
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd or PROJECT_ROOT,
        capture_output=capture,
        text=True
    )
    return result

def transpile_lua(lua_file, output_cpp):
    cmd = f'python -m lua2cpp.cli.main "{lua_file}" -o "{output_cpp}"'
    result = run_command(cmd, cwd=CLI_ROOT)
    if result.returncode != 0:
        print(f"Transpile error: {result.stderr}")
        raise RuntimeError(f"Transpilation failed: {result.stderr}")
    return output_cpp

def create_table_wrapper(generated_cpp_path, output_path):
    with open(generated_cpp_path, 'r') as f:
        generated = f.read()
    
    generated_modified = generated.replace(
        '#include "../runtime/l2c_runtime.hpp"',
        '// runtime included via wrapper'
    )
    
    wrapper = f'''// TABLE Runtime Benchmark
#include "l2c_runtime.hpp"
#include <sstream>

{TABLE_RUNTIME_IMPL}

{generated_modified}

int main() {{
    spectral_norm_module_init(TABLE());
    return 0;
}}
'''
    with open(output_path, 'w') as f:
        f.write(wrapper)
    return output_path

def create_luatable_wrapper(generated_cpp_path, output_path):
    with open(generated_cpp_path, 'r') as f:
        generated = f.read()
    
    generated_modified = generated.replace(
        '#include "../runtime/l2c_runtime.hpp"',
        '#include "l2c_runtime_lua_table.hpp"'
    )
    
    wrapper = f'''// LuaTable Runtime Benchmark
{generated_modified}

int main() {{
    spectral_norm_module_init(TValue::Nil());
    return 0;
}}
'''
    with open(output_path, 'w') as f:
        f.write(wrapper)
    return output_path

def compile_cpp(cpp_file, output_exe, runtime_dir):
    cmd = f'g++ -O2 -std=c++17 -I "{runtime_dir}" "{cpp_file}" -o "{output_exe}" -lm'
    result = run_command(cmd)
    if result.returncode != 0:
        print(f"Compile error: {result.stderr}")
        raise RuntimeError(f"Compilation failed: {result.stderr}")
    return output_exe

def run_benchmark(exe_path, iterations=5):
    times = []
    for i in range(iterations):
        start = time.perf_counter()
        result = run_command(f'"{exe_path}"', capture=False)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        print(f"  Iteration {i+1}: {elapsed:.3f} s")
    return times

def main():
    print("=" * 60)
    print("Lua2C++ Runtime Performance Benchmark")
    print("=" * 60)
    print(f"Input: {LUA_INPUT}")
    print(f"Iterations: {ITERATIONS}")
    print()
    
    if not LUA_INPUT.exists():
        print(f"Error: Input file not found: {LUA_INPUT}")
        sys.exit(1)
    if not RUNTIME_TABLE.exists():
        print(f"Error: TABLE runtime not found: {RUNTIME_TABLE}")
        sys.exit(1)
    if not RUNTIME_LUATABLE.exists():
        print(f"Error: LuaTable runtime not found: {RUNTIME_LUATABLE}")
        sys.exit(1)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        generated_cpp = tmpdir / "spectral_norm_gen.cpp"
        table_wrapper = tmpdir / "spectral_norm_table.cpp"
        luatable_wrapper = tmpdir / "spectral_norm_luatable.cpp"
        exe_table = tmpdir / "spectral_norm_table"
        exe_luatable = tmpdir / "spectral_norm_luatable"
        
        print("Transpiling spectral-norm.lua...")
        transpile_lua(LUA_INPUT, generated_cpp)
        print(f"  Generated: {generated_cpp}")
        print()
        
        print("Benchmarking TABLE runtime...")
        create_table_wrapper(generated_cpp, table_wrapper)
        compile_cpp(table_wrapper, exe_table, RUNTIME_DIR)
        table_times = run_benchmark(exe_table, ITERATIONS)
        table_avg = sum(table_times) / len(table_times)
        print(f"  Average: {table_avg:.3f} s")
        print()
        
        print("Benchmarking LuaTable runtime...")
        create_luatable_wrapper(generated_cpp, luatable_wrapper)
        compile_cpp(luatable_wrapper, exe_luatable, RUNTIME_DIR)
        luatable_times = run_benchmark(exe_luatable, ITERATIONS)
        luatable_avg = sum(luatable_times) / len(luatable_times)
        print(f"  Average: {luatable_avg:.3f} s")
        print()
        
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"TABLE:    {table_avg:.3f} s")
        print(f"LuaTable: {luatable_avg:.3f} s")
        print()
        
        if luatable_avg < table_avg:
            speedup = table_avg / luatable_avg
            print(f"LuaTable is {speedup:.2f}x FASTER")
        else:
            slowdown = luatable_avg / table_avg
            print(f"LuaTable is {slowdown:.2f}x SLOWER")
        
        print()
        print("Details:")
        print(f"  TABLE times:    {[f'{t:.3f}' for t in table_times]}")
        print(f"  LuaTable times: {[f'{t:.3f}' for t in luatable_times]}")
        
        return {
            "table_avg": table_avg,
            "luatable_avg": luatable_avg,
            "table_times": table_times,
            "luatable_times": luatable_times
        }

if __name__ == "__main__":
    results = main()
