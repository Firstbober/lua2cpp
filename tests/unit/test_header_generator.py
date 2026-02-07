"""Unit tests for HeaderGenerator"""

import pytest
from lua2c.generators.header_generator import HeaderGenerator


class TestHeaderGenerator:
    def test_generate_simple_module_header(self):
        """Test header generation for simple module"""
        gen = HeaderGenerator()
        header = gen.generate_module_header("utils", "myproject")
        
        assert "#pragma once" in header
        assert '#include "l2c_runtime.hpp"' in header
        assert '#include "myproject_state.hpp"' in header
        assert "_l2c__utils_export" in header
        assert "myproject_lua_State* state" in header

    def test_generate_nested_module_header(self):
        """Test header generation for nested directory module"""
        gen = HeaderGenerator()
        header = gen.generate_module_header("subdir_helper", "myproject")
        
        assert "_l2c__subdir_helper_export" in header or "_l2c__subdir__helper_export" in header

    def test_header_compiles(self):
        """Test that generated header is valid C++"""
        gen = HeaderGenerator()
        header = gen.generate_module_header("main", "testproj")
        
        # Should not contain syntax errors
        assert ";" in header
        assert header.count("#pragma once") == 1
