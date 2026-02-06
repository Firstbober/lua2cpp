"""Propagation logger for inter-procedural type analysis

Logs type propagation decisions and conflicts with configurable verbosity.
By default, only logs warnings to minimize output, but can track all
propagations for debugging purposes.

Design Principles:
- Warnings-only logging by default (user preference)
- Comprehensive statistics tracking
- Clear formatting for debugging
- Support for conflict resolution tracking
"""

from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

if __name__.startswith('lua2c.analyzers'):
    from lua2c.core.type_system import Type, TableTypeInfo
else:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from lua2c.core.type_system import Type, TableTypeInfo


class PropagationDirection(Enum):
    """Direction of type propagation"""
    ARGS_TO_PARAMS = "arg→param"
    PARAMS_TO_ARGS = "param→arg"


@dataclass
class PropagationRecord:
    """Record of a single type propagation event

    Stores details about each type propagation step, enabling
    debugging and analysis of the propagation process.

    Attributes:
        from_symbol: Source symbol name
        to_symbol: Destination symbol name
        table_info: Table type information that was propagated
        direction: Propagation direction (args→params or params→args)
        iteration: Propagation iteration number
        line: Source line number (optional)
    """
    from_symbol: str
    to_symbol: str
    table_info: 'TableTypeInfo'
    direction: PropagationDirection
    iteration: int
    line: Optional[int] = None

    def format(self) -> str:
        """Format propagation record for display

        Returns:
            Formatted string representation
        """
        value_type_str = table_info.value_type.kind.name if table_info.value_type else "unknown"
        array_str = "array" if self.table_info.is_array else "map"

        return (
            f"  {self.direction.value} (iter {self.iteration}): "
            f"{self.from_symbol} → {self.to_symbol}: "
            f"{array_str}[{value_type_str}]"
        )


@dataclass
class ConflictRecord:
    """Record of a type conflict during propagation

    Documents when conflicting type information is encountered
    and how it was resolved (typically by creating a VARIANT type).

    Attributes:
        symbol: Symbol name with conflict
        existing_type: Previously inferred type
        new_type: Newly encountered type
        result_type: Resulting type after conflict resolution
    """
    symbol: str
    existing_type: 'Type'
    new_type: 'Type'
    result_type: 'Type'

    def format(self) -> str:
        """Format conflict record for display

        Returns:
            Formatted string representation
        """
        return (
            f"  Conflict: '{self.symbol}': "
            f"{self.existing_type.kind.name} vs {self.new_type.kind.name} "
            f"→ {self.result_type.cpp_type()}"
        )


