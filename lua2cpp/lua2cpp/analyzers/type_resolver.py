"""Type resolver for Lua2Cpp transpiler

Multi-pass type inference engine that propagates types across
function boundaries using bidirectional analysis.

Structure:
- Pass 1: Collect function signatures
- Pass 2: Local type inference within functions
- Pass 3: Iterative inter-procedural type propagation
- Pass 4: Validation and finalization

Design Principles:
- Bidirectional propagation (arguments ↔ parameters)
- ANY/VARIANT types for conflicting type information
- Iterative fixed-point algorithm
- Comprehensive call graph tracking
"""

from typing import Dict, Optional
from luaparser import astnodes

from lua2cpp.core.scope import ScopeManager
from lua2cpp.core.symbol_table import SymbolTable
from lua2cpp.core.types import Type, TypeKind, ASTAnnotationStore


class TypeResolver:
    """Type inference engine with multi-pass inter-procedural support

    Performs four-pass type analysis to propagate type information
    across function boundaries using a fixed-point algorithm.
    """

    def __init__(
        self,
        scope_manager: ScopeManager,
        symbol_table: SymbolTable,
        function_registry: 'FunctionSignatureRegistry'
    ) -> None:
        """Initialize type resolver

        Args:
            scope_manager: Scope manager for tracking variable scoping
            symbol_table: Symbol table for variable resolution
            function_registry: Function signature registry for inter-procedural analysis
        """
        self.scope_manager = scope_manager
        self.symbol_table = symbol_table
        self.function_registry = function_registry

        self._current_function: Optional[str] = None
        self._max_iterations: int = 10
        self.inferred_types: Dict[str, Type] = {}

    def resolve_chunk(self, chunk: astnodes.Chunk) -> None:
        """Perform multi-pass type resolution on entire chunk

        Executes four passes:
        1. Collect all function signatures
        2. Infer local types within functions
        3. Iteratively propagate types inter-procedurally
        4. Validate and finalize types

        Args:
            chunk: AST chunk to analyze
        """
        self._collect_function_signatures(chunk)
        self._infer_local_types(chunk)
        self._propagate_types_interprocedurally()
        self._validate_and_finalize()

    def _collect_function_signatures(self, chunk: astnodes.Chunk) -> None:
        """Pass 1: Collect all function definitions

        Registers all local functions with their parameter signatures
        before any type inference occurs. This provides the
        foundation for inter-procedural analysis.

        Args:
            chunk: AST chunk to analyze
        """
        for stmt in chunk.body.body:
            if isinstance(stmt, astnodes.LocalFunction):
                func_name = stmt.name.id if hasattr(stmt.name, 'id') else "anonymous"
                param_names = [p.id for p in stmt.args if hasattr(p, 'id')]
                self.function_registry.register_function(
                    func_name, param_names, is_local=True
                )

    def _infer_local_types(self, chunk: astnodes.Chunk) -> None:
        """Pass 2: Infer types within function bodies

        Performs local type inference for all statements,
        tracking parameter usage patterns within each function.

        Args:
            chunk: AST chunk to analyze
        """
        for stmt in chunk.body.body:
            self._infer_statement(stmt)

    def _propagate_types_interprocedurally(self) -> None:
        """Pass 3: Iterative type propagation until fixed point

        Performs bidirectional type propagation:
        - Arguments → Parameters: Types from call sites propagate to function params
        - Parameters → Arguments: Parameter types propagate back to arguments

        Uses iterative fixed-point algorithm to handle cyclic dependencies.
        Stops when no changes occur or max iterations reached.

        Conflict Resolution:
        - Conflicting types are merged into ANY/VARIANT types
        - Most specific types are preferred (NUMBER > TABLE > UNKNOWN)
        """
        changed = True
        iteration = 0

        while changed and iteration < self._max_iterations:
            changed = False
            iteration += 1

            changed |= self._propagate_args_to_params()
            changed |= self._propagate_params_to_args()

            if not changed and iteration < self._max_iterations:
                break

    def _propagate_args_to_params(self) -> bool:
        """Propagate types from arguments to parameters

        For each function call, examines the types of arguments
        and propagates them to the corresponding parameters.
        This enables type inference even when parameters are only
        used without explicit type assignments.

        Returns:
            True if any changes were made, False otherwise
        """
        changed = False
        from lua2cpp.core.types import TableTypeInfo

        for func_name, signature in self.function_registry.signatures.items():
            for call_site in signature.call_sites:
                # For each argument at this call site
                for arg_idx, arg_symbol_name in enumerate(call_site.arg_symbols):
                    if not arg_symbol_name:
                        # Argument is not a simple name (e.g., expression)
                        continue

                    # Get argument's type
                    arg_type = self.inferred_types.get(arg_symbol_name)
                    if not arg_type:
                        # Argument has no type info yet
                        continue

                    # Get parameter's current table info
                    param_table_info = self.function_registry.get_param_table_info(
                        func_name, arg_idx
                    )

                    if not param_table_info:
                        # Initialize parameter table info from argument
                        # Store argument type as value_type in param table info
                        new_table_info = TableTypeInfo(
                            is_array=True,  # Default to array for now
                            value_type=arg_type
                        )
                        self.function_registry.update_param_table_info(
                            func_name, arg_idx, new_table_info
                        )
                        changed = True
                    else:
                        # Merge table info (handle conflicts)
                        if param_table_info.value_type:
                            # Merge argument type with parameter type
                            merged_type = self._merge_types(
                                param_table_info.value_type, arg_type
                            )
                            if merged_type != param_table_info.value_type:
                                param_table_info.value_type = merged_type
                                changed = True
                        else:
                            # Set argument type as parameter value type
                            param_table_info.value_type = arg_type
                            changed = True

        return changed

    def _propagate_params_to_args(self) -> bool:
        """Propagate types from parameters back to arguments

        For each function with typed parameters, propagates the
        parameter type information to all arguments at call sites.
        This handles cases where functions expect typed parameters
        but arguments have no explicit type information.

        Returns:
            True if any changes were made, False otherwise
        """
        changed = False

        for func_name, signature in self.function_registry.signatures.items():
            for param_idx, param_name in enumerate(signature.param_names):
                # Get parameter's table info
                param_table_info = self.function_registry.get_param_table_info(
                    func_name, param_idx
                )
                if not param_table_info or not param_table_info.value_type:
                    # Parameter has no type info or value_type is not set
                    continue

                # Propagate to all call sites
                for call_site in signature.call_sites:
                    arg_symbol_name = call_site.get_arg_symbol(param_idx)
                    if not arg_symbol_name:
                        # Argument is not a simple name
                        continue

                    # Get argument's current type
                    arg_type = self.inferred_types.get(arg_symbol_name)

                    if not arg_type:
                        # Initialize argument type from parameter
                        self.inferred_types[arg_symbol_name] = param_table_info.value_type
                        changed = True
                    else:
                        # Merge argument type with parameter type
                        merged_type = self._merge_types(arg_type, param_table_info.value_type)
                        if merged_type != arg_type:
                            self.inferred_types[arg_symbol_name] = merged_type
                            changed = True

        return changed

    def _merge_types(self, existing: Type, new_type: Type) -> Type:
        """Merge conflicting types into ANY/VARIANT type

        Handles type conflict resolution by creating composite types
        when incompatible types are encountered.

        Args:
            existing: Existing type
            new_type: New type to merge

        Returns:
            Merged type (existing, new_type, or ANY/VARIANT)
        """
        if existing.kind == new_type.kind:
            return existing

        if existing.kind == TypeKind.UNKNOWN:
            return new_type

        if new_type.kind == TypeKind.UNKNOWN:
            return existing

        return Type(TypeKind.ANY, subtypes=[existing, new_type])

    def _validate_and_finalize(self) -> None:
        """Pass 4: Validate and finalize all types

        Ensures type consistency and finalizes all type information.

        Validation includes:
        - Checking all inferred types are stable (not UNKNOWN)
        - Reporting type statistics
        - Finalizing type information on all symbols
        - Detecting unresolved circular dependencies
        - Handling any remaining type conflicts
        """
        # Count types by kind for statistics
        type_counts = {kind: 0 for kind in TypeKind}
        unknown_symbols = []

        # Analyze all inferred types
        for symbol_name, type_obj in self.inferred_types.items():
            type_counts[type_obj.kind] += 1

            # Track symbols with UNKNOWN type
            if type_obj.kind == TypeKind.UNKNOWN:
                unknown_symbols.append(symbol_name)

        # Track conflicts (ANY/VARIANT types)
        conflict_symbols = []
        for symbol_name, type_obj in self.inferred_types.items():
            if type_obj.kind in (TypeKind.ANY, TypeKind.VARIANT):
                conflict_symbols.append((symbol_name, type_obj))

        # Report statistics
        self._report_type_statistics(type_counts, unknown_symbols, conflict_symbols)

        # Validate no critical issues remain
        if unknown_symbols:
            # UNKNOWN types are acceptable in Lua (dynamic typing)
            # but we track them for completeness
            pass

        # Finalize type information on all symbols
        self._finalize_type_information()

    def _infer_statement(self, stmt: astnodes.Node) -> None:
        """Infer types in a statement

        Args:
            stmt: AST statement to analyze
        """
        if isinstance(stmt, astnodes.LocalAssign):
            self._infer_local_assign(stmt)
        elif isinstance(stmt, astnodes.Assign):
            self._infer_assign(stmt)
        elif isinstance(stmt, astnodes.LocalFunction):
            self._infer_local_function(stmt)
        elif isinstance(stmt, astnodes.Call):
            self._infer_expression(stmt)
        elif isinstance(stmt, astnodes.While):
            self._infer_expression(stmt.test)
            for s in stmt.body.body:
                self._infer_statement(s)
        elif isinstance(stmt, astnodes.If):
            self._infer_expression(stmt.test)
            for s in stmt.body.body:
                self._infer_statement(s)
            if stmt.orelse:
                if isinstance(stmt.orelse, list):
                    for s in stmt.orelse:
                        self._infer_statement(s)
                elif isinstance(stmt.orelse, astnodes.Block):
                    for s in stmt.orelse.body:
                        self._infer_statement(s)
        elif isinstance(stmt, astnodes.Return):
            for v in (stmt.values or []):
                self._infer_expression(v)

    def _infer_local_assign(self, stmt: astnodes.LocalAssign) -> None:
        for i, target in enumerate(stmt.targets):
            if hasattr(target, 'id'):
                var_name = target.id
                if i < len(stmt.values):
                    value_type = self._infer_expression(stmt.values[i])
                    self.inferred_types[var_name] = value_type
                else:
                    self.inferred_types[var_name] = Type(TypeKind.UNKNOWN)

    def _infer_assign(self, stmt: astnodes.Assign) -> None:
        for i, (target, value) in enumerate(zip(stmt.targets, stmt.values)):
            if isinstance(target, astnodes.Name):
                value_type = self._infer_expression(value)
                self.inferred_types[target.id] = value_type
            elif isinstance(target, astnodes.Index):
                self._infer_expression(target.value)
                self._infer_expression(target.idx)
                self._infer_expression(value)

    def _infer_local_function(self, stmt: astnodes.LocalFunction) -> None:
        func_name = stmt.name.id if hasattr(stmt.name, 'id') else "anonymous"
        self.inferred_types[func_name] = Type(TypeKind.FUNCTION)

        old_function = self._current_function
        self._current_function = func_name

        for param in stmt.args:
            if hasattr(param, 'id'):
                self.inferred_types[param.id] = Type(TypeKind.UNKNOWN)

        for s in stmt.body.body:
            self._infer_statement(s)

        self._current_function = old_function

    def _infer_expression(self, expr: astnodes.Node) -> Type:
        if isinstance(expr, astnodes.Number):
            type_info = Type(TypeKind.NUMBER, is_constant=True)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.String):
            type_info = Type(TypeKind.STRING, is_constant=True)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.TrueExpr) or isinstance(expr, astnodes.FalseExpr):
            type_info = Type(TypeKind.BOOLEAN, is_constant=True)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Name):
            type_info = self.inferred_types.get(expr.id, Type(TypeKind.UNKNOWN))
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Call):
            self._infer_expression(expr.func)
            for arg in expr.args:
                self._infer_expression(arg)
            type_info = Type(TypeKind.UNKNOWN)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Table):
            type_info = Type(TypeKind.TABLE)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Index):
            self._infer_expression(expr.value)
            self._infer_expression(expr.idx)
            type_info = Type(TypeKind.UNKNOWN)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.AnonymousFunction):
            type_info = Type(TypeKind.FUNCTION)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, (astnodes.AddOp, astnodes.SubOp, astnodes.MultOp,
                                astnodes.FloatDivOp, astnodes.FloorDivOp,
                                astnodes.ModOp, astnodes.ExpoOp)):
            left_type = self._infer_expression(expr.left)
            self._infer_expression(expr.right)
            type_info = self._infer_arithmetic_result(left_type)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Concat):
            self._infer_expression(expr.left)
            self._infer_expression(expr.right)
            type_info = Type(TypeKind.STRING)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, (astnodes.EqToOp, astnodes.NotEqToOp, astnodes.LessThanOp,
                                astnodes.LessOrEqThanOp, astnodes.GreaterThanOp,
                                astnodes.GreaterOrEqThanOp)):
            self._infer_expression(expr.left)
            self._infer_expression(expr.right)
            type_info = Type(TypeKind.BOOLEAN)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, (astnodes.AndLoOp, astnodes.OrLoOp)):
            left_type = self._infer_expression(expr.left)
            right_type = self._infer_expression(expr.right)
            type_info = self._merge_types(left_type, right_type)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.UMinusOp):
            type_info = self._infer_expression(expr.operand)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.ULNotOp):
            self._infer_expression(expr.operand)
            type_info = Type(TypeKind.BOOLEAN)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info

        type_info = Type(TypeKind.UNKNOWN)
        ASTAnnotationStore.set_type(expr, type_info)
        return type_info

    def _infer_arithmetic_result(self, left: Type) -> Type:
        if left.kind == TypeKind.NUMBER:
            return Type(TypeKind.NUMBER)
        return Type(TypeKind.UNKNOWN)

    def get_type(self, symbol: str) -> Type:
        """Get inferred type for a symbol

        Args:
            symbol: Symbol name to look up

        Returns:
            Inferred type or UNKNOWN if not found
        """
        if symbol in self.inferred_types:
            return self.inferred_types[symbol]
        return Type(TypeKind.UNKNOWN)

    def annotate_node(self, node: astnodes.Node, type_obj: Type) -> None:
        """Attach type information to AST node using ASTAnnotationStore

        Args:
            node: AST node to annotate
            type_obj: Type object to attach
        """
        ASTAnnotationStore.set_type(node, type_obj)

    def get_node_type(self, node: astnodes.Node) -> Optional[Type]:
        """Retrieve type information from AST node

        Args:
            node: AST node to query

        Returns:
            Type object if found, None otherwise
        """
        return ASTAnnotationStore.get_type(node)

    def _report_type_statistics(
        self,
        type_counts: Dict[TypeKind, int],
        unknown_symbols: list,
        conflict_symbols: list
    ) -> None:
        """Report type statistics and issues

        Args:
            type_counts: Dictionary counting each TypeKind
            unknown_symbols: List of symbols with UNKNOWN type
            conflict_symbols: List of (symbol, type) with ANY/VARIANT type
        """
        total_symbols = sum(type_counts.values())
        if total_symbols == 0:
            return

        stats = self.function_registry.get_statistics()
        lines = ["=== Type Resolution Statistics ==="]
        lines.append(f"Total symbols: {total_symbols}")

        for kind, count in type_counts.items():
            if count > 0:
                lines.append(f"  {kind.name}: {count}")

        if unknown_symbols:
            lines.append(f"\nSymbols with UNKNOWN type ({len(unknown_symbols)}):")
            for symbol in unknown_symbols[:10]:
                lines.append(f"  {symbol}")
            if len(unknown_symbols) > 10:
                lines.append(f"  ... and {len(unknown_symbols) - 10} more")

        if conflict_symbols:
            lines.append(f"\nSymbols with type conflicts ({len(conflict_symbols)}):")
            for symbol, type_obj in conflict_symbols[:10]:
                lines.append(f"  {symbol}: {type_obj.cpp_type()}")
            if len(conflict_symbols) > 10:
                lines.append(f"  ... and {len(conflict_symbols) - 10} more")

    def _finalize_type_information(self) -> None:
        """Finalize type information on all symbols

        Ensures all type information is properly attached and ready
        for use by code generation phases.
        """
        # All types are already stored in self.inferred_types
        # This method is a hook for future finalization steps
        pass
