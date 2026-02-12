"""Tests for LibraryCallCollector

Tests that library function calls are correctly detected and metadata is retrieved.
"""

import pytest
try:
    from luaparser import ast
    from lua2cpp.core.library_call_collector import LibraryCallCollector
    from lua2cpp.core.types import TypeKind
except ImportError:
    pytest.skip("luaparser is required. Install with: pip install luaparser", allow_module_level=True)


class TestLibraryCallCollector:
    def test_detect_io_write(self):
        """Test that io.write() is detected as library function"""
        code = '''
io.write('test')
'''
        chunk = ast.parse(code)
        collector = LibraryCallCollector()
        collector.visit(chunk)
        calls = collector.get_library_calls()
        
        assert len(calls) == 1
        assert calls[0].module == "io"
        assert calls[0].func == "write"
        assert calls[0].line == 2

    def test_detect_math_sqrt(self):
        """Test that math.sqrt() is detected as library function"""
        code = '''
math.sqrt(4)
'''
        chunk = ast.parse(code)
        collector = LibraryCallCollector()
        collector.visit(chunk)
        calls = collector.get_library_calls()
        
        assert len(calls) == 1
        assert calls[0].module == "math"
        assert calls[0].func == "sqrt"
        assert calls[0].line == 2

    def test_detect_string_format(self):
        """Test that string.format() is detected as library function"""
        code = '''
string.format('hello %s', 'world')
'''
        chunk = ast.parse(code)
        collector = LibraryCallCollector()
        collector.visit(chunk)
        calls = collector.get_library_calls()
        
        assert len(calls) == 1
        assert calls[0].module == "string"
        assert calls[0].func == "format"
        assert calls[0].line == 2

    def test_get_library_info(self):
        """Test that get_library_info() returns correct LibraryFunction"""
        code = '''
io.write('test')
'''
        chunk = ast.parse(code)
        collector = LibraryCallCollector()
        collector.visit(chunk)
        calls = collector.get_library_calls()
        
        # Get info for io.write
        info = collector._registry.get_library_info("io", "write")
        
        assert info is not None
        assert info.module == "io"
        assert info.name == "write"
        assert info.return_type == TypeKind.BOOLEAN

    def test_non_library_call(self):
        """Test that user-defined function is not detected as library"""
        code = '''
function myfunc()
    return 42
end
'''
        chunk = ast.parse(code)
        collector = LibraryCallCollector()
        collector.visit(chunk)
        calls = collector.get_library_calls()

        # No calls should be detected (user function doesn't use Index notation)
        assert len(calls) == 0

    def test_detect_global_functions(self):
        """Test that global function calls are detected as Name nodes"""
        code = '''
print('hello')
tonumber('123')
tostring(42)
'''
        chunk = ast.parse(code)
        collector = LibraryCallCollector()
        collector.visit(chunk)
        calls = collector.get_library_calls()

        # Global functions are NOT library calls (they use Name nodes, not Index nodes)
        # LibraryCallCollector only detects Index-based calls like io.write()
        assert len(calls) == 0

    def test_global_and_library_mixed(self):
        """Test that library calls are detected but global calls are not"""
        code = '''
print('hello')
io.write('world')
tonumber('123')
math.sqrt(4)
'''
        chunk = ast.parse(code)
        collector = LibraryCallCollector()
        collector.visit(chunk)
        calls = collector.get_library_calls()

        # Only library calls should be detected (io.write, math.sqrt)
        assert len(calls) == 2
        module_func_pairs = {(call.module, call.func) for call in calls}
        assert ("io", "write") in module_func_pairs
        assert ("math", "sqrt") in module_func_pairs

    def test_variable_reference_not_global(self):
        """Test that variable references are not detected as library calls"""
        code = '''
local f = print
f('hello')
'''
        chunk = ast.parse(code)
        collector = LibraryCallCollector()
        collector.visit(chunk)
        calls = collector.get_library_calls()

        # Variable reference should not be detected as library call
        assert len(calls) == 0
