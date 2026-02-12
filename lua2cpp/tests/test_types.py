"""Unit tests for type system

Tests for TypeKind enum, Type dataclass, and ASTAnnotationStore.
"""

import pytest
from pathlib import Path


class TestTypeKind:
    """Test TypeKind enum"""

    def test_enum_values_exist(self):
        """Test that all required TypeKind values exist"""
        from lua2cpp.core.types import TypeKind

        assert hasattr(TypeKind, 'UNKNOWN')
        assert hasattr(TypeKind, 'STRING')
        assert hasattr(TypeKind, 'NUMBER')
        assert hasattr(TypeKind, 'FUNCTION')
        assert hasattr(TypeKind, 'BOOLEAN')
        assert hasattr(TypeKind, 'TABLE')
        assert hasattr(TypeKind, 'ANY')

    def test_no_nil_type(self):
        """Test that NIL is NOT a separate TypeKind (handled via ANY)"""
        from lua2cpp.core.types import TypeKind

        assert not hasattr(TypeKind, 'NIL')

    def test_no_array_type(self):
        """Test that ARRAY is NOT a separate TypeKind"""
        from lua2cpp.core.types import TypeKind

        assert not hasattr(TypeKind, 'ARRAY')

    def test_enum_values_are_ints(self):
        """Test that TypeKind values are integers"""
        from lua2cpp.core.types import TypeKind

        assert TypeKind.UNKNOWN.value == 0
        assert TypeKind.STRING.value == 1
        assert TypeKind.NUMBER.value == 2
        assert TypeKind.FUNCTION.value == 3
        assert TypeKind.BOOLEAN.value == 4
        assert TypeKind.TABLE.value == 5
        assert TypeKind.ANY.value == 6


class TestType:
    """Test Type dataclass"""

    def test_type_has_required_fields(self):
        """Test that Type has kind, is_constant, subtypes fields"""
        from lua2cpp.core.types import Type, TypeKind

        t = Type(kind=TypeKind.STRING)
        assert hasattr(t, 'kind')
        assert hasattr(t, 'is_constant')
        assert hasattr(t, 'subtypes')

    def test_type_initialization(self):
        """Test Type initialization with defaults"""
        from lua2cpp.core.types import Type, TypeKind

        t = Type(kind=TypeKind.NUMBER)
        assert t.kind == TypeKind.NUMBER
        assert t.is_constant is False
        assert t.subtypes == []

    def test_cpp_type_method_exists(self):
        """Test that Type has cpp_type() method"""
        from lua2cpp.core.types import Type, TypeKind

        t = Type(kind=TypeKind.STRING)
        assert callable(t.cpp_type)

    def test_cpp_type_returns_correct_values(self):
        """Test cpp_type() returns correct C++ type names"""
        from lua2cpp.core.types import Type, TypeKind

        tests = [
            (TypeKind.UNKNOWN, 'auto'),
            (TypeKind.STRING, 'std::string'),
            (TypeKind.NUMBER, 'double'),
            (TypeKind.FUNCTION, 'auto'),
            (TypeKind.BOOLEAN, 'bool'),
            (TypeKind.TABLE, 'TABLE'),
            (TypeKind.ANY, 'ANY'),
        ]

        for kind, expected in tests:
            t = Type(kind=kind)
            if expected == 'ANY':
                assert 'variant' in t.cpp_type().lower()
            else:
                assert t.cpp_type() == expected


class TestASTAnnotationStore:
    """Test ASTAnnotationStore"""

    def test_set_and_get_type(self):
        """Test setting and getting type annotations"""
        from lua2cpp.core.types import ASTAnnotationStore, Type, TypeKind
        from luaparser import astnodes

        node = astnodes.Number(42)
        t = Type(kind=TypeKind.NUMBER)

        ASTAnnotationStore.set_type(node, t)
        retrieved = ASTAnnotationStore.get_type(node)

        assert retrieved is t
        assert retrieved.kind == TypeKind.NUMBER

    def test_set_and_get_annotation(self):
        """Test setting and getting custom annotations"""
        from lua2cpp.core.types import ASTAnnotationStore
        from luaparser import astnodes

        node = astnodes.Name('x')
        ASTAnnotationStore.set_annotation(node, 'custom_key', 'custom_value')
        retrieved = ASTAnnotationStore.get_annotation(node, 'custom_key')

        assert retrieved == 'custom_value'

    def test_has_annotation(self):
        """Test has_annotation returns correct boolean"""
        from lua2cpp.core.types import ASTAnnotationStore
        from luaparser import astnodes

        node = astnodes.Name('y')
        assert not ASTAnnotationStore.has_annotation(node, 'nonexistent')

        ASTAnnotationStore.set_annotation(node, 'test_key', 'test_value')
        assert ASTAnnotationStore.has_annotation(node, 'test_key')

    def test_private_namespace(self):
        """Test that annotations use _l2c_ prefix"""
        from lua2cpp.core.types import ASTAnnotationStore
        from luaparser import astnodes

        node = astnodes.Name('z')

        # Set an annotation
        ASTAnnotationStore.set_annotation(node, 'test', 'value')

        # Verify it uses private namespace
        assert hasattr(node, '_l2c_test')
        assert node._l2c_test == 'value'
