#!/usr/bin/env python3
"""Test library alias detection in different Lua files."""

import sys
import os
sys.path.insert(0, '/home/bober/Documents/ProgrammingProjects/Python/lua2c')
sys.path.insert(0, '/home/bober/.local/lib/python3.14/site-packages')

import lua2cpp

def test_heapsort():
    """Test heapsort.lua which has math.random and math.floor aliases."""
    lua_code = """local random, floor = math.random, math.floor
function test()
    local n = floor(10.5)
    local r = random()
    return n + r
end"""
    
    # Parse the Lua code
    import luaparser as ast
    
    chunk = ast.parse(lua_code)
    
    # Test the _collect_library_aliases method
    # We need to create an emitter and test it
    from lua2cpp.generators.cpp_emitter import CppEmitter
    from lua2cpp.core.scope_manager import ScopeManager
    from lua2cpp.core.symbol_table import SymbolTable
    from lua2cpp.core.function_registry import FunctionRegistry
    
    scope_manager = ScopeManager()
    symbol_table = SymbolTable()
    function_registry = FunctionRegistry()
    emitter = CppEmitter(scope_manager, symbol_table, function_registry)
    
    # Call the method
    emitter._collect_library_aliases(chunk)
    
    # Check the aliases
    aliases = emitter._stmt_gen.get_library_aliases()
    
    assert 'random' in aliases, "random alias not found"
    assert 'floor' in aliases, "floor alias not found"
    
    random_alias = aliases['random']
    floor_alias = aliases['floor']
    
    assert random_alias.lua_name == 'random', f"Expected random.lua_name, got {random_alias.lua_name}"
    assert floor_alias.lua_name == 'floor', f"Expected floor.lua_name, got {floor_alias.lua_name}"
    
    assert random_alias.cpp_lib == 'math_lib', f"Expected math_lib, got {random_alias.cpp_lib}"
    assert floor_alias.cpp_lib == 'math_lib', f"Expected math_lib, got {floor_alias.cpp_lib}"
    
    print("✓ Heapsort test passed!")
    return True

def test_fasta():
    """Test fasta.lua which has io.write and string.sub aliases."""
    lua_code = """local write, sub = io.write, string.sub
function test()
    local s = sub("hello world", 1, 5)
    write(s)
    return s
end"""
    
    import luaparser as ast
    chunk = ast.parse(lua_code)
    
    from lua2cpp.generators.cpp_emitter import CppEmitter
    from lua2cpp.core.scope_manager import ScopeManager
    from lua2cpp.core.symbol_table import SymbolTable
    from lua2cpp.core.function_registry import FunctionRegistry
    
    scope_manager = ScopeManager()
    symbol_table = SymbolTable()
    function_registry = FunctionRegistry()
    emitter = CppEmitter(scope_manager, symbol_table, function_registry)
    
    emitter._collect_library_aliases(chunk)
    
    aliases = emitter._stmt_gen.get_library_aliases()
    
    assert 'write' in aliases, "write alias not found"
    assert 'sub' in aliases, "sub alias not found"
    
    write_alias = aliases['write']
    sub_alias = aliases['sub']
    
    assert write_alias.lua_name == 'write', f"Expected write.lua_name, got {write_alias.lua_name}"
    assert sub_alias.lua_name == 'sub', f"Expected sub.lua_name, got {sub_alias.lua_name}"
    
    assert write_alias.cpp_lib == 'io', f"Expected io, got {write_alias.cpp_lib}"
    assert sub_alias.cpp_lib == 'string_lib', f"Expected string_lib, got {sub_alias.cpp_lib}"
    
    print("✓ Fasta test passed!")
    return True

def test_no_aliases():
    """Test that no aliases are created when there are none."""
    lua_code = """local x = 10
local y = 20
function test()
    return x + y
end"""
    
    import luaparser as ast
    chunk = ast.parse(lua_code)
    
    from lua2cpp.generators.cpp_emitter import CppEmitter
    from lua2cpp.core.scope_manager import ScopeManager
    from lua2cpp.core.symbol_table import SymbolTable
    from lua2cpp.core.function_registry import FunctionRegistry
    
    scope_manager = ScopeManager()
    symbol_table = SymbolTable()
    function_registry = FunctionRegistry()
    emitter = CppEmitter(scope_manager, symbol_table, function_registry)
    
    emitter._collect_library_aliases(chunk)
    
    aliases = emitter._stmt_gen.get_library_aliases()
    
    assert len(aliases) == 0, f"Expected no aliases, but got {aliases}"
    
    print("✓ No aliases test passed!")
    return True

def test_function_local_aliases():
    """Test that aliases inside functions are not detected."""
    lua_code = """function test()
    local random, floor = math.random, math.floor
    return random() + floor(10)
end"""
    
    import luaparser as ast
    chunk = ast.parse(lua_code)
    
    from lua2cpp.generators.cpp_emitter import CppEmitter
    from lua2cpp.core.scope_manager import ScopeManager
    from lua2cpp.core.symbol_table import SymbolTable
    from lua2cpp.core.function_registry import FunctionRegistry
    
    scope_manager = ScopeManager()
    symbol_table = SymbolTable()
    function_registry = FunctionRegistry()
    emitter = CppEmitter(scope_manager, symbol_table, function_registry)
    
    emitter._collect_library_aliases(chunk)
    
    aliases = emitter._stmt_gen.get_library_aliases()
    
    assert len(aliases) == 0, f"Expected no aliases (should be inside function), but got {aliases}"
    
    print("✓ Function local aliases test passed!")
    return True

if __name__ == "__main__":
    try:
        test_heapsort()
        test_fasta()
        test_no_aliases()
        test_function_local_aliases()
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
