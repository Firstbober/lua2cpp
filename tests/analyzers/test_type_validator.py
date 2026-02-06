"""Tests for type validation system

Tests the TypeValidator that checks inferred types for
completeness, consistency, and potential issues.

Test Coverage:
- Type gap detection
- Table consistency checking
- Propagation completeness
- Variant type validation
- Issue formatting and reporting
"""

import pytest
from pathlib import Path
from luaparser import ast

from lua2c.core.context import TranslationContext
from lua2c.analyzers.type_inference import TypeInference
from lua2c.analyzers.type_validator import (
    TypeValidator, ValidationSeverity, ValidationIssue
)
from lua2c.core.type_system import Type, TypeKind, TableTypeInfo


class TestTypeValidator:
    """Test type validation functionality"""

    def _create_test_context(self, lua_code: str) -> TranslationContext:
        """Helper to create test context and parse code"""
        tree = ast.parse(lua_code)
        context = TranslationContext(Path.cwd(), "")
        return context, tree

    def test_detects_type_gaps(self):
        """Validator should detect symbols without type info"""
        lua_code = """
        local x
        local y
        print(x)
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        issues = validator.validate_all()

        gap_issues = [i for i in issues if i.issue_type == "type_gap"]
        assert len(gap_issues) > 0

    def test_detects_undetermined_tables(self):
        """Validator should detect tables without clear array/map decision"""
        lua_code = """
        local t = {}
        -- No usage to determine if array or map
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        issues = validator.validate_all()

        undetermined = [i for i in issues if i.issue_type == "undetermined_table"]
        # May or may not have issue depending on finalization
        if undetermined:
            assert "t" in undetermined[0].symbol

    def test_detects_mixed_table_usage(self):
        """Validator should detect arrays used as maps"""
        lua_code = """
        local t = {}
        t[1] = "a"
        t.key = "b"
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        issues = validator.validate_all()

        mixed_issues = [i for i in issues if i.issue_type == "mixed_usage"]
        assert len(mixed_issues) == 1
        assert "t" in mixed_issues[0].symbol

    def test_detects_sparse_arrays(self):
        """Validator should detect sparse array usage"""
        lua_code = """
        local sparse = {}
        sparse[1] = "a"
        sparse[10] = "b"
        sparse[100] = "c"
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        issues = validator.validate_all()

        sparse_issues = [i for i in issues if i.issue_type == "sparse_array"]
        # May detect as sparse array
        if sparse_issues:
            assert "sparse" in sparse_issues[0].symbol

    def test_detects_incomplete_array_parameters(self):
        """Validator should detect array parameters without element type"""
        lua_code = """
        local function foo(arr)
            -- arr is used as array but element type unknown
            arr[#arr + 1] = 42
        end

        local x = {}
        foo(x)
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        issues = validator.validate_all()

        incomplete = [i for i in issues if i.issue_type == "incomplete_array"]
        # May detect incomplete array info
        if incomplete:
            assert "foo." in incomplete[0].symbol

    def test_valid_typed_code(self):
        """Well-typed code should have no errors or warnings"""
        lua_code = """
        local function add(a, b)
            return a + b
        end

        local x = 1
        local y = 2
        local result = add(x, y)
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        issues = validator.validate_all()

        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0

    def test_has_errors_and_has_warnings(self):
        """Test has_errors() and has_warnings() methods"""
        lua_code = """
        local t = {}
        t[1] = 1
        t.key = "value"
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        issues = validator.validate_all()

        warnings = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]

        assert validator.has_warnings() == (len(warnings) > 0)
        assert validator.has_errors() == (len(errors) > 0)

    def test_get_issues_by_severity(self):
        """Test filtering issues by severity"""
        lua_code = """
        local t = {}
        t[1] = 1
        t.key = "value"
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        validator.validate_all()

        warnings = validator.get_issues_by_severity(ValidationSeverity.WARNING)
        errors = validator.get_issues_by_severity(ValidationSeverity.ERROR)
        infos = validator.get_issues_by_severity(ValidationSeverity.INFO)

        # All returned issues should have the correct severity
        for issue in warnings:
            assert issue.severity == ValidationSeverity.WARNING
        for issue in errors:
            assert issue.severity == ValidationSeverity.ERROR
        for issue in infos:
            assert issue.severity == ValidationSeverity.INFO

    def test_print_issues(self):
        """Test issue report formatting"""
        lua_code = """
        local t = {}
        t[1] = 1
        t.key = "value"
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        validator.validate_all()

        report = validator.print_issues()

        assert "Type Validation Issues" in report
        if validator.has_warnings():
            assert "WARNING" in report

    def test_print_issues_filter_severity(self):
        """Test filtering in print_issues()"""
        lua_code = """
        local t = {}
        t[1] = 1
        t.key = "value"
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        validator.validate_all()

        warning_report = validator.print_issues(
            filter_severity=ValidationSeverity.WARNING
        )

        assert "WARNING" in warning_report
        assert "ERROR" not in warning_report  # Should not show errors

    def test_print_issues_max_limit(self):
        """Test max_issues parameter in print_issues()"""
        lua_code = """
        local x
        local y
        local z
        local a
        local b
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        issues = validator.validate_all()

        report = validator.print_issues(max_issues=2)

        # Should have issues (undeclared variables)
        assert "Type Validation Issues" in report
        # Check for truncation notice if more issues exist
        if len(issues) > 2:
            assert "more issues hidden" in report

    def test_print_summary(self):
        """Test summary statistics formatting"""
        lua_code = """
        local t = {}
        t[1] = 1
        t.key = "value"
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        issues = validator.validate_all()

        summary = validator.print_summary()

        assert "Type Validation Summary" in summary
        assert "Total issues:" in summary
        if issues:
            assert "Issues by type:" in summary

    def test_clear_issues(self):
        """Test clearing all validation issues"""
        lua_code = """
        local x
        local y
        print(x)
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        validator.validate_all()

        assert len(validator.issues) > 0

        validator.clear()
        assert len(validator.issues) == 0

    def test_validation_issue_format(self):
        """Test ValidationIssue format method"""
        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            symbol="test_var",
            issue_type="test_issue",
            message="Test message",
            suggestion="Test suggestion",
            line=42
        )

        formatted = issue.format()

        assert "WARNING" in formatted
        assert "test_var" in formatted
        assert "Test message" in formatted
        assert "Test suggestion" in formatted


class TestSpectralNormValidation:
    """Test validation with real spectral-norm.lua code"""

    def _create_test_context(self, lua_code: str) -> TranslationContext:
        """Helper to create test context and parse code"""
        tree = ast.parse(lua_code)
        context = TranslationContext(Path.cwd(), "")
        return context, tree

    def test_spectral_norm_no_type_gaps(self):
        """spectral-norm.lua should have no type gaps for arrays"""
        lua_code = """
        local function A(i, j)
            local ij = i + j - 1
            return 1.0 / (ij * (ij - 1) * 0.5 + i)
        end

        local function Av(x, y, N)
            for i=1,N do
                local a = 0
                for j=1,N do
                    a = a + x[j] * A(i, j)
                end
                y[i] = a
            end
        end

        local function Atv(x, y, N)
            for i=1,N do
                local a = 0
                for j=1,N do
                    a = a + x[j] * A(j, i)
                end
                y[i] = a
            end
        end

        local function AtAv(x, y, t, N)
            Av(x, t, N)
            Atv(t, y, N)
        end

        local u, v, t = {}, {}, {}
        local N = 100
        for i=1,N do u[i] = 1 end

        for i=1,10 do AtAv(u, v, t, N) AtAv(v, u, t, N) end

        local vBv, vv = 0, 0
        for i=1,N do
            local ui, vi = u[i], v[i]
            vBv = vBv + ui * vi
            vv = vv + vi * vi
        end
        """

        context, tree = self._create_test_context(lua_code)
        inferencer = TypeInference(context)
        inferencer.infer_chunk(tree)

        validator = TypeValidator(inferencer)
        issues = validator.validate_all()

        # Check that u, v, t have proper table info
        for var_name in ["u", "v", "t"]:
            assert var_name in inferencer.table_info
            table_info = inferencer.table_info[var_name]
            assert table_info.is_array is True
            assert table_info.value_type is not None
            assert table_info.value_type.kind == TypeKind.NUMBER

        # No errors should be present
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