class PropagationLogger:
    """Logs type propagation decisions and conflicts

    Provides comprehensive tracking of type propagation during
    inter-procedural analysis. By default, only logs warnings
    to minimize output noise.

    Usage Example:
        logger = PropagationLogger()

        # Start a propagation iteration
        logger.start_iteration(1)

        # Log a propagation event
        table_info = TableTypeInfo(is_array=True, value_type=Type(TypeKind.NUMBER))
        logger.log_propagation("arg", "param", table_info,
                            PropagationDirection.ARGS_TO_PARAMS)

        # Log a conflict
        logger.log_conflict("x", Type(TypeKind.NUMBER), Type(TypeKind.STRING),
                          result_type)

        # Print summary
        print(logger.print_summary())
    """

    def __init__(self, verbose: bool = False) -> None:
        """Initialize propagation logger

        Args:
            verbose: If True, log all propagations; if False, only warnings
        """
        self.verbose = verbose
        self.propagations: List[PropagationRecord] = []
        self.conflicts: List[ConflictRecord] = []
        self.warnings: List[str] = []
        self._iteration = 0

    def start_iteration(self, iteration: int) -> None:
        """Mark the start of a propagation iteration

        Args:
            iteration: Iteration number (starting from 1)
        """
        self._iteration = iteration

    def log_propagation(
        self,
        from_symbol: str,
        to_symbol: str,
        table_info: 'TableTypeInfo',
        direction: PropagationDirection,
        line: Optional[int] = None
    ) -> None:
        """Log a type propagation event

        Internal use by type inference system. Records all propagations
        regardless of verbose setting (for statistics).

        Args:
            from_symbol: Source symbol name
            to_symbol: Destination symbol name
            table_info: Table type information being propagated
            direction: Propagation direction
            line: Source line number (optional)
        """
        record = PropagationRecord(
            from_symbol=from_symbol,
            to_symbol=to_symbol,
            table_info=table_info,
            direction=direction,
            iteration=self._iteration,
            line=line
        )
        self.propagations.append(record)

    def log_conflict(
        self,
        symbol: str,
        existing_type: 'Type',
        new_type: 'Type',
        result_type: 'Type'
    ) -> None:
        """Log a type conflict and its resolution

        Called when conflicting type information is encountered.
        Logs as warning (user preference).

        Args:
            symbol: Symbol name with conflict
            existing_type: Previously inferred type
            new_type: Newly encountered conflicting type
            result_type: Resulting type after conflict resolution
        """
        record = ConflictRecord(
            symbol=symbol,
            existing_type=existing_type,
            new_type=new_type,
            result_type=result_type
        )
        self.conflicts.append(record)

        # Always log conflicts as warnings
        self.warnings.append(
            f"Type conflict for '{symbol}': "
            f"{existing_type.kind.name} vs {new_type.kind.name} "
            f"→ {result_type.cpp_type()}"
        )

    def log_warning(self, message: str) -> None:
        """Log a warning message

        Used for non-conflict warnings such as propagation
        convergence issues or unexpected situations.

        Args:
            message: Warning message
        """
        self.warnings.append(message)

    def get_statistics(self) -> dict:
        """Get propagation statistics

        Returns:
            Dictionary with comprehensive statistics:
            - total_propagations: Total number of propagations
            - args_to_params: Count of arg→param propagations
            - params_to_args: Count of param→arg propagations
            - conflicts: Number of conflicts resolved
            - warnings: Number of warnings logged
            - iterations: Highest iteration number reached
        """
        args_to_params = sum(
            1 for p in self.propagations
            if p.direction == PropagationDirection.ARGS_TO_PARAMS
        )
        params_to_args = sum(
            1 for p in self.propagations
            if p.direction == PropagationDirection.PARAMS_TO_ARGS
        )
        iterations = max([p.iteration for p in self.propagations], default=0)

        return {
            "total_propagations": len(self.propagations),
            "args_to_params": args_to_params,
            "params_to_args": params_to_args,
            "conflicts": len(self.conflicts),
            "warnings": len(self.warnings),
            "iterations": iterations
        }

    def get_propagations_by_iteration(self) -> dict:
        """Get propagations grouped by iteration number

        Returns:
            Dictionary mapping iteration number to list of propagations
        """
        result = {}
        for prop in self.propagations:
            if prop.iteration not in result:
                result[prop.iteration] = []
            result[prop.iteration].append(prop)
        return result

    def print_summary(self) -> str:
        """Generate formatted summary string

        Shows warnings (if any), conflicts, and propagation statistics.
        Verbose mode shows detailed propagation records.

        Returns:
            Formatted summary as string
        """
        stats = self.get_statistics()
        lines = ["=== Type Propagation Summary ==="]

        # Warnings (always shown)
        if self.warnings:
            lines.append(f"\n⚠ Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"  {warning}")
            lines.append("")

        # Conflicts
        if stats["conflicts"] > 0:
            lines.append(f"Conflicts resolved: {stats['conflicts']}")
            if self.verbose:
                for conflict in self.conflicts:
                    lines.append(conflict.format())
            lines.append("")

        # Statistics
        lines.append(f"Total propagations: {stats['total_propagations']}")
        lines.append(f"  Arguments → Parameters: {stats['args_to_params']}")
        lines.append(f"  Parameters → Arguments: {stats['params_to_args']}")
        lines.append(f"Iterations completed: {stats['iterations']}")

        # Verbose output
        if self.verbose and self.propagations:
            lines.append("\nDetailed propagation log:")
            by_iteration = self.get_propagations_by_iteration()
            for iter_num in sorted(by_iteration.keys()):
                lines.append(f"\n  Iteration {iter_num}:")
                for prop in by_iteration[iter_num]:
                    lines.append(prop.format())

        return "\n".join(lines)

    def print_propagation_graph(self) -> str:
        """Print simplified propagation graph for debugging

        Shows which symbols influenced which others during propagation.

        Returns:
            Graph representation as string
        """
        if not self.propagations:
            return "No propagations recorded."

        lines = ["=== Propagation Graph ==="]

        # Group by source symbol
        by_source: dict[str, List[PropagationRecord]] = {}
        for prop in self.propagations:
            if prop.from_symbol not in by_source:
                by_source[prop.from_symbol] = []
            by_source[prop.from_symbol].append(prop)

        for source, props in sorted(by_source.items()):
            targets = set(p.to_symbol for p in props)
            lines.append(f"{source} → {', '.join(sorted(targets))}")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all logged propagations, conflicts, and warnings"""
        self.propagations.clear()
        self.conflicts.clear()
        self.warnings.clear()
        self._iteration = 0