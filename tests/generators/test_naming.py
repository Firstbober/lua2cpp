"""Tests for naming scheme"""

import pytest
from lua2c.generators.naming import NamingScheme


class TestNamingScheme:
    """Test suite for NamingScheme"""

    def test_sanitize_path_empty(self):
        """Test sanitizing empty path"""
        result = NamingScheme.sanitize_path("")
        assert result == ""

    def test_sanitize_path_simple(self):
        """Test sanitizing simple path"""
        result = NamingScheme.sanitize_path("core/utils")
        assert result == "__core__utils"

    def test_sanitize_path_with_dashes(self):
        """Test sanitizing path with dashes"""
        result = NamingScheme.sanitize_path("src-core/utils")
        assert result == "__src_core__utils"

    def test_sanitize_path_multiple_separators(self):
        """Test sanitizing path with multiple consecutive separators"""
        result = NamingScheme.sanitize_path("a//b___c")
        assert result == "__a__b__c"

    def test_module_export_name_simple(self):
        """Test module export name generation"""
        result = NamingScheme.module_export_name("core/utils")
        assert result == "_l2c__core__utils_export"

    def test_module_export_name_nested(self):
        """Test module export name with nested path"""
        result = NamingScheme.module_export_name("src/core/utils")
        assert result == "_l2c__src__core__utils_export"

    def test_module_export_name_root(self):
        """Test module export name at root"""
        result = NamingScheme.module_export_name("main")
        assert result == "_l2c__main_export"

    def test_function_name_simple(self):
        """Test function name generation"""
        result = NamingScheme.function_name("core/utils", "add")
        assert result == "_l2c__core__utils_add"

    def test_function_name_with_dashes(self):
        """Test function name with dashes"""
        result = NamingScheme.function_name("core/utils", "add-numbers")
        assert result == "_l2c__core__utils_add_numbers"

    def test_function_name_nested(self):
        """Test function name with nested path"""
        result = NamingScheme.function_name("src/core/utils", "initialize")
        assert result == "_l2c__src__core__utils_initialize"

    def test_variable_name_no_scope(self):
        """Test variable name without scope"""
        result = NamingScheme.variable_name("", "x")
        assert result == "x"

    def test_variable_name_with_scope(self):
        """Test variable name with scope"""
        result = NamingScheme.variable_name("function", "count")
        assert result == "_l2c__function_count"

    def test_string_literal_name(self):
        """Test string literal name generation"""
        result = NamingScheme.string_literal_name(42)
        assert result == "_l2c_string_42"

    def test_string_literal_name_zero(self):
        """Test string literal name with zero index"""
        result = NamingScheme.string_literal_name(0)
        assert result == "_l2c_string_0"

    def test_is_valid_identifier_valid(self):
        """Test valid identifiers"""
        assert NamingScheme.is_valid_identifier("x")
        assert NamingScheme.is_valid_identifier("_x")
        assert NamingScheme.is_valid_identifier("x1")
        assert NamingScheme.is_valid_identifier("_123")
        assert NamingScheme.is_valid_identifier("my_var_123")

    def test_is_valid_identifier_invalid(self):
        """Test invalid identifiers"""
        assert not NamingScheme.is_valid_identifier("")
        assert not NamingScheme.is_valid_identifier("123abc")
        assert not NamingScheme.is_valid_identifier("x-y")
        assert not NamingScheme.is_valid_identifier("x.y")
        assert not NamingScheme.is_valid_identifier("x y")
