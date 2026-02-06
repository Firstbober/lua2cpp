"""Type validator for Lua2C transpiler

Validates inferred types for completeness, consistency, and potential issues.
Provides detailed reporting and suggestions for improving type inference.

Design Principles:
- Comprehensive validation of type system state
- Clear severity levels (INFO, WARNING, ERROR)
- Actionable suggestions for each issue
- Formatted output for easy review
"""

from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

if __name__.startswith('lua2c.analyzers'):
    from lua2c.core.type_system import Type, TypeKind, TableTypeInfo
else:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from lua2c.core.type_system import Type, TypeKind, TableTypeInfo


class ValidationSeverity(Enum):
    """Severity level of validation issue"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    """A validation issue found during type checking

    Encapsulates information about a type-related issue detected
    during validation, including severity and actionable suggestions.

    Attributes:
        severity: Severity level (INFO, WARNING, or ERROR)
        symbol: Symbol name (optional for non-symbol-specific issues)
        issue_type: Category/type of issue
        message: Human-readable description
        suggestion: Actionable suggestion (optional)
        line: Source line number (optional)
    """
    severity: ValidationSeverity
    symbol: Optional[str]
    issue_type: str
    message: str
    suggestion: Optional[str] = None
    line: Optional[int] = None

    def format(self) -> str:
        """Format validation issue for display

        Returns:
            Formatted string representation
        """
        symbol_part = f"[{self.symbol}] " if self.symbol else ""
        result = f"  {self.severity.value.upper()}: {symbol_part}{self.message}"
        if self.suggestion:
            result += f"\n    → {self.suggestion}"
        return result


class TypeValidator:
    """Validates inferred types for completeness and consistency

    Performs comprehensive validation of the type inference results,
    checking for type gaps, inconsistencies, and potential issues.

    Usage Example:
        validator = TypeValidator(type_inferencer)
        issues = validator.validate_all()

        if issues:
            print(validator.print_issues())
            print(validator.print_summary())
    """

    def __init__(self, inferencer) -> None:
        """Initialize type validator

        Args:
            inferencer: TypeInference instance with completed inference
        """
        self.inferencer = inferencer
        self.issues: List[ValidationIssue] = []

    def validate_all(self) -> List[ValidationIssue]:
        """Run all validation checks

        Executes all validation methods and collects all issues found.

        Returns:
            List of ValidationIssue objects (may be empty)
        """
        self.issues.clear()

        # Run all validation checks
        self._check_type_gaps()
        self._check_table_consistency()
        self._check_propagation_completeness()
        self._check_function_param_types()
        self._check_function_return_types()
        self._check_variant_types()

        return self.issues

    def _check_type_gaps(self) -> None:
        """Check for symbols without type information

        Identifies symbols that were never assigned a concrete type
        during inference. These will use auto or luaValue in generated code.
        """
        # Check all symbols in inferred_types
        all_symbols = set(self.inferencer.table_info.keys()) | set(self.inferencer.inferred_types.keys())

        for symbol_name in all_symbols:
            # Check if symbol has inferred type
            if symbol_name in self.inferencer.inferred_types:
                type_info = self.inferencer.inferred_types[symbol_name]
                if type_info.kind == TypeKind.UNKNOWN:
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        symbol=symbol_name,
                        issue_type="type_gap",
                        message=f"No inferred type for symbol '{symbol_name}'",
                        suggestion=(
                            "Symbol will use auto in generated code. "
                            "Consider initializing with a concrete value or "
                            "adding type annotations."
                        )
                    ))

            # Check if table has clear array/map decision
            if symbol_name in self.inferencer.table_info:
                table_info = self.inferencer.table_info[symbol_name]
                if not table_info.is_array and not table_info.has_string_keys and not table_info.has_numeric_keys:
                    self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    symbol=symbol_name,
                    issue_type="undetermined_table",
                    message=(
                        f"Table '{symbol_name}' usage doesn't clearly "
                        f"indicate array or map structure"
                    ),
                    suggestion=(
                        "Table will be generated as luaValue (dynamic type). "
                        "Add explicit indexing or assignments to clarify usage."
                    )
                ))

    def _check_table_consistency(self) -> None:
        """Check for inconsistent table usage

        Detects tables that are used as both arrays and maps,
        which indicates potential bugs or intentional mixed usage.
        """
        for symbol_name, table_info in self.inferencer.table_info.items():
            # Check for mixed array/map usage
            if table_info.is_array and table_info.has_string_keys:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    symbol=symbol_name,
                    issue_type="mixed_usage",
                    message=(
                        f"Table '{symbol_name}' used as both array "
                        f"and map (numeric keys: {len(table_info.has_numeric_keys)}, "
                        f"string keys: {len(table_info.has_string_keys)})"
                    ),
                    suggestion=(
                        "Will be generated as luaValue (dynamic type). "
                        "Consider using separate arrays and maps for clarity."
                    )
                ))

            # Check for sparse arrays
            if table_info.is_array and table_info.has_numeric_keys:
                keys = sorted(table_info.has_numeric_keys)
                if keys:
                    # Check if keys are non-contiguous
                    expected = range(1, len(keys) + 1)
                    actual = set(keys)
                    if actual != set(expected):
                        self.issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            symbol=symbol_name,
                            issue_type="sparse_array",
                            message=(
                                f"Table '{symbol_name}' appears to be a sparse "
                                f"array with non-contiguous keys: {keys[:10]}..."
                            ),
                            suggestion=(
                                "Sparse arrays may have performance implications. "
                                "Consider using map with explicit keys instead."
                            )
                        ))

    def _check_propagation_completeness(self) -> None:
        """Check if all inter-procedural propagations completed

        Verifies that function parameters involved in inter-procedural
        analysis have proper type information.
        """
        for func_name in self.inferencer.func_registry.get_all_functions():
            signature = self.inferencer.func_registry.get_signature(func_name)
            if not signature:
                continue

            for param_idx in range(signature.get_num_params()):
                param_name = self.inferencer.func_registry.get_param_name(
                    func_name, param_idx
                )
                param_info = self.inferencer.func_registry.get_param_table_info(
                    func_name, param_idx
                )

                # Check if parameter has array usage but no element type
                if param_info and param_info.is_array and not param_info.value_type:
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        symbol=f"{func_name}.{param_name}",
                        issue_type="incomplete_array",
                        message=(
                            f"Parameter '{param_name}' in '{func_name}' is "
                            f"array-typed but element type unknown"
                        ),
                        suggestion=(
                            "Will use luaValue for array elements. "
                            "Ensure parameter is used with consistent element types."
                        )
                    ))

    def _check_function_param_types(self) -> None:
        """Check that function parameters have type information

        Identifies parameters without type information that will
        require generic templating in generated code.
        """
        for func_name in self.inferencer.func_registry.get_all_functions():
            signature = self.inferencer.func_registry.get_signature(func_name)
            if not signature:
                continue

            # Check functions with call sites but untyped parameters
            if signature.call_sites:
                for param_idx, param_name in enumerate(signature.param_names):
                    param_info = self.inferencer.func_registry.get_param_table_info(
                        func_name, param_idx
                    )

                    if not param_info:
                        # Count how many call sites provide typed arguments
                        typed_args = 0
                        for call_site in signature.call_sites:
                            arg_sym = call_site.get_arg_symbol(param_idx)
                            if arg_sym and arg_sym in self.inferencer.table_info:
                                typed_args += 1

                        if typed_args > 0:
                            self.issues.append(ValidationIssue(
                                severity=ValidationSeverity.INFO,
                                symbol=f"{func_name}.{param_name}",
                                issue_type="no_param_info",
                                message=(
                                    f"Parameter '{param_name}' in '{func_name}' "
                                    f"has no type info ({typed_args} typed args provided)"
                                ),
                                suggestion=(
                                    "Parameter will use auto& (template parameter). "
                                    "Type propagation may improve this."
                                )
                            ))

    def _check_function_return_types(self) -> None:
        """Check function return type consistency

        Validates that functions have consistent return types
        when multiple return paths exist.
        """
        # This is a placeholder for future enhancement
        # Return type analysis would require tracking return statements
        pass

    def _check_variant_types(self) -> None:
        """Check for VARIANT types that could be optimized

        Identifies symbols with VARIANT types that might be
        collapsible to a more specific type.
        """
        for symbol_name, symbol in self._get_all_symbols().items():
            if symbol.inferred_type and symbol.inferred_type.kind == TypeKind.VARIANT:
                # Check if variant contains incompatible types
                kinds = set(t.kind for t in symbol.inferred_type.subtypes)
                if TypeKind.TABLE in kinds and TypeKind.NUMBER in kinds:
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        symbol=symbol_name,
                        issue_type="mixed_variant",
                        message=(
                            f"Symbol '{symbol_name}' has VARIANT type with "
                            f"incompatible types (TABLE and NUMBER)"
                        ),
                        suggestion=(
                            "VARIANT will use luaValue at runtime. "
                            "Review code to ensure consistent usage."
                        )
                    ))

    def _get_all_symbols(self) -> dict:
        """Get all symbols from context

        Returns:
            Dictionary of symbol name to Symbol object
        """
        result = {}
        all_syms = self.inferencer.context.get_all_symbols()
        for sym in all_syms:
            result[sym.name] = sym
        return result

    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues filtered by severity level

        Args:
            severity: Severity level to filter by

        Returns:
            List of ValidationIssue objects with specified severity
        """
        return [i for i in self.issues if i.severity == severity]

    def has_errors(self) -> bool:
        """Check if any errors were found

        Returns:
            True if at least one ERROR severity issue exists
        """
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)

    def has_warnings(self) -> bool:
        """Check if any warnings were found

        Returns:
            True if at least one WARNING severity issue exists
        """
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)

    def print_issues(
        self,
        filter_severity: Optional[ValidationSeverity] = None,
        max_issues: Optional[int] = None
    ) -> str:
        """Generate formatted issue report

        Args:
            filter_severity: Only show issues of this severity (None = all)
            max_issues: Maximum number of issues to show (None = all)

        Returns:
            Formatted issue report as string
        """
        filtered_issues = self.issues
        if filter_severity:
            filtered_issues = [
                i for i in self.issues if i.severity == filter_severity
            ]

        if max_issues:
            filtered_issues = filtered_issues[:max_issues]

        if not filtered_issues:
            return "No validation issues found."

        lines = ["=== Type Validation Issues ==="]

        # Group by severity
        by_severity = {
            ValidationSeverity.ERROR: [],
            ValidationSeverity.WARNING: [],
            ValidationSeverity.INFO: []
        }
        for issue in filtered_issues:
            by_severity[issue.severity].append(issue)

        # Print each severity group
        for severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING,
                         ValidationSeverity.INFO]:
            issues = by_severity[severity]
            if issues:
                lines.append(f"\n{severity.value.upper()} ({len(issues)}):")
                for issue in issues:
                    lines.append(issue.format())

        # Add truncation notice
        if max_issues and len(filtered_issues) < len(self.issues):
            lines.append(
                f"\n... ({len(self.issues) - len(filtered_issues)} more issues hidden)"
            )

        return "\n".join(lines)

    def print_summary(self) -> str:
        """Generate formatted summary statistics

        Returns:
            Formatted summary as string
        """
        lines = ["=== Type Validation Summary ==="]

        # Count by severity
        by_severity = {
            ValidationSeverity.ERROR: 0,
            ValidationSeverity.WARNING: 0,
            ValidationSeverity.INFO: 0
        }
        for issue in self.issues:
            by_severity[issue.severity] += 1

        lines.append(f"Total issues: {len(self.issues)}")
        lines.append(f"  Errors: {by_severity[ValidationSeverity.ERROR]}")
        lines.append(f"  Warnings: {by_severity[ValidationSeverity.WARNING]}")
        lines.append(f"  Info: {by_severity[ValidationSeverity.INFO]}")

        # Count by issue type
        by_type: dict[str, int] = {}
        for issue in self.issues:
            by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1

        if by_type:
            lines.append("\nIssues by type:")
            for issue_type, count in sorted(by_type.items()):
                lines.append(f"  {issue_type}: {count}")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all validation issues"""
        self.issues.clear()