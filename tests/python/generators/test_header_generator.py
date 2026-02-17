"""Tests for HeaderGenerator class

Tests for:
1. Pragma once guard generation
2. Struct definitions for library modules
3. Global function declarations
4. Template functions for variadic parameters
5. Namespace declarations
6. Complete header file generation

Test Coverage:
- _generate_pragma_once() method
- _generate_struct_definitions() method
- _generate_global_function_declarations() method
- generate_header() method with various inputs
- Edge cases (empty inputs, unknown functions, duplicate calls)
"""

import pytest
from lua2cpp.generators.header_generator import HeaderGenerator
from lua2cpp.core.library_call_collector import LibraryCall
from lua2cpp.core.library_registry import LibraryFunctionRegistry
from lua2cpp.core.types import TypeKind


class TestGeneratePragmaOnce:
    """Test _generate_pragma_once() method"""

    def test_pragma_once_generates_directive(self):
        """Test that _generate_pragma_once() generates #pragma once directive

        Expected output: "#pragma once"
        """
        gen = HeaderGenerator()
        pragma = gen._generate_pragma_once()
        assert pragma == "#pragma once", \
            "Pragma once should generate '#pragma once' directive"

    def test_pragma_once_returns_string(self):
        """Test that _generate_pragma_once() returns a string

        Expected: Return type should be str
        """
        gen = HeaderGenerator()
        pragma = gen._generate_pragma_once()
        assert isinstance(pragma, str), \
            "Pragma once should return a string"


class TestGenerateStructDefinitions:
    """Test _generate_struct_definitions() method"""

    def test_single_library_single_function(self):
        """Test struct definition for single library with one function

        Library calls: io.write
        Expected: struct io { static bool io_write(State* state); };
        """
        gen = HeaderGenerator()
        library_calls = [LibraryCall("io", "write", 10)]

        struct_defs = gen._generate_struct_definitions(library_calls)

        assert len(struct_defs) > 0, "Should generate struct definitions"
        assert any("struct io {" in line for line in struct_defs), \
            "Should define struct io"
        assert any("io_write" in line for line in struct_defs), \
            "Should declare io_write function"

    def test_single_library_multiple_functions(self):
        """Test struct definition for single library with multiple functions

        Library calls: io.write, io.read, io.open
        Expected: struct io with all three function declarations
        """
        gen = HeaderGenerator()
        library_calls = [
            LibraryCall("io", "write", 10),
            LibraryCall("io", "read", 15),
            LibraryCall("io", "open", 20)
        ]

        struct_defs = gen._generate_struct_definitions(library_calls)

        assert any("struct io {" in line for line in struct_defs), \
            "Should define struct io"
        assert any("io_write" in line for line in struct_defs), \
            "Should declare io_write function"
        assert any("io_read" in line for line in struct_defs), \
            "Should declare io_read function"
        assert any("io_open" in line for line in struct_defs), \
            "Should declare io_open function"

    def test_multiple_libraries(self):
        """Test struct definitions for multiple library modules

        Library calls: io.write, math.sqrt, string.len
        Expected: Three separate structs: io, math, string
        """
        gen = HeaderGenerator()
        library_calls = [
            LibraryCall("io", "write", 10),
            LibraryCall("math", "sqrt", 15),
            LibraryCall("string", "len", 20)
        ]

        struct_defs = gen._generate_struct_definitions(library_calls)

        assert any("struct io {" in line for line in struct_defs), \
            "Should define struct io"
        assert any("struct math {" in line for line in struct_defs), \
            "Should define struct math"
        assert any("struct string {" in line for line in struct_defs), \
            "Should define struct string"

    def test_empty_library_calls(self):
        """Test struct definitions with no library calls

        Library calls: []
        Expected: Empty list (no struct definitions)
        """
        gen = HeaderGenerator()
        library_calls = []

        struct_defs = gen._generate_struct_definitions(library_calls)

        assert struct_defs == [], \
            "Should return empty list for no library calls"

    def test_duplicate_calls_single_function(self):
        """Test that duplicate calls to same function generate single declaration

        Library calls: math.sqrt (line 10), math.sqrt (line 15), math.sqrt (line 20)
        Expected: struct math with single sqrt declaration (not duplicates)
        """
        gen = HeaderGenerator()
        library_calls = [
            LibraryCall("math", "sqrt", 10),
            LibraryCall("math", "sqrt", 15),
            LibraryCall("math", "sqrt", 20)
        ]

        struct_defs = gen._generate_struct_definitions(library_calls)

        sqrt_count = sum(1 for line in struct_defs if "math_sqrt" in line)
        assert sqrt_count == 1, \
            "Should generate single declaration for duplicate calls"

    def test_unknown_function_comment(self):
        """Test that unknown functions generate comment instead of declaration

        Library calls: unknown.unknown_function
        Expected: Comment like "// unknown.unknown_function - unknown function signature"
        """
        gen = HeaderGenerator()
        library_calls = [LibraryCall("unknown", "unknown_function", 10)]

        struct_defs = gen._generate_struct_definitions(library_calls)

        assert any("unknown.unknown_function" in line and "//" in line for line in struct_defs), \
            "Should add comment for unknown function"
        assert not any("static" in line and "unknown_function" in line for line in struct_defs), \
            "Should NOT generate declaration for unknown function"


