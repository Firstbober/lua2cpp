"""Tests for arg detection and module_init naming

Tests for:
1. Arg detection logic - identifying when Lua uses 'arg' for varargs
2. Module_init naming - proper naming of module initialization functions
3. Parameter handling - adding TABLE arg parameter when arg is detected

Test Coverage:
- Arg detection in module body
- Module_init function naming format
- Filename sanitization for C identifiers
- Edge cases (shadowing, explicit parameters)
"""

import pytest
import tempfile
from pathlib import Path

try:
    from luaparser import ast
except ImportError:
    pytest.skip("luaparser is required. Install with: pip install luaparser", allow_module_level=True)

from lua2cpp.generators.cpp_emitter import CppEmitter


class TestArgDetection:
    """Test arg detection logic for vararg handling"""

    def test_arg_detected_when_used(self):
        """Test that arg is detected when used in Lua code

        Lua code:
            return #arg

        Expected: Module init function should have TABLE arg parameter
        Expected function signature: simple_module_init(StateType* state, TABLE arg)
        """
        lua_code = "return #arg"
        chunk = ast.parse(lua_code)
        assert chunk is not None

        with tempfile.TemporaryDirectory() as tmpdir:
            lua_file = Path(tmpdir) / 'simple.lua'
            lua_file.write_text(lua_code)

            emitter = CppEmitter()
            cpp_code = emitter.generate_file(chunk, lua_file)

            assert 'TABLE arg' in cpp_code, \
                "Generated code should have TABLE arg parameter when Lua uses arg"
            assert 'simple_module_init(' in cpp_code, \
                "Module init function should be named simple_module_init"

    def test_arg_not_detected_when_unused(self):
        """Test that arg is NOT added when not used in Lua code

        Lua code:
            local x = 5
            return x

        Expected: Module init function should NOT have TABLE arg parameter
        Expected function signature: simple_module_init(StateType* state) only
        """
        lua_code = "local x = 5\nreturn x"
        chunk = ast.parse(lua_code)
        assert chunk is not None

        with tempfile.TemporaryDirectory() as tmpdir:
            lua_file = Path(tmpdir) / 'simple.lua'
            lua_file.write_text(lua_code)

            emitter = CppEmitter()
            cpp_code = emitter.generate_file(chunk, lua_file)

            assert 'TABLE arg' not in cpp_code, \
                "Generated code should NOT have TABLE arg parameter when Lua does not use arg"
            assert 'simple_module_init(' in cpp_code, \
                "Module init function should be named simple_module_init"

    def test_arg_ignored_when_explicit_param(self):
        """Test that arg is ignored when declared as explicit function parameter

        Lua code:
            function foo(arg)
                return arg
            end
            return foo(42)

        Expected: Module init function should NOT have TABLE arg parameter
        Reason: arg is a function parameter, not the global vararg
        """
        lua_code = """
function foo(arg)
    return arg
end
return foo(42)
"""
        chunk = ast.parse(lua_code)
        assert chunk is not None

        with tempfile.TemporaryDirectory() as tmpdir:
            lua_file = Path(tmpdir) / 'foo.lua'
            lua_file.write_text(lua_code)

            emitter = CppEmitter()
            cpp_code = emitter.generate_file(chunk, lua_file)

            assert 'TABLE arg' not in cpp_code, \
                "Generated code should NOT have TABLE arg parameter when arg is a function parameter"
            assert 'foo_module_init(' in cpp_code, \
                "Module init function should be named foo_module_init"

    def test_arg_ignored_when_local_shadowing(self):
        """Test that arg is ignored when shadowed by local variable

        Lua code:
            local arg = 5
            return arg

        Expected: Module init function should NOT have TABLE arg parameter
        Reason: arg is a local variable, not the global vararg
        """
        lua_code = "local arg = 5\nreturn arg"
        chunk = ast.parse(lua_code)
        assert chunk is not None

        with tempfile.TemporaryDirectory() as tmpdir:
            lua_file = Path(tmpdir) / 'simple.lua'
            lua_file.write_text(lua_code)

            emitter = CppEmitter()
            cpp_code = emitter.generate_file(chunk, lua_file)

            assert 'TABLE arg' not in cpp_code, \
                "Generated code should NOT have TABLE arg parameter when arg is a local variable"
            assert 'simple_module_init(' in cpp_code, \
                "Module init function should be named simple_module_init"


class TestModuleInitNaming:
    """Test module_init function naming and filename sanitization"""

    def test_module_init_naming_simple(self):
        """Test module_init naming for simple filename

        Filename: simple.lua
        Expected function name: simple_module_init
        """
        lua_code = "return 42"
        chunk = ast.parse(lua_code)
        assert chunk is not None

        with tempfile.TemporaryDirectory() as tmpdir:
            lua_file = Path(tmpdir) / 'simple.lua'
            lua_file.write_text(lua_code)

            emitter = CppEmitter()
            cpp_code = emitter.generate_file(chunk, lua_file)

            assert 'simple_module_init(' in cpp_code, \
                "Module init function should be named simple_module_init for simple.lua"

    def test_module_init_naming_sanitized(self):
        """Test module_init naming with sanitized special characters

        Filename: my-file.lua
        Expected function name: my_file_module_init (dash converted to underscore)
        """
        lua_code = "return 42"
        chunk = ast.parse(lua_code)
        assert chunk is not None

        with tempfile.TemporaryDirectory() as tmpdir:
            lua_file = Path(tmpdir) / 'my-file.lua'
            lua_file.write_text(lua_code)

            emitter = CppEmitter()
            cpp_code = emitter.generate_file(chunk, lua_file)

            assert 'my_file_module_init(' in cpp_code, \
                "Module init function should sanitize dashes to underscores"

    def test_module_init_naming_extension(self):
        """Test module_init naming strips .lua extension

        Filename: test.lua
        Expected function name: test_module_init (no .lua in function name)
        """
        lua_code = "return 42"
        chunk = ast.parse(lua_code)
        assert chunk is not None

        with tempfile.TemporaryDirectory() as tmpdir:
            lua_file = Path(tmpdir) / 'test.lua'
            lua_file.write_text(lua_code)

            emitter = CppEmitter()
            cpp_code = emitter.generate_file(chunk, lua_file)

            assert 'test_module_init(' in cpp_code, \
                "Module init function should be named test_module_init"
            assert 'test.lua_module_init' not in cpp_code, \
                "Module init function name should not contain .lua extension"

    def test_module_init_no_arg_when_unused(self):
        """Test module_init has no TABLE arg parameter when arg is not used

        Filename: simple.lua
        Lua code: return 42
        Expected: simple_module_init(StateType* state) only, no TABLE arg parameter
        """
        lua_code = "return 42"
        chunk = ast.parse(lua_code)
        assert chunk is not None

        with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False,
                                         prefix='simple_') as f:
            f.write(lua_code)
            f.flush()
            lua_file = Path(f.name)

        try:
            emitter = CppEmitter()
            cpp_code = emitter.generate_file(chunk, lua_file)

            assert 'TABLE arg' not in cpp_code, \
                "Module init function should NOT have TABLE arg parameter when arg is not used"

            assert '_module_init(' in cpp_code, \
                "Module init function should exist"
        finally:
            lua_file.unlink()
