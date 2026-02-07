"""Test suite for main generator

Tests MainGenerator class for generating main.cpp in multi-file projects.
"""

import pytest
from pathlib import Path
from lua2c.generators.main_generator import MainGenerator


class TestMainGenerator:
    """Test main.cpp generation for multi-file projects"""

    @pytest.fixture
    def main_gen(self):
        """Create MainGenerator instance"""
        return MainGenerator()

    # ============================================================================
    # Test includes generation
    # ============================================================================

    def test_generate_includes_basic(self, main_gen):
        """Test basic include generation"""
        lines = main_gen._generate_includes("myproject")
        code = "\n".join(lines)
        assert '#include "l2c_runtime.hpp"' in code
        assert '#include "myproject_state.hpp"' in code

    def test_generate_includes_project_name(self, main_gen):
        """Test include with custom project name"""
        lines = main_gen._generate_includes("spectral_norm")
        code = "\n".join(lines)
        assert '#include "spectral_norm_state.hpp"' in code

    def test_generate_includes_empty_string(self, main_gen):
        """Test include with edge case project name"""
        lines = main_gen._generate_includes("test123")
        code = "\n".join(lines)
        assert '#include "test123_state.hpp"' in code

    # ============================================================================
    # Test forward declarations
    # ============================================================================

    def test_generate_forward_declarations_single_module(self, main_gen):
        """Test forward declarations with single module"""
        dependency_order = ["main"]
        lines = main_gen._generate_forward_declarations("myproject", dependency_order)
        code = "\n".join(lines)
        assert "luaValue _l2c__main_export(myproject_lua_State* state);" in code
        assert "// Forward declarations for all modules" in code

    def test_generate_forward_declarations_multiple_modules(self, main_gen):
        """Test forward declarations with multiple modules"""
        dependency_order = ["helper", "utils", "config", "main"]
        lines = main_gen._generate_forward_declarations("myproject", dependency_order)
        code = "\n".join(lines)
        assert "luaValue _l2c__helper_export(myproject_lua_State* state);" in code
        assert "luaValue _l2c__utils_export(myproject_lua_State* state);" in code
        assert "luaValue _l2c__config_export(myproject_lua_State* state);" in code
        assert "luaValue _l2c__main_export(myproject_lua_State* state);" in code

    def test_generate_forward_declarations_nested_module(self, main_gen):
        """Test forward declarations with nested module"""
        dependency_order = ["subdir_helper", "main"]
        lines = main_gen._generate_forward_declarations("myproject", dependency_order)
        code = "\n".join(lines)
        assert "luaValue _l2c__subdir_helper_export(myproject_lua_State* state);" in code

    def test_generate_forward_declarations_empty_order(self, main_gen):
        """Test forward declarations with empty dependency order"""
        dependency_order = []
        lines = main_gen._generate_forward_declarations("myproject", dependency_order)
        code = "\n".join(lines)
        assert "// Forward declarations for all modules" in code
        # Should have no module declarations

    # ============================================================================
    # Test arg initialization
    # ============================================================================

    def test_generate_arg_initialization_basic(self, main_gen):
        """Test basic arg initialization (1-based indexing)"""
        lines = main_gen._generate_arg_initialization()
        code = "\n".join(lines)
        assert "// Set command line arguments" in code
        assert "state.arg = luaArray<luaValue>{{}};" in code
        assert "for (int i = 1; i < argc; ++i)" in code
        assert "state.arg.set(i - 1, luaValue(argv[i]));" in code

    def test_generate_arg_initialization_one_based_indexing(self, main_gen):
        """Verify 1-based indexing (skip argv[0])"""
        lines = main_gen._generate_arg_initialization()
        code = "\n".join(lines)
        # Should start at i=1, skip argv[0]
        assert "i = 1" in code
        assert "argv[i]" in code
        # Should store at i-1 (0-based C array)
        assert "i - 1" in code

    # ============================================================================
    # Test library initialization
    # ============================================================================

    def test_generate_library_initialization_io(self, main_gen):
        """Test IO library initialization"""
        used_libraries = {"io"}
        lines = main_gen._generate_library_initialization(used_libraries)
        code = "\n".join(lines)
        assert "// Initialize library function pointers" in code
        assert "state.io.write = &l2c::io_write;" in code
        assert "state.io.read = &l2c::io_read;" in code
        assert "state.io.flush = &l2c::io_flush;" in code
        # Should not have other libraries
        assert "state.math" not in code
        assert "state.string" not in code

    def test_generate_library_initialization_math(self, main_gen):
        """Test math library initialization"""
        used_libraries = {"math"}
        lines = main_gen._generate_library_initialization(used_libraries)
        code = "\n".join(lines)
        assert "state.math.sqrt = &l2c::math_sqrt;" in code
        assert "state.math.abs = &l2c::math_abs;" in code
        assert "state.math.sin = &l2c::math_sin;" in code
        assert "state.math.cos = &l2c::math_cos;" in code
        assert "state.math.random = &l2c::math_random;" in code
        assert "state.io" not in code

    def test_generate_library_initialization_string(self, main_gen):
        """Test string library initialization"""
        used_libraries = {"string"}
        lines = main_gen._generate_library_initialization(used_libraries)
        code = "\n".join(lines)
        assert "state.string.format = &l2c::string_format;" in code
        assert "state.string.len = &l2c::string_len;" in code
        assert "state.string.sub = &l2c::string_sub;" in code
        assert "state.string.upper = &l2c::string_upper;" in code
        assert "state.string.lower = &l2c::string_lower;" in code
        assert "state.io" not in code
        assert "state.math" not in code

    def test_generate_library_initialization_table(self, main_gen):
        """Test table library initialization"""
        used_libraries = {"table"}
        lines = main_gen._generate_library_initialization(used_libraries)
        code = "\n".join(lines)
        assert "state.table.unpack = &l2c::table_unpack;" in code

    def test_generate_library_initialization_os(self, main_gen):
        """Test OS library initialization"""
        used_libraries = {"os"}
        lines = main_gen._generate_library_initialization(used_libraries)
        code = "\n".join(lines)
        assert "state.os.clock = &l2c::os_clock;" in code
        assert "state.os.time = &l2c::os_time;" in code
        assert "state.os.date = &l2c::os_date;" in code

    def test_generate_library_initialization_multiple(self, main_gen):
        """Test multiple libraries initialization"""
        used_libraries = {"io", "math", "string"}
        lines = main_gen._generate_library_initialization(used_libraries)
        code = "\n".join(lines)
        # Should have all three libraries
        assert "state.io.write = &l2c::io_write;" in code
        assert "state.math.sqrt = &l2c::math_sqrt;" in code
        assert "state.string.format = &l2c::string_format;" in code
        # Should be sorted alphabetically
        io_pos = code.find("state.io")
        math_pos = code.find("state.math")
        string_pos = code.find("state.string")
        assert io_pos < math_pos < string_pos

    def test_generate_library_initialization_standalone_functions(self, main_gen):
        """Test standalone function initialization (print, tonumber)"""
        used_libraries = set()
        lines = main_gen._generate_library_initialization(used_libraries)
        code = "\n".join(lines)
        # Standalone functions should always be initialized
        assert "state.print = &l2c::print;" in code
        assert "state.tonumber = &l2c::tonumber;" in code

    def test_generate_library_initialization_no_libraries(self, main_gen):
        """Test with no library modules used"""
        used_libraries = set()
        lines = main_gen._generate_library_initialization(used_libraries)
        code = "\n".join(lines)
        # Should still have standalone functions
        assert "state.print = &l2c::print;" in code
        assert "state.tonumber = &l2c::tonumber;" in code
        # Should not have any library modules
        assert "state.io" not in code
        assert "state.math" not in code
        assert "state.string" not in code
        assert "state.table" not in code
        assert "state.os" not in code

    # ============================================================================
    # Test module registration
    # ============================================================================

    def test_generate_module_registration_single(self, main_gen):
        """Test module registration with single module"""
        dependency_order = ["main"]
        lines = main_gen._generate_module_registration("myproject", dependency_order)
        code = "\n".join(lines)
        assert "// Initialize modules (in dependency order: main)" in code
        assert 'state.modules["main"] = &_l2c__main_export;' in code

    def test_generate_module_registration_multiple(self, main_gen):
        """Test module registration with multiple modules"""
        dependency_order = ["helper", "utils", "main"]
        lines = main_gen._generate_module_registration("myproject", dependency_order)
        code = "\n".join(lines)
        assert "// Initialize modules (in dependency order: helper → utils → main)" in code
        assert 'state.modules["helper"] = &_l2c__helper_export;' in code
        assert 'state.modules["utils"] = &_l2c__utils_export;' in code
        assert 'state.modules["main"] = &_l2c__main_export;' in code

    def test_generate_module_registration_order_preserved(self, main_gen):
        """Verify dependency order is preserved in registration"""
        dependency_order = ["base", "middle", "top"]
        lines = main_gen._generate_module_registration("myproject", dependency_order)
        code = "\n".join(lines)

        # Check positions in code
        base_pos = code.find('state.modules["base"]')
        middle_pos = code.find('state.modules["middle"]')
        top_pos = code.find('state.modules["top"]')

        assert base_pos < middle_pos < top_pos

    def test_generate_module_registration_nested_module(self, main_gen):
        """Test registration with nested module name"""
        dependency_order = ["subdir_helper", "main"]
        lines = main_gen._generate_module_registration("myproject", dependency_order)
        code = "\n".join(lines)
        assert 'state.modules["subdir_helper"] = &_l2c__subdir_helper_export;' in code

    def test_generate_module_registration_empty(self, main_gen):
        """Test with empty dependency order"""
        dependency_order = []
        lines = main_gen._generate_module_registration("myproject", dependency_order)
        code = "\n".join(lines)
        assert "// Initialize modules" in code
        # Should not have any registrations

    # ============================================================================
    # Test main entry point generation
    # ============================================================================

    def test_generate_main_entry_basic(self, main_gen):
        """Test basic main entry point generation"""
        lines = main_gen._generate_main_entry("myproject", "main")
        code = "\n".join(lines)
        assert "// Call main module entry point" in code
        assert "luaValue result = _l2c__main_export(&state);" in code
        assert "return 0;" in code
        assert code.endswith("}")

    def test_generate_main_entry_custom_main_module(self, main_gen):
        """Test with custom main module name"""
        lines = main_gen._generate_main_entry("myproject", "app")
        code = "\n".join(lines)
        assert "luaValue result = _l2c__app_export(&state);" in code

    def test_generate_main_entry_nested_main(self, main_gen):
        """Test with nested main module"""
        lines = main_gen._generate_main_entry("myproject", "src_main")
        code = "\n".join(lines)
        assert "luaValue result = _l2c__src_main_export(&state);" in code

    # ============================================================================
    # Test main module name extraction
    # ============================================================================

    def test_extract_main_module_name_simple(self, main_gen):
        """Test extracting module name from simple path"""
        path = Path("/project/main.lua")
        name = main_gen._extract_main_module_name(path)
        assert name == "main"

    def test_extract_main_module_name_with_directory(self, main_gen):
        """Test extracting module name with directory"""
        path = Path("/project/src/app.lua")
        name = main_gen._extract_main_module_name(path)
        assert name == "app"

    def test_extract_main_module_name_absolute_path(self, main_gen):
        """Test extracting from absolute path"""
        path = Path("/home/user/projects/myproject/main.lua")
        name = main_gen._extract_main_module_name(path)
        assert name == "main"

    def test_extract_main_module_name_relative_path(self, main_gen):
        """Test extracting from relative path"""
        path = Path("tests/main.lua")
        name = main_gen._extract_main_module_name(path)
        assert name == "main"

    # ============================================================================
    # Test used libraries detection from globals
    # ============================================================================

    def test_detect_used_libraries_from_globals_io(self, main_gen):
        """Detect IO library from globals"""
        globals = {"io", "arg"}
        used_libs = main_gen._detect_used_libraries_from_globals(globals)
        assert "io" in used_libs

    def test_detect_used_libraries_from_globals_math(self, main_gen):
        """Detect math library from globals"""
        globals = {"math", "arg"}
        used_libs = main_gen._detect_used_libraries_from_globals(globals)
        assert "math" in used_libs

    def test_detect_used_libraries_from_globals_function_access(self, main_gen):
        """Detect library from function access (e.g., 'io.write' in globals)"""
        globals = {"io.write", "math.sqrt", "arg"}
        used_libs = main_gen._detect_used_libraries_from_globals(globals)
        assert "io" in used_libs
        assert "math" in used_libs

    def test_detect_used_libraries_from_globals_multiple(self, main_gen):
        """Detect multiple libraries from globals"""
        globals = {"io", "math", "string", "arg"}
        used_libs = main_gen._detect_used_libraries_from_globals(globals)
        assert used_libs == {"io", "math", "string"}

    def test_detect_used_libraries_from_globals_empty(self, main_gen):
        """Detect with empty globals"""
        globals = set()
        used_libs = main_gen._detect_used_libraries_from_globals(globals)
        assert used_libs == set()

    def test_detect_used_libraries_from_globals_only_arg(self, main_gen):
        """Detect with only arg (no library modules)"""
        globals = {"arg"}
        used_libs = main_gen._detect_used_libraries_from_globals(globals)
        assert used_libs == set()

    # ============================================================================
    # Test complete main file generation
    # ============================================================================

    def test_complete_main_file_basic(self, main_gen):
        """Test full main.cpp generation with basic setup"""
        main_file = Path("/project/main.lua")
        globals = {"arg"}
        dependency_order = ["main"]
        used_libraries = {"print"}

        code = main_gen.generate_main_file(
            "myproject", main_file, globals, dependency_order, used_libraries
        )

        # Verify structure
        assert '#include "l2c_runtime.hpp"' in code
        assert '#include "myproject_state.hpp"' in code
        assert "int main(int argc, char* argv[]) {" in code
        assert "return 0;" in code

    def test_complete_main_file_with_multiple_modules(self, main_gen):
        """Test with multiple modules in dependency order"""
        main_file = Path("/project/main.lua")
        globals = {"arg"}
        dependency_order = ["helper", "utils", "main"]
        used_libraries = {"io", "math", "print"}

        code = main_gen.generate_main_file(
            "myproject", main_file, globals, dependency_order, used_libraries
        )

        # Verify forward declarations
        assert "luaValue _l2c__helper_export(myproject_lua_State* state);" in code
        assert "luaValue _l2c__utils_export(myproject_lua_State* state);" in code
        assert "luaValue _l2c__main_export(myproject_lua_State* state);" in code

        # Verify arg initialization
        assert "state.arg = luaArray<luaValue>{{}};" in code
        assert "for (int i = 1; i < argc; ++i)" in code

        # Verify library initialization
        assert "state.io.write = &l2c::io_write;" in code
        assert "state.math.sqrt = &l2c::math_sqrt;" in code
        assert "state.print = &l2c::print;" in code

        # Verify module registration
        assert 'state.modules["helper"] = &_l2c__helper_export;' in code
        assert 'state.modules["utils"] = &_l2c__utils_export;' in code
        assert 'state.modules["main"] = &_l2c__main_export;' in code

        # Verify main entry call
        assert "luaValue result = _l2c__main_export(&state);" in code

    def test_complete_main_file_with_nested_modules(self, main_gen):
        """Test with nested module names"""
        main_file = Path("/project/main.lua")
        globals = {"arg"}
        dependency_order = ["subdir_helper", "src_utils", "main"]
        used_libraries = {"print"}

        code = main_gen.generate_main_file(
            "myproject", main_file, globals, dependency_order, used_libraries
        )

        assert "luaValue _l2c__subdir_helper_export(myproject_lua_State* state);" in code
        assert "luaValue _l2c__src_utils_export(myproject_lua_State* state);" in code
        assert 'state.modules["subdir_helper"] = &_l2c__subdir_helper_export;' in code
        assert 'state.modules["src_utils"] = &_l2c__src_utils_export;' in code

    def test_complete_main_file_without_used_libraries_param(self, main_gen):
        """Test without used_libraries parameter (fallback detection)"""
        main_file = Path("/project/main.lua")
        globals = {"arg", "io", "math"}
        dependency_order = ["main"]

        code = main_gen.generate_main_file("myproject", main_file, globals, dependency_order)

        # Should detect io and math from globals
        assert "state.io.write = &l2c::io_write;" in code
        assert "state.math.sqrt = &l2c::math_sqrt;" in code

    def test_complete_main_file_with_all_libraries(self, main_gen):
        """Test with all library modules used"""
        main_file = Path("/project/main.lua")
        globals = {"arg"}
        dependency_order = ["main"]
        used_libraries = {"io", "math", "string", "table", "os"}

        code = main_gen.generate_main_file(
            "myproject", main_file, globals, dependency_order, used_libraries
        )

        # Verify all libraries initialized
        assert "state.io.write = &l2c::io_write;" in code
        assert "state.math.sqrt = &l2c::math_sqrt;" in code
        assert "state.string.format = &l2c::string_format;" in code
        assert "state.table.unpack = &l2c::table_unpack;" in code
        assert "state.os.clock = &l2c::os_clock;" in code

    def test_complete_main_file_project_name(self, main_gen):
        """Test with custom project name"""
        main_file = Path("/project/app.lua")
        globals = {"arg"}
        dependency_order = ["app"]
        used_libraries = {"print"}

        code = main_gen.generate_main_file(
            "spectral_norm", main_file, globals, dependency_order, used_libraries
        )

        assert '#include "spectral_norm_state.hpp"' in code
        assert "spectral_norm_lua_State state;" in code
        assert "luaValue _l2c__app_export(spectral_norm_lua_State* state);" in code
        assert 'state.modules["app"] = &_l2c__app_export;' in code

    def test_complete_main_file_comment_order_preserved(self, main_gen):
        """Verify dependency order in comment matches registration order"""
        main_file = Path("/project/main.lua")
        globals = {"arg"}
        dependency_order = ["z", "y", "x"]
        used_libraries = {"print"}

        code = main_gen.generate_main_file(
            "myproject", main_file, globals, dependency_order, used_libraries
        )

        # Check comment
        assert "// Initialize modules (in dependency order: z → y → x)" in code
        # Check actual registration order
        z_pos = code.find('state.modules["z"]')
        y_pos = code.find('state.modules["y"]')
        x_pos = code.find('state.modules["x"]')
        assert z_pos < y_pos < x_pos

    # ============================================================================
    # Edge cases
    # ============================================================================

    def test_edge_case_empty_dependency_order(self, main_gen):
        """Test with no modules"""
        main_file = Path("/project/main.lua")
        globals = {"arg"}
        dependency_order = []
        used_libraries = {"print"}

        code = main_gen.generate_main_file(
            "myproject", main_file, globals, dependency_order, used_libraries
        )

        # Should still generate valid code
        assert '#include "l2c_runtime.hpp"' in code
        assert "int main(int argc, char* argv[]) {" in code
        # Should not have any module registrations
        assert "state.modules[" not in code

    def test_edge_case_no_libraries_used(self, main_gen):
        """Test with no libraries (only arg global)"""
        main_file = Path("/project/main.lua")
        globals = {"arg"}
        dependency_order = ["main"]
        used_libraries = set()

        code = main_gen.generate_main_file(
            "myproject", main_file, globals, dependency_order, used_libraries
        )

        # Should still have standalone functions
        assert "state.print = &l2c::print;" in code
        assert "state.tonumber = &l2c::tonumber;" in code
        # Should not have any library modules
        assert "state.io" not in code
        assert "state.math" not in code

    def test_edge_case_module_name_with_special_chars(self, main_gen):
        """Test with module names containing special characters"""
        main_file = Path("/project/my-module_main.lua")
        globals = {"arg"}
        dependency_order = ["my-module_main"]
        used_libraries = {"print"}

        code = main_gen.generate_main_file(
            "myproject", main_file, globals, dependency_order, used_libraries
        )

        # Module name should be sanitized (dashes to underscores)
        assert "luaValue _l2c__my_module_main_export" in code
        assert 'state.modules["my-module_main"]' in code

    def test_edge_case_large_dependency_chain(self, main_gen):
        """Test with large number of modules"""
        main_file = Path("/project/main.lua")
        globals = {"arg"}
        dependency_order = [f"module{i}" for i in range(20)]
        used_libraries = {"io", "print"}

        code = main_gen.generate_main_file(
            "myproject", main_file, globals, dependency_order, used_libraries
        )

        # Verify all modules declared
        assert "luaValue _l2c__module0_export" in code
        assert "luaValue _l2c__module19_export" in code

        # Verify all modules registered
        assert 'state.modules["module0"]' in code
        assert 'state.modules["module19"]' in code

    def test_edge_case_project_name_with_numbers(self, main_gen):
        """Test with project name containing numbers"""
        main_file = Path("/project/main.lua")
        globals = {"arg"}
        dependency_order = ["main"]
        used_libraries = {"print"}

        code = main_gen.generate_main_file(
            "project2024", main_file, globals, dependency_order, used_libraries
        )

        assert '#include "project2024_state.hpp"' in code
        assert "project2024_lua_State state;" in code

    def test_edge_case_main_module_not_first_in_order(self, main_gen):
        """Test when main module is not first in dependency order"""
        main_file = Path("/project/main.lua")
        globals = {"arg"}
        dependency_order = ["helper", "utils", "config", "main"]
        used_libraries = {"print"}

        code = main_gen.generate_main_file(
            "myproject", main_file, globals, dependency_order, used_libraries
        )

        # All modules should be registered in order
        assert 'state.modules["helper"]' in code
        assert 'state.modules["utils"]' in code
        assert 'state.modules["config"]' in code
        assert 'state.modules["main"]' in code

        # But main should still be called directly
        assert "luaValue result = _l2c__main_export(&state);" in code