class TestGenerateGlobalFunctionDeclarations:
    """Test _generate_global_function_declarations() method"""

    def test_single_global_function(self):
        """Test global function declaration for single function

        Global functions: {"print"}
        Expected: namespace lua2c { ... print(...); };
        """
        gen = HeaderGenerator()
        global_functions = {"print"}

        decls = gen._generate_global_function_declarations(global_functions)

        assert len(decls) > 0, "Should generate declarations"
        assert any("namespace l2c {" in line for line in decls), \
            "Should use l2c namespace"
        assert any("print" in line for line in decls), \
            "Should declare print function"

    def test_multiple_global_functions(self):
        """Test global function declarations for multiple functions

        Global functions: {"print", "tonumber", "tostring"}
        Expected: All three functions declared in lua2c namespace
        """
        gen = HeaderGenerator()
        global_functions = {"print", "tonumber", "tostring"}

        decls = gen._generate_global_function_declarations(global_functions)

        assert any("namespace l2c {" in line for line in decls), \
            "Should use l2c namespace"
        assert any("print" in line for line in decls), \
            "Should declare print function"
        assert any("tonumber" in line for line in decls), \
            "Should declare tonumber function"
        assert any("tostring" in line for line in decls), \
            "Should declare tostring function"

    def test_namespace_opening_and_closing(self):
        """Test that namespace has proper opening and closing

        Global functions: {"print"}
        Expected: namespace lua2c { ... }  // namespace lua2c
        """
        gen = HeaderGenerator()
        global_functions = {"print"}

        decls = gen._generate_global_function_declarations(global_functions)

        assert decls[0] == "namespace l2c {", \
            "First line should open namespace"
        assert decls[-1] == "}  // namespace l2c", \
            "Last line should close namespace with comment"

    def test_empty_global_functions(self):
        """Test global function declarations with no functions

        Global functions: set()
        Expected: Empty namespace lua2c { }
        """
        gen = HeaderGenerator()
        global_functions = set()

        decls = gen._generate_global_function_declarations(global_functions)

        assert len(decls) == 2, \
            "Should return namespace opening and closing even when empty"
        assert decls[0] == "namespace l2c {", \
            "First line should open namespace"
        assert decls[1] == "}  // namespace l2c", \
            "Last line should close namespace"

    def test_unknown_global_function_comment(self):
        """Test that unknown global functions generate comment

        Global functions: {"unknown_func"}
        Expected: Comment like "// unknown_func - unknown function signature"
        Note: Global function signatures are not yet in registry
        """
        gen = HeaderGenerator()
        global_functions = {"unknown_func"}

        decls = gen._generate_global_function_declarations(global_functions)

        assert any("unknown_func" in line and "//" in line for line in decls), \
            "Should add comment for unknown global function"

    def test_get_global_function_info(self):
        """Test that _get_global_function_info returns correct LibraryFunction"""
        gen = HeaderGenerator()

        # Test known global function 'print'
        info = gen._get_global_function_info("print")
        assert info is not None, "Global function 'print' should be found"
        assert info.name == "print", "Function name should be 'print'"
        assert info.module == "", "Global functions have empty module"
        assert info.cpp_name == "print", "CPP name should match function name"
        assert hasattr(info, "return_type"), "Should have return_type"
        assert hasattr(info, "params"), "Should have params"

        # Test known global function 'tonumber'
        info = gen._get_global_function_info("tonumber")
        assert info is not None, "Global function 'tonumber' should be found"
        assert info.name == "tonumber", "Function name should be 'tonumber'"
        assert info.module == "", "Global functions have empty module"

        # Test unknown function
        info = gen._get_global_function_info("unknown_function")
        assert info is None, "Unknown function should return None"

    def test_known_global_function_declarations(self):
        """Test that known global functions generate proper declarations"""
        gen = HeaderGenerator()
        global_functions = {"print", "tonumber", "tostring"}

        decls = gen._generate_global_function_declarations(global_functions)

        assert any("namespace l2c {" in line for line in decls), \
            "Should use l2c namespace"
        assert any("print" in line and "print" not in "//" for line in decls), \
            "Should declare print function (not as comment)"
        assert any("tonumber" in line and "tonumber" not in "//" for line in decls), \
            "Should declare tonumber function (not as comment)"
        assert any("tostring" in line and "tostring" not in "//" for line in decls), \
            "Should declare tostring function (not as comment)"

    def test_known_and_unknown_global_functions_mixed(self):
        """Test that mixed known/unknown functions generate correct declarations"""
        gen = HeaderGenerator()
        global_functions = {"print", "unknown_func", "tonumber"}

        decls = gen._generate_global_function_declarations(global_functions)

        # Known functions should generate declarations
        assert any("print" in line and "print" not in "//" for line in decls), \
            "Should declare print function"
        assert any("tonumber" in line and "tonumber" not in "//" for line in decls), \
            "Should declare tonumber function"

        # Unknown function should generate comment
        assert any("unknown_func" in line and "//" in line for line in decls), \
            "Should add comment for unknown function"


