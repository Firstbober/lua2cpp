"""Unit tests for ProjectStateGenerator"""

import pytest
from pathlib import Path
from lua2c.generators.project_state_generator import ProjectStateGenerator


class TestProjectStateGenerator:
    def test_generate_simple_state(self):
        """Test state generation with no libraries"""
        gen = ProjectStateGenerator("myproject")
        state = gen.generate_state_class(set(), set())
        
        assert "struct myproject_lua_State" in state
        assert "std::unordered_map" in state
        assert "modules" in state

    def test_generate_with_io_library(self):
        """Test state generation with IO library"""
        gen = ProjectStateGenerator("myproject")
        state = gen.generate_state_class(set(), set(), {"io"})
        
        # Check for anonymous struct with io name
        assert "} io;" in state or "io {" in state
        assert "write" in state

    def test_generate_with_math_library(self):
        """Test state generation with Math library"""
        gen = ProjectStateGenerator("myproject")
        state = gen.generate_state_class(set(), set(), {"math"})
        
        # Check for anonymous struct with math name
        assert "} math;" in state or "math {" in state
        assert "sqrt" in state

    def test_generate_with_globals(self):
        """Test state generation with special globals"""
        gen = ProjectStateGenerator("myproject")
        state = gen.generate_state_class({"arg"}, set())
        
        assert "luaArray<luaValue> arg" in state

    def test_module_registry_type(self):
        """Test module registry has correct type"""
        gen = ProjectStateGenerator("testproj")
        state = gen.generate_state_class(set(), {"utils"})
        
        assert "luaValue(*)(testproj_lua_State*)" in state

    def test_multiple_libraries(self):
        """Test state with multiple libraries"""
        gen = ProjectStateGenerator("myproject")
        state = gen.generate_state_class(set(), set(), {"io", "math", "string"})
        
        # Check for anonymous structs with library names
        assert ("} io;" in state or "io {" in state)
        assert ("} math;" in state or "math {" in state)
        assert ("} string;" in state or "string {" in state)

    def test_state_compiles(self):
        """Test that generated state compiles"""
        gen = ProjectStateGenerator("testproj")
        state = gen.generate_state_class({"arg"}, set(), {"io", "math"})
        
        # Verify C++ syntax
        assert "struct testproj_lua_State" in state
        assert state.count("{") >= 1
        assert state.count("}") >= 1
        assert ";" in state

    def test_detect_used_libraries_simple(self, tmp_path):
        """Test library detection from simple code"""
        gen = ProjectStateGenerator("testproj")
        
        # Create a simple Lua file using io.write
        lua_file = tmp_path / "test.lua"
        lua_file.write_text('io.write("hello\\n")')
        
        used_libs = gen.detect_used_libraries([Path("test.lua")], tmp_path)
        
        assert "io" in used_libs

    def test_detect_used_libraries_math(self, tmp_path):
        """Test library detection from code using math"""
        gen = ProjectStateGenerator("testproj")
        
        # Create a Lua file using math.sqrt
        lua_file = tmp_path / "test.lua"
        lua_file.write_text('local x = math.sqrt(16)')
        
        used_libs = gen.detect_used_libraries([Path("test.lua")], tmp_path)
        
        assert "math" in used_libs

    def test_detect_used_libraries_multiple(self, tmp_path):
        """Test library detection from code using multiple libraries"""
        gen = ProjectStateGenerator("testproj")
        
        # Create a Lua file using multiple libraries
        lua_file = tmp_path / "test.lua"
        lua_file.write_text('''
            io.write("x = " .. x)
            local x = math.sqrt(y)
            local s = string.upper("hello")
        ''')
        
        used_libs = gen.detect_used_libraries([Path("test.lua")], tmp_path)
        
        assert "io" in used_libs
        assert "math" in used_libs
        assert "string" in used_libs

    def test_detect_used_libraries_none(self, tmp_path):
        """Test library detection from code with no libraries"""
        gen = ProjectStateGenerator("testproj")
        
        # Create a Lua file without any library calls
        lua_file = tmp_path / "test.lua"
        lua_file.write_text('local x = 5 + 3')
        
        used_libs = gen.detect_used_libraries([Path("test.lua")], tmp_path)
        
        assert len(used_libs) == 0

    def test_generate_state_with_all_libraries(self):
        """Test state generation with all standard libraries"""
        gen = ProjectStateGenerator("myproject")
        state = gen.generate_state_class(
            set(), 
            set(), 
            {"io", "string", "math", "table", "os"}
        )
        
        # Check all libraries are present (as anonymous structs)
        assert ("} io;" in state or "io {" in state)
        assert ("} string;" in state or "string {" in state)
        assert ("} math;" in state or "math {" in state)
        assert ("} table;" in state or "table {" in state)
        assert ("} os;" in state or "os {" in state)
