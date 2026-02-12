"""Tests for library function registry"""

import pytest
from lua2cpp.core.library_registry import LibraryFunction, LibraryFunctionRegistry
from lua2cpp.core.types import TypeKind


class TestLibraryFunction:
    """Test suite for LibraryFunction dataclass"""

    def test_creation(self):
        """Test creating a LibraryFunction"""
        func = LibraryFunction(
            module="io",
            name="write",
            return_type=TypeKind.BOOLEAN,
            params=[TypeKind.STRING],
            cpp_name="io_write"
        )
        assert func.module == "io"
        assert func.name == "write"
        assert func.return_type == TypeKind.BOOLEAN
        assert func.params == [TypeKind.STRING]
        assert func.cpp_name == "io_write"


class TestLibraryFunctionRegistry:
    """Test suite for LibraryFunctionRegistry"""

    def test_initialization(self):
        """Test registry initializes with all libraries"""
        registry = LibraryFunctionRegistry()
        modules = registry.get_all_modules()
        assert len(modules) == 8
        assert "io" in modules
        assert "string" in modules
        assert "math" in modules
        assert "table" in modules
        assert "os" in modules
        assert "package" in modules
        assert "debug" in modules
        assert "coroutine" in modules

    def test_is_library_function_true(self):
        """Test is_library_function returns True for valid functions"""
        registry = LibraryFunctionRegistry()
        assert registry.is_library_function("io", "write")
        assert registry.is_library_function("string", "format")
        assert registry.is_library_function("math", "sqrt")
        assert registry.is_library_function("table", "insert")

    def test_is_library_function_false_invalid_module(self):
        """Test is_library_function returns False for invalid module"""
        registry = LibraryFunctionRegistry()
        assert not registry.is_library_function("invalid_module", "write")

    def test_is_library_function_false_invalid_function(self):
        """Test is_library_function returns False for invalid function"""
        registry = LibraryFunctionRegistry()
        assert not registry.is_library_function("io", "nonexistent_function")

    def test_get_library_info_valid(self):
        """Test get_library_info returns correct function info"""
        registry = LibraryFunctionRegistry()
        info = registry.get_library_info("io", "write")
        assert info is not None
        assert info.module == "io"
        assert info.name == "write"
        assert info.cpp_name == "io_write"

    def test_get_library_info_none_invalid_module(self):
        """Test get_library_info returns None for invalid module"""
        registry = LibraryFunctionRegistry()
        info = registry.get_library_info("invalid_module", "write")
        assert info is None

    def test_get_library_info_none_invalid_function(self):
        """Test get_library_info returns None for invalid function"""
        registry = LibraryFunctionRegistry()
        info = registry.get_library_info("io", "nonexistent_function")
        assert info is None

    def test_is_standard_library_true(self):
        """Test is_standard_library returns True for standard libraries"""
        registry = LibraryFunctionRegistry()
        assert registry.is_standard_library("io")
        assert registry.is_standard_library("string")
        assert registry.is_standard_library("math")
        assert registry.is_standard_library("table")
        assert registry.is_standard_library("os")
        assert registry.is_standard_library("package")
        assert registry.is_standard_library("debug")
        assert registry.is_standard_library("coroutine")

    def test_is_standard_library_false(self):
        """Test is_standard_library returns False for non-standard modules"""
        registry = LibraryFunctionRegistry()
        assert not registry.is_standard_library("user_module")
        assert not registry.is_standard_library("my_lib")

    def test_get_module_functions_valid_module(self):
        """Test get_module_functions returns all functions in a module"""
        registry = LibraryFunctionRegistry()
        io_funcs = registry.get_module_functions("io")
        assert len(io_funcs) > 0
        func_names = [f.name for f in io_funcs]
        assert "write" in func_names
        assert "read" in func_names
        assert "open" in func_names

    def test_get_module_functions_invalid_module(self):
        """Test get_module_functions returns empty list for invalid module"""
        registry = LibraryFunctionRegistry()
        funcs = registry.get_module_functions("nonexistent_module")
        assert funcs == []

    def test_io_library_functions(self):
        """Test io library has all expected functions"""
        registry = LibraryFunctionRegistry()
        funcs = registry.get_module_functions("io")
        func_names = {f.name for f in funcs}
        assert "close" in func_names
        assert "flush" in func_names
        assert "input" in func_names
        assert "lines" in func_names
        assert "open" in func_names
        assert "output" in func_names
        assert "popen" in func_names
        assert "read" in func_names
        assert "type" in func_names
        assert "write" in func_names

    def test_string_library_functions(self):
        """Test string library has all expected functions"""
        registry = LibraryFunctionRegistry()
        funcs = registry.get_module_functions("string")
        func_names = {f.name for f in funcs}
        assert "byte" in func_names
        assert "char" in func_names
        assert "find" in func_names
        assert "format" in func_names
        assert "gsub" in func_names
        assert "len" in func_names
        assert "lower" in func_names
        assert "upper" in func_names

    def test_math_library_functions(self):
        """Test math library has all expected functions"""
        registry = LibraryFunctionRegistry()
        funcs = registry.get_module_functions("math")
        func_names = {f.name for f in funcs}
        assert "abs" in func_names
        assert "sqrt" in func_names
        assert "sin" in func_names
        assert "cos" in func_names
        assert "random" in func_names
        assert "floor" in func_names
        assert "ceil" in func_names

    def test_table_library_functions(self):
        """Test table library has all expected functions"""
        registry = LibraryFunctionRegistry()
        funcs = registry.get_module_functions("table")
        func_names = {f.name for f in funcs}
        assert "concat" in func_names
        assert "insert" in func_names
        assert "remove" in func_names
        assert "sort" in func_names

    def test_os_library_functions(self):
        """Test os library has all expected functions"""
        registry = LibraryFunctionRegistry()
        funcs = registry.get_module_functions("os")
        func_names = {f.name for f in funcs}
        assert "clock" in func_names
        assert "date" in func_names
        assert "execute" in func_names
        assert "exit" in func_names

    def test_package_library_functions(self):
        """Test package library has all expected functions"""
        registry = LibraryFunctionRegistry()
        funcs = registry.get_module_functions("package")
        func_names = {f.name for f in funcs}
        assert "loadlib" in func_names
        assert "searchpath" in func_names

    def test_debug_library_functions(self):
        """Test debug library has all expected functions"""
        registry = LibraryFunctionRegistry()
        funcs = registry.get_module_functions("debug")
        func_names = {f.name for f in funcs}
        assert "debug" in func_names
        assert "getinfo" in func_names
        assert "getlocal" in func_names
        assert "traceback" in func_names

    def test_coroutine_library_functions(self):
        """Test coroutine library has all expected functions"""
        registry = LibraryFunctionRegistry()
        funcs = registry.get_module_functions("coroutine")
        func_names = {f.name for f in funcs}
        assert "create" in func_names
        assert "resume" in func_names
        assert "yield" in func_names
        assert "status" in func_names

    def test_function_cpp_name_format(self):
        """Test cpp_name follows expected format"""
        registry = LibraryFunctionRegistry()
        info = registry.get_library_info("io", "write")
        assert info.cpp_name == "io_write"

        info = registry.get_library_info("math", "sqrt")
        assert info.cpp_name == "math_sqrt"

        info = registry.get_library_info("string", "format")
        assert info.cpp_name == "string_format"

    def test_all_functions_have_valid_cpp_names(self):
        """Test all registered functions have cpp_name following convention"""
        registry = LibraryFunctionRegistry()
        for module in registry.get_all_modules():
            funcs = registry.get_module_functions(module)
            for func in funcs:
                assert func.cpp_name.startswith(module + "_")
                assert func.name in func.cpp_name

    def test_function_return_types(self):
        """Test functions have appropriate return types"""
        registry = LibraryFunctionRegistry()
        info = registry.get_library_info("io", "write")
        assert info.return_type == TypeKind.BOOLEAN

        info = registry.get_library_info("string", "format")
        assert info.return_type == TypeKind.STRING

        info = registry.get_library_info("math", "sqrt")
        assert info.return_type == TypeKind.NUMBER

    def test_library_function_fields(self):
        """Test LibraryFunction has all required fields"""
        registry = LibraryFunctionRegistry()
        info = registry.get_library_info("io", "write")
        assert hasattr(info, "module")
        assert hasattr(info, "name")
        assert hasattr(info, "return_type")
        assert hasattr(info, "params")
        assert hasattr(info, "cpp_name")
        assert isinstance(info.params, list)

    def test_global_functions_registered(self):
        """Test that all 18 global functions are registered"""
        registry = LibraryFunctionRegistry()

        # Test all global functions are registered
        global_functions = [
            "print", "tonumber", "tostring", "type", "ipairs", "pairs", "next",
            "error", "assert", "pcall", "xpcall", "select", "collectgarbage",
            "rawget", "rawset", "rawlen", "getmetatable", "setmetatable"
        ]

        for func_name in global_functions:
            assert registry.is_global_function(func_name), \
                f"Global function '{func_name}' should be registered"

    def test_global_function_info_module(self):
        """Test that global functions have empty string as module"""
        registry = LibraryFunctionRegistry()

        global_functions = ["print", "tonumber", "tostring"]

        for func_name in global_functions:
            info = registry.get_global_info(func_name)
            assert info is not None, f"Global function '{func_name}' should have info"
            assert info.module == "", f"Global function '{func_name}' module should be empty string"

    def test_global_function_info_structure(self):
        """Test that global function info has correct structure"""
        registry = LibraryFunctionRegistry()
        info = registry.get_global_info("print")

        assert info is not None
        assert info.name == "print"
        assert info.module == ""
        assert info.cpp_name == "print"
        assert hasattr(info, "return_type")
        assert hasattr(info, "params")

    def test_is_global_function_false_for_library(self):
        """Test that is_global_function returns False for library functions"""
        registry = LibraryFunctionRegistry()

        # io.write is a library function, not a global
        assert not registry.is_global_function("io"), "Module name should not be global function"

    def test_get_global_info_none_for_unknown(self):
        """Test that get_global_info returns None for unknown function"""
        registry = LibraryFunctionRegistry()
        info = registry.get_global_info("unknown_global_function")
        assert info is None