class TestGenerateHeader:
    """Test generate_header() method"""

    def test_complete_header_with_all_sections(self):
        """Test complete header generation with pragma, structs, and global functions

        Library calls: [io.write, math.sqrt]
        Global functions: {"print"}
        Expected: Full header with pragma once, struct definitions, and global declarations
        """
        gen = HeaderGenerator()
        library_calls = [
            LibraryCall("io", "write", 10),
            LibraryCall("math", "sqrt", 15)
        ]
        global_functions = {"print"}

        header = gen.generate_header(library_calls, global_functions)

        assert "#pragma once" in header, \
            "Header should start with pragma once"
        assert "struct io {" in header, \
            "Header should define struct io"
        assert "struct math {" in header, \
            "Header should define struct math"
        assert "namespace l2c {" in header, \
            "Header should have l2c namespace"
        assert "print" in header, \
            "Header should declare print function"

    def test_header_only_pragma_once_empty_inputs(self):
        """Test header generation with empty inputs

        Library calls: []
        Global functions: set()
        Expected: Pragma once and empty namespace lua2c
        """
        gen = HeaderGenerator()
        library_calls = []
        global_functions = set()

        header = gen.generate_header(library_calls, global_functions)

        assert "#pragma once" in header, \
            "Header should have pragma once"
        assert "namespace l2c {" in header, \
            "Header should have empty namespace l2c"

    def test_header_only_library_calls_no_global(self):
        """Test header with library calls but no global functions

        Library calls: [io.write]
        Global functions: set()
        Expected: Pragma once, struct definitions, and empty namespace lua2c
        """
        gen = HeaderGenerator()
        library_calls = [LibraryCall("io", "write", 10)]
        global_functions = set()

        header = gen.generate_header(library_calls, global_functions)

        assert "#pragma once" in header, \
            "Header should have pragma once"
        assert "struct io {" in header, \
            "Header should define struct io"
        assert "namespace l2c {" in header, \
            "Header should have empty namespace l2c"

    def test_header_only_global_functions_no_library(self):
        """Test header with global functions but no library calls

        Library calls: []
        Global functions: {"print"}
        Expected: Pragma once and global namespace
        Note: Header may contain 'struct State;' forward declaration
        """
        gen = HeaderGenerator()
        library_calls = []
        global_functions = {"print"}

        header = gen.generate_header(library_calls, global_functions)

        assert "#pragma once" in header, \
            "Header should have pragma once"
        assert "namespace l2c {" in header, \
            "Header should have l2c namespace"

    def test_header_formatting_blank_lines(self):
        """Test that header has proper blank line formatting

        Expected: Blank line between sections
        """
        gen = HeaderGenerator()
        library_calls = [LibraryCall("io", "write", 10)]
        global_functions = {"print"}

        header = gen.generate_header(library_calls, global_functions)

        lines = header.split("\n")

        # Find where sections end
        pragma_idx = next(i for i, line in enumerate(lines) if "#pragma once" in line)
        # There should be a blank line after pragma once
        assert lines[pragma_idx + 1] == "", \
            "Should have blank line after pragma once"


