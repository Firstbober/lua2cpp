"""Tests for string pool"""

import pytest
from lua2c.generators.string_pool import StringPool


class TestStringPool:
    """Test suite for StringPool"""

    def test_initial_state(self):
        """Test initial empty state"""
        pool = StringPool()
        assert pool.size() == 0
        assert pool.all_strings() == []

    def test_add_single_string(self):
        """Test adding a single string"""
        pool = StringPool()
        index = pool.add("hello")
        assert index == 0
        assert pool.size() == 1
        assert pool.get(0) == "hello"

    def test_add_multiple_strings(self):
        """Test adding multiple distinct strings"""
        pool = StringPool()
        idx1 = pool.add("hello")
        idx2 = pool.add("world")
        idx3 = pool.add("test")

        assert idx1 == 0
        assert idx2 == 1
        assert idx3 == 2
        assert pool.size() == 3
        assert pool.all_strings() == ["hello", "world", "test"]

    def test_deduplicate_strings(self):
        """Test that duplicate strings return same index"""
        pool = StringPool()
        idx1 = pool.add("hello")
        idx2 = pool.add("world")
        idx3 = pool.add("hello")  # Duplicate

        assert idx1 == 0
        assert idx2 == 1
        assert idx3 == 0  # Same as idx1
        assert pool.size() == 2

    def test_get_valid_index(self):
        """Test getting string by valid index"""
        pool = StringPool()
        pool.add("test")
        assert pool.get(0) == "test"

    def test_get_invalid_index_negative(self):
        """Test getting string with negative index"""
        pool = StringPool()
        pool.add("test")
        with pytest.raises(IndexError):
            pool.get(-1)

    def test_get_invalid_index_out_of_bounds(self):
        """Test getting string with out-of-bounds index"""
        pool = StringPool()
        pool.add("test")
        with pytest.raises(IndexError):
            pool.get(1)

    def test_index_found(self):
        """Test getting index of existing string"""
        pool = StringPool()
        pool.add("hello")
        pool.add("world")
        assert pool.index("hello") == 0
        assert pool.index("world") == 1

    def test_index_not_found(self):
        """Test getting index of non-existent string"""
        pool = StringPool()
        pool.add("hello")
        assert pool.index("world") is None

    def test_contains_true(self):
        """Test contains returns True for existing string"""
        pool = StringPool()
        pool.add("hello")
        assert pool.contains("hello") is True

    def test_contains_false(self):
        """Test contains returns False for non-existent string"""
        pool = StringPool()
        pool.add("hello")
        assert pool.contains("world") is False

    def test_all_strings_returns_copy(self):
        """Test that all_strings returns a copy, not reference"""
        pool = StringPool()
        pool.add("hello")
        strings = pool.all_strings()
        strings.append("modified")
        assert pool.size() == 1
        assert pool.all_strings() == ["hello"]

    def test_clear(self):
        """Test clearing the string pool"""
        pool = StringPool()
        pool.add("hello")
        pool.add("world")
        assert pool.size() == 2

        pool.clear()
        assert pool.size() == 0
        assert pool.all_strings() == []

    def test_empty_string(self):
        """Test handling empty string"""
        pool = StringPool()
        index = pool.add("")
        assert index == 0
        assert pool.get(0) == ""
        assert pool.contains("")

    def test_string_with_quotes(self):
        """Test strings with quotes"""
        pool = StringPool()
        idx1 = pool.add('hello "world"')
        idx2 = pool.add("hello 'world'")
        assert idx1 == 0
        assert idx2 == 1
        assert pool.get(0) == 'hello "world"'
        assert pool.get(1) == "hello 'world'"

    def test_unicode_strings(self):
        """Test unicode strings"""
        pool = StringPool()
        idx1 = pool.add("你好")
        idx2 = pool.add("🎉")
        assert idx1 == 0
        assert idx2 == 1
        assert pool.get(0) == "你好"
        assert pool.get(1) == "🎉"

    def test_large_pool(self):
        """Test with many strings"""
        pool = StringPool()
        for i in range(1000):
            pool.add(f"string_{i}")

        assert pool.size() == 1000
        assert pool.get(500) == "string_500"
        assert pool.index("string_999") == 999
