#!/usr/bin/env python3
"""
Compare output from Lua interpreter and C++ executable.
Supports floating-point tolerance for numeric comparisons.
"""

import sys
import math
from typing import List, Tuple


def parse_number(s: str) -> float:
    """Try to parse a string as a number."""
    try:
        return float(s.strip())
    except ValueError:
        return None


def compare_lines(lua_line: str, cpp_line: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
    """
    Compare two lines, using relative tolerance for numeric values.
    
    Returns:
        (matches, message)
    """
    lua_stripped = lua_line.strip()
    cpp_stripped = cpp_line.strip()
    
    # Try numeric comparison first
    lua_num = parse_number(lua_stripped)
    cpp_num = parse_number(cpp_stripped)
    
    if lua_num is not None and cpp_num is not None:
        # Both are numbers - use relative tolerance
        if lua_num == 0 and cpp_num == 0:
            return True, "Both zero"
        
        max_val = max(abs(lua_num), abs(cpp_num))
        diff = abs(lua_num - cpp_num)
        rel_diff = diff / max_val if max_val != 0 else diff
        
        if rel_diff <= tolerance:
            return True, f"Within tolerance: lua={lua_num}, cpp={cpp_num}, rel_diff={rel_diff}"
        else:
            return False, f"Out of tolerance: lua={lua_num}, cpp={cpp_num}, rel_diff={rel_diff}"
    
    # Fall back to string comparison
    if lua_stripped == cpp_stripped:
        return True, "Exact match"
    else:
        return False, f"String mismatch: lua='{lua_stripped}', cpp='{cpp_stripped}'"


def compare_files(lua_path: str, cpp_path: str, tolerance: float = 1e-6) -> bool:
    """
    Compare two output files.
    
    Returns:
        True if all lines match (within tolerance for numeric lines)
    """
    try:
        with open(lua_path, 'r') as f:
            lua_lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Lua output file not found: {lua_path}")
        return False
    
    try:
        with open(cpp_path, 'r') as f:
            cpp_lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: C++ output file not found: {cpp_path}")
        return False
    
    # Check line counts
    if len(lua_lines) != len(cpp_lines):
        print(f"Line count mismatch: Lua has {len(lua_lines)}, C++ has {len(cpp_lines)}")
        return False
    
    all_match = True
    for i, (lua_line, cpp_line) in enumerate(zip(lua_lines, cpp_lines), 1):
        matches, message = compare_lines(lua_line, cpp_line, tolerance)
        if not matches:
            print(f"Line {i}: {message}")
            all_match = False
    
    return all_match


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <lua_output> <cpp_output> [--tolerance=1e-6]")
        sys.exit(1)
    
    lua_path = sys.argv[1]
    cpp_path = sys.argv[2]
    tolerance = 1e-6
    
    for arg in sys.argv[3:]:
        if arg.startswith('--tolerance='):
            tolerance = float(arg.split('=')[1])
    
    if compare_files(lua_path, cpp_path, tolerance):
        print("Output matches!")
        sys.exit(0)
    else:
        print("Output differs.")
        sys.exit(1)


if __name__ == '__main__':
    main()