class TestTemplateFunctions:
    """Test template function generation for variadic parameters"""

    def test_variadic_function_template(self):
        """Test that variadic functions use template syntax

        Library calls: string.format (variadic)
        Expected: template <typename... Args> and static std::string format(State* state, Args&&... args);
        """
        gen = HeaderGenerator()
        library_calls = [LibraryCall("string", "format", 10)]

        struct_defs = gen._generate_struct_definitions(library_calls)

        assert any("template <typename... Args>" in line for line in struct_defs), \
            "Variadic function should use template syntax"
        assert any("string_format" in line and "Args&&..." in line for line in struct_defs), \
            "Variadic function should have Args&&... parameter"

    def test_non_variadic_function_no_template(self):
        """Test that non-variadic functions don't use template syntax

        Library calls: math.sqrt (non-variadic)
        Expected: static double sqrt(State* state, double /* param */); (no template)
        """
        gen = HeaderGenerator()
        library_calls = [LibraryCall("math", "sqrt", 10)]

        struct_defs = gen._generate_struct_definitions(library_calls)

        assert not any("template <typename... Args>" in line for line in struct_defs), \
            "Non-variadic function should NOT use template syntax"
        assert any("math_sqrt" in line and "State* state" in line for line in struct_defs), \
            "Non-variadic function should have State* state parameter"


class TestTypeConversions:
    """Test TypeKind to C++ type conversions"""

    def test_boolean_type_conversion(self):
        """Test BOOLEAN type conversion to bool

        Library calls: io.write (returns BOOLEAN)
        Expected: return type should be bool
        """
        gen = HeaderGenerator()
        library_calls = [LibraryCall("io", "write", 10)]

        struct_defs = gen._generate_struct_definitions(library_calls)

        # io.write returns BOOLEAN
        assert any("BOOLEAN" in line and "io_write" in line for line in struct_defs), \
            "BOOLEAN return type should stay as BOOLEAN"

    def test_number_type_conversion(self):
        """Test NUMBER type conversion to NUMBER

        Library calls: math.sqrt (returns NUMBER)
        Expected: return type should be NUMBER
        """
        gen = HeaderGenerator()
        library_calls = [LibraryCall("math", "sqrt", 10)]

        struct_defs = gen._generate_struct_definitions(library_calls)

        assert any("NUMBER" in line and "math_sqrt" in line for line in struct_defs), \
            "NUMBER return type should convert to NUMBER"

    def test_string_type_conversion(self):
        """Test STRING type conversion to STRING

        Library calls: string.len (returns NUMBER), io.type (returns STRING)
        Expected: STRING return type should stay as STRING
        """
        gen = HeaderGenerator()
        library_calls = [LibraryCall("io", "type", 10)]

        struct_defs = gen._generate_struct_definitions(library_calls)

        assert any("STRING" in line and "io_type" in line for line in struct_defs), \
            "STRING return type should stay as STRING"

    def test_table_type_conversion(self):
        """Test TABLE type conversion to TABLE

        Library calls: io.open (returns TABLE)
        Expected: return type should be TABLE
        """
        gen = HeaderGenerator()
        library_calls = [LibraryCall("io", "open", 10)]

        struct_defs = gen._generate_struct_definitions(library_calls)

        assert any("TABLE" in line and "io_open" in line for line in struct_defs), \
            "TABLE return type should stay as TABLE"

    def test_function_type_conversion(self):
        """Test FUNCTION type conversion to auto

        Library calls: io.lines (returns FUNCTION)
        Expected: return type should be auto
        """
        gen = HeaderGenerator()
        library_calls = [LibraryCall("io", "lines", 10)]

        struct_defs = gen._generate_struct_definitions(library_calls)

        assert any("auto" in line and "io_lines" in line for line in struct_defs), \
            "FUNCTION return type should convert to auto"


class TestCustomRegistry:
    """Test HeaderGenerator with custom LibraryFunctionRegistry"""

    def test_header_with_custom_registry(self):
        """Test that HeaderGenerator uses provided custom registry

        Create custom registry and pass to HeaderGenerator
        Expected: Should use custom registry for function info
        """
        custom_registry = LibraryFunctionRegistry()
        gen = HeaderGenerator(registry=custom_registry)

        library_calls = [LibraryCall("io", "write", 10)]
        global_functions = {"print"}

        header = gen.generate_header(library_calls, global_functions)

        assert "#pragma once" in header, \
            "Header should generate with custom registry"
        assert "struct io {" in header, \
            "Should use custom registry for library functions"

    def test_default_registry_when_none_provided(self):
        """Test that HeaderGenerator creates default registry when None provided

        Expected: Should create new LibraryFunctionRegistry internally
        """
        gen = HeaderGenerator(registry=None)

        library_calls = [LibraryCall("io", "write", 10)]

        struct_defs = gen._generate_struct_definitions(library_calls)

        assert len(struct_defs) > 0, \
            "Should generate definitions with default registry"
