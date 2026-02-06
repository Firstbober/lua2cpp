"""Optimization logger for Lua2C transpiler

Tracks and reports optimization decisions, skipped optimizations,
and provides summary statistics.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class OptimizationKind(Enum):
    """Types of optimizations"""
    LITERAL = "literal"
    LOCAL_VAR = "local_variable"
    OPERATOR = "operator"
    TABLE = "table"
    LOOP = "loop"
    FUNCTION_PARAM = "function_parameter"
    TYPE_CONVERSION = "type_conversion"


@dataclass
class OptimizationRecord:
    """Record of a single optimization decision"""
    kind: OptimizationKind
    symbol: Optional[str]
    from_type: str
    to_type: str
    reason: str
    line: Optional[int] = None


@dataclass
class SkipRecord:
    """Record of a skipped optimization"""
    kind: OptimizationKind
    symbol: Optional[str]
    reason: str
    line: Optional[int] = None


class OptimizationLogger:
    """Logs optimization decisions and provides summaries"""

    def __init__(self) -> None:
        self.optimizations: List[OptimizationRecord] = []
        self.skipped: List[SkipRecord] = []
        self.warnings: List[str] = []

    def log_optimization(self,
                        kind: OptimizationKind,
                        symbol: Optional[str],
                        from_type: str,
                        to_type: str,
                        reason: str,
                        line: Optional[int] = None) -> None:
        """Log a successful optimization

        Args:
            kind: Type of optimization
            symbol: Symbol name (if applicable)
            from_type: Original type
            to_type: Optimized type
            reason: Reason for optimization
            line: Source line number
        """
        record = OptimizationRecord(
            kind=kind,
            symbol=symbol,
            from_type=from_type,
            to_type=to_type,
            reason=reason,
            line=line
        )
        self.optimizations.append(record)

    def log_skipped(self,
                   kind: OptimizationKind,
                   symbol: Optional[str],
                   reason: str,
                   line: Optional[int] = None) -> None:
        """Log a skipped optimization

        Args:
            kind: Type of optimization that was skipped
            symbol: Symbol name (if applicable)
            reason: Reason for skipping
            line: Source line number
        """
        record = SkipRecord(
            kind=kind,
            symbol=symbol,
            reason=reason,
            line=line
        )
        self.skipped.append(record)

    def log_warning(self, message: str) -> None:
        """Log a warning message

        Args:
            message: Warning message
        """
        self.warnings.append(message)

    def get_summary(self) -> Dict:
        """Get summary statistics

        Returns:
            Dictionary with optimization statistics
        """
        optimized_by_kind: Dict[OptimizationKind, int] = {}
        for opt in self.optimizations:
            optimized_by_kind[opt.kind] = optimized_by_kind.get(opt.kind, 0) + 1

        skipped_by_kind: Dict[OptimizationKind, int] = {}
        for skip in self.skipped:
            skipped_by_kind[skip.kind] = skipped_by_kind.get(skip.kind, 0) + 1

        type_changes: Dict[str, int] = {}
        for opt in self.optimizations:
            change = f"{opt.from_type} → {opt.to_type}"
            type_changes[change] = type_changes.get(change, 0) + 1

        return {
            "total_optimizations": len(self.optimizations),
            "optimizations_by_kind": optimized_by_kind,
            "type_changes": type_changes,
            "total_skipped": len(self.skipped),
            "skipped_by_kind": skipped_by_kind,
            "total_warnings": len(self.warnings)
        }

    def print_summary(self) -> str:
        """Generate formatted summary string

        Returns:
            Formatted summary as string
        """
        summary = self.get_summary()
        lines = []

        lines.append("=== Optimization Summary ===")
        lines.append(f"Total optimizations: {summary['total_optimizations']}")
        lines.append("")

        if summary['optimizations_by_kind']:
            lines.append("Optimizations by kind:")
            for kind, count in summary['optimizations_by_kind'].items():
                lines.append(f"  {kind.value}: {count}")
            lines.append("")

        if summary['type_changes']:
            lines.append("Type changes:")
            for change, count in sorted(summary['type_changes'].items()):
                lines.append(f"  {change}: {count}")
            lines.append("")

        lines.append(f"Skipped optimizations: {summary['total_skipped']}")

        if summary['skipped_by_kind']:
            lines.append("Skipped by kind:")
            for kind, count in summary['skipped_by_kind'].items():
                lines.append(f"  {kind.value}: {count}")
            lines.append("")

        if self.skipped:
            lines.append("Skipped details (top 10):")
            for skip in self.skipped[:10]:
                symbol_part = f"'{skip.symbol}': " if skip.symbol else ""
                lines.append(f"  {skip.kind.value} - {symbol_part}{skip.reason}")
            lines.append("")

        lines.append(f"Warnings: {summary['total_warnings']}")

        if self.warnings:
            lines.append("Warning details:")
            for warning in self.warnings:
                lines.append(f"  {warning}")

        return "\n".join(lines)

    def get_optimized_symbols(self) -> List[str]:
        """Get list of symbols that were optimized

        Returns:
            List of symbol names
        """
        return [opt.symbol for opt in self.optimizations if opt.symbol]

    def get_skipped_symbols(self) -> List[str]:
        """Get list of symbols where optimization was skipped

        Returns:
            List of symbol names
        """
        return [skip.symbol for skip in self.skipped if skip.symbol]

    def clear(self) -> None:
        """Clear all logs"""
        self.optimizations.clear()
        self.skipped.clear()
        self.warnings.clear()
