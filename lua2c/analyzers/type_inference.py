"""Type inference analyzer for Lua2C

Walks AST and infers types for all variables and expressions.
Tracks type usage to determine if types are stable or dynamic.

Enhanced with multi-pass inter-procedural type propagation:
- Pass 1: Collect function signatures
- Pass 2: Local type inference within functions
- Pass 3: Iterative inter-procedural type propagation
- Pass 4: Validation and finalization

Design Principles:
- Bidirectional propagation (arguments ↔ parameters)
- VARIANT types for conflicting type information
- Iterative fixed-point algorithm
- Comprehensive call graph tracking
"""

from typing import Dict, Set, Optional, List
from lua2c.core.context import TranslationContext
from lua2c.core.type_system import Type, TypeKind, TableTypeInfo
from lua2c.core.ast_annotation import ASTAnnotationStore
from luaparser import astnodes
from lua2c.analyzers.function_registry import FunctionSignatureRegistry
from lua2c.analyzers.propagation_logger import (
    PropagationLogger, PropagationDirection
)


class TypeInference:
    """Infers types from Lua AST with inter-procedural support

    Enhanced type inference that performs multi-pass analysis to
    propagate type information across function boundaries.
    """

    def __init__(self, context: TranslationContext, verbose: bool = False) -> None:
        """Initialize type inferencer

        Args:
            context: Translation context
            verbose: Enable verbose logging (default: warnings only)
        """
        self.context = context
        self.inferred_types: Dict[str, Type] = {}
        self.table_info: Dict[str, TableTypeInfo] = {}
        self.seen_types: Dict[str, Set[TypeKind]] = {}

        # Inter-procedural analysis support
        self.func_registry = FunctionSignatureRegistry()
        self.propagation_logger = PropagationLogger(verbose=verbose)
        self._current_function: Optional[str] = None
        self._max_iterations = 10

    def infer_chunk(self, chunk: astnodes.Chunk) -> None:
        """Perform multi-pass type inference on entire chunk

        Executes four passes:
        1. Collect all function signatures
        2. Infer local types within functions
        3. Iteratively propagate types inter-procedurally
        4. Validate and finalize types

        Args:
            chunk: AST chunk to analyze
        """
        # Pass 1: Collect function signatures
        self._collect_function_signatures(chunk)

        # Pass 2: Local type inference
        self._infer_local_types(chunk)

        # Pass 3: Inter-procedural propagation (iterative)
        self._propagate_types_interprocedurally()

        # Pass 4: Validate and finalize
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
                self.func_registry.register_function(
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

        # Track parameter array usage in each function
        for stmt in chunk.body.body:
            if isinstance(stmt, astnodes.LocalFunction):
                func_name = stmt.name.id if hasattr(stmt.name, 'id') else "anonymous"
                for body_stmt in stmt.body.body:
                    self._track_param_array_usage(
                        stmt.args, body_stmt, func_name
                    )

    def _propagate_types_interprocedurally(self) -> None:
        """Pass 3: Iterative type propagation until fixed point

        Performs bidirectional type propagation:
        - Arguments → Parameters: Types from call sites propagate to function params
        - Parameters → Arguments: Parameter types propagate back to arguments

        Uses iterative fixed-point algorithm to handle cyclic dependencies.
        Stops when no changes occur or max iterations reached.

        Conflict Resolution:
        - Conflicting types are merged into VARIANT types
        - Most specific types are preferred (NUMBER > TABLE > UNKNOWN)
        """
        changed = True
        iteration = 0

        while changed and iteration < self._max_iterations:
            changed = False
            iteration += 1
            self.propagation_logger.start_iteration(iteration)

            # Direction 1: Arguments → Parameters
            changed |= self._propagate_args_to_params()

            # Direction 2: Parameters → Arguments
            changed |= self._propagate_params_to_args()

            if not changed and iteration < self._max_iterations:
                # Convergence achieved
                break

        if iteration == self._max_iterations and changed:
            self.propagation_logger.log_warning(
                f"Type propagation did not converge after {self._max_iterations} iterations. "
                "This may indicate circular dependencies or complex type relationships."
            )

    def _propagate_args_to_params(self) -> bool:
        """Propagate types from arguments to parameters

        For each function call, examines the types of arguments
        and propagates them to the corresponding parameters.
        This enables type inference even when parameters are only
        used as arrays without explicit element type assignments.

        Returns:
            True if any changes were made, False otherwise
        """
        changed = False

        for func_name, signature in self.func_registry.signatures.items():
            for call_site in signature.call_sites:
                # For each argument at this call site
                for arg_idx, arg_symbol_name in enumerate(call_site.arg_symbols):
                    if not arg_symbol_name:
                        # Argument is not a simple name (e.g., expression)
                        continue

                    # Get argument's table info
                    arg_table_info = self.table_info.get(arg_symbol_name)
                    if not arg_table_info or not arg_table_info.is_array:
                        # Argument not an array or no type info
                        continue

                    # Get parameter's current table info
                    param_table_info = self.func_registry.get_param_table_info(
                        func_name, arg_idx
                    )

                    if not param_table_info:
                        # Initialize parameter table info from argument
                        self.func_registry.update_param_table_info(
                            func_name, arg_idx, arg_table_info
                        )
                        self.propagation_logger.log_propagation(
                            from_symbol=arg_symbol_name,
                            to_symbol=f"{func_name}[{arg_idx}]",
                            table_info=arg_table_info,
                            direction=PropagationDirection.ARGS_TO_PARAMS,
                            line=call_site.line_number
                        )
                        changed = True
                    else:
                        # Merge table info (handle conflicts)
                        if self._merge_table_info(param_table_info, arg_table_info):
                            self.propagation_logger.log_propagation(
                                from_symbol=arg_symbol_name,
                                to_symbol=f"{func_name}[{arg_idx}]",
                                table_info=param_table_info,
                                direction=PropagationDirection.ARGS_TO_PARAMS,
                                line=call_site.line_number
                            )
                            changed = True

        return changed

    def _propagate_params_to_args(self) -> bool:
        """Propagate types from parameters back to arguments

        For each function with typed parameters, propagates the
        parameter type information to all arguments at call sites.
        This handles cases like spectral-norm.lua where empty
        tables are passed to functions expecting typed arrays.

        Returns:
            True if any changes were made, False otherwise
        """
        changed = False

        for func_name, signature in self.func_registry.signatures.items():
            for param_idx, param_name in enumerate(signature.param_names):
                # Get parameter's table info
                param_table_info = self.func_registry.get_param_table_info(
                    func_name, param_idx
                )
                if not param_table_info or not param_table_info.is_array:
                    # Parameter not an array or no type info
                    continue

                # Propagate to all call sites
                for call_site in signature.call_sites:
                    arg_symbol_name = call_site.get_arg_symbol(param_idx)
                    if not arg_symbol_name:
                        # Argument is not a simple name
                        continue

                    # Get argument's current table info
                    arg_table_info = self.table_info.get(arg_symbol_name)

                    if not arg_table_info:
                        # Initialize argument table info from parameter
                        self.table_info[arg_symbol_name] = TableTypeInfo(
                            is_array=True,
                            value_type=param_table_info.value_type
                        )
                        self.propagation_logger.log_propagation(
                            from_symbol=f"{func_name}[{param_idx}]",
                            to_symbol=arg_symbol_name,
                            table_info=self.table_info[arg_symbol_name],
                            direction=PropagationDirection.PARAMS_TO_ARGS,
                            line=call_site.line_number
                        )
                        changed = True
                    else:
                        # Merge table info (handle conflicts)
                        if self._merge_table_info(arg_table_info, param_table_info):
                            self.propagation_logger.log_propagation(
                                from_symbol=f"{func_name}[{param_idx}]",
                                to_symbol=arg_symbol_name,
                                table_info=arg_table_info,
                                direction=PropagationDirection.PARAMS_TO_ARGS,
                                line=call_site.line_number
                            )
                            changed = True

        return changed

    def _merge_table_info(self, target: TableTypeInfo, source: TableTypeInfo) -> bool:
        """Merge source table info into target

        Handles conflict resolution using VARIANT types when source
        and target have incompatible value types (user's choice).

        Preference order (most specific first):
        1. Known value type (NUMBER, STRING, etc.)
        2. Array flag (if source is array, target becomes array)
        3. UNKNOWN (fallback)

        Args:
            target: TableTypeInfo to merge into (modified in place)
            source: TableTypeInfo to merge from

        Returns:
            True if target was modified, False otherwise
        """
        changed = False

        # Merge array flag
        if source.is_array and not target.is_array:
            target.is_array = True
            changed = True

        # Merge value types with conflict resolution
        if source.value_type and target.value_type:
            if target.value_type.kind != source.value_type.kind:
                # Conflict - create VARIANT type
                if target.value_type.kind != TypeKind.VARIANT:
                    # First conflict detected
                    existing_type = target.value_type
                    target.value_type = Type(
                        TypeKind.VARIANT,
                        subtypes=[existing_type, source.value_type]
                    )
                    self.propagation_logger.log_conflict(
                        symbol=target.value_type.cpp_type(),
                        existing_type=existing_type,
                        new_type=source.value_type,
                        result_type=target.value_type
                    )
                    changed = True
                else:
                    # Already VARIANT - add to subtypes
                    if source.value_type not in target.value_type.subtypes:
                        target.value_type.subtypes.append(source.value_type)
                        changed = True
        elif source.value_type:
            # Target has no value type, use source's
            target.value_type = source.value_type
            changed = True

        return changed

    def _validate_and_finalize(self) -> None:
        """Pass 4: Validate and finalize all types

        Ensures type consistency and finalizes all table information.
        Currently a placeholder for future validation integration.
        """
        # Finalize array decisions for all table_info
        for symbol_name, table_info in self.table_info.items():
            table_info.finalize_array()

    def _infer_statement(self, stmt: astnodes.Node) -> None:
        """Infer types in a statement"""
        if isinstance(stmt, astnodes.LocalAssign):
            self._infer_local_assign(stmt)
        elif isinstance(stmt, astnodes.Assign):
            self._infer_assign(stmt)
        elif isinstance(stmt, astnodes.LocalFunction):
            self._infer_local_function(stmt)
        elif isinstance(stmt, astnodes.Call):
            # Process entire Call expression to trigger call site recording
            self._infer_expression(stmt)
        elif isinstance(stmt, astnodes.While):
            self._infer_expression(stmt.test)
            for s in stmt.body.body:
                self._infer_statement(s)
        elif isinstance(stmt, astnodes.Repeat):
            for s in stmt.body.body:
                self._infer_statement(s)
            self._infer_expression(stmt.test)
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
        elif isinstance(stmt, astnodes.Forin):
            for e in stmt.iter:
                self._infer_expression(e)
            for s in stmt.body.body:
                self._infer_statement(s)
        elif isinstance(stmt, astnodes.Fornum):
            # Infer types for start, stop, step
            start_type = self._infer_expression(stmt.start)
            self._infer_expression(stmt.stop)
            if stmt.step and isinstance(stmt.step, astnodes.Node):
                self._infer_expression(stmt.step)

            # Infer type for loop target variable
            if hasattr(stmt.target, 'id'):
                var_name = stmt.target.id
                # Don't define the symbol here, just infer its type
                # The symbol will be defined during code generation
                self._merge_type(var_name, start_type)

            # Infer body statements
            for s in stmt.body.body:
                self._infer_statement(s)
        elif isinstance(stmt, astnodes.Return):
            for v in (stmt.values or []):
                self._infer_expression(v)

    def _infer_local_assign(self, stmt: astnodes.LocalAssign) -> None:
        """Infer types from local variable assignment"""
        for i, target in enumerate(stmt.targets):
            if hasattr(target, 'id'):
                var_name = target.id
                if i < len(stmt.values):
                    value_type = self._infer_expression(stmt.values[i])
                    self._merge_type(var_name, value_type)
                    
                    # Track table info for array-like tables
                    if (value_type.kind == TypeKind.TABLE and
                        isinstance(stmt.values[i], astnodes.Table)):
                        self._infer_table_constructor(var_name, stmt.values[i])
                else:
                    self._merge_type(var_name, Type(TypeKind.NIL))

    def _infer_assign(self, stmt: astnodes.Assign) -> None:
        """Infer types from assignment"""
        for i, (target, value) in enumerate(zip(stmt.targets, stmt.values)):
            if isinstance(target, astnodes.Name):
                value_type = self._infer_expression(value)
                self._merge_type(target.id, value_type)
            elif isinstance(target, astnodes.Index):
                self._infer_table_index(target, value)

    def _infer_local_function(self, stmt: astnodes.LocalFunction) -> None:
        """Infer types from local function definition"""
        func_name = stmt.name.id if hasattr(stmt.name, 'id') else "anonymous"
        self._merge_type(func_name, Type(TypeKind.FUNCTION))

        # Initialize parameter symbols
        for param in stmt.args:
            if hasattr(param, 'id'):
                self._merge_type(param.id, Type(TypeKind.UNKNOWN))

        # Register function signature (if not already registered)
        # This ensures signature exists before analyzing body
        if not self.func_registry.has_function(func_name):
            param_names = [p.id for p in stmt.args if hasattr(p, 'id')]
            self.func_registry.register_function(func_name, param_names, is_local=True)

        # Track current function for call site recording
        self._current_function = func_name

        # Infer function body
        for s in stmt.body.body:
            self._infer_statement(s)

        # Reset current function
        self._current_function = None

        # Heuristic: if parameters are used with array indexing (read or write), mark them as arrays
        for s in stmt.body.body:
            self._track_param_array_usage(stmt.args, s, func_name)

    def _infer_expression(self, expr: astnodes.Node, parent_expr: Optional[astnodes.Node] = None) -> Type:
        """Infer type of an expression"""
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
        elif isinstance(expr, astnodes.Nil):
            type_info = Type(TypeKind.NIL, is_constant=True)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Name):
            type_info = self._get_symbol_type(expr.id)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Call):
            # Track call site for inter-procedural analysis
            func_name = self._get_function_name(expr)
            arg_symbols = [self._extract_arg_name(arg) for arg in expr.args]

            if func_name:
                # Record this call site (including module-level calls)
                caller_name = self._current_function or "<module>"
                self.func_registry.record_call_site(
                    caller=caller_name,
                    callee=func_name,
                    arg_symbols=arg_symbols,
                    line=expr.line if hasattr(expr, 'line') else None
                )

            # Infer types for function and arguments
            self._infer_expression(expr.func, parent_expr=expr)
            for arg in expr.args:
                self._infer_expression(arg, parent_expr=expr)

            type_info = Type(TypeKind.UNKNOWN)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Table):
            type_info = Type(TypeKind.TABLE)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Index):
            element_type = self._infer_table_index(expr, parent_expr=parent_expr)
            type_info = element_type
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.AnonymousFunction):
            type_info = Type(TypeKind.FUNCTION)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, (astnodes.AddOp, astnodes.SubOp, astnodes.MultOp,
                                astnodes.FloatDivOp, astnodes.FloorDivOp,
                                astnodes.ModOp, astnodes.ExpoOp)):
            left_type = self._infer_expression(expr.left, parent_expr=expr)
            right_type = self._infer_expression(expr.right, parent_expr=expr)
            type_info = self._infer_arithmetic_result(left_type, right_type)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, (astnodes.Concat,)):
            left_type = self._infer_expression(expr.left, parent_expr=expr)
            right_type = self._infer_expression(expr.right, parent_expr=expr)
            type_info = Type(TypeKind.STRING)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, (astnodes.EqToOp, astnodes.NotEqToOp, astnodes.LessThanOp,
                                astnodes.LessOrEqThanOp, astnodes.GreaterThanOp,
                                astnodes.GreaterOrEqThanOp)):
            type_info = Type(TypeKind.BOOLEAN)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, (astnodes.AndLoOp, astnodes.OrLoOp)):
            left_type = self._infer_expression(expr.left)
            right_type = self._infer_expression(expr.right)
            type_info = self._merge_two_types(left_type, right_type)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.UMinusOp):
            type_info = self._infer_expression(expr.operand)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.ULNotOp):
            type_info = Type(TypeKind.BOOLEAN)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.ULengthOP):
            type_info = Type(TypeKind.NUMBER)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Dots):
            type_info = Type(TypeKind.UNKNOWN)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Field):
            type_info = self._infer_expression(expr.value)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Invoke):
            type_info = Type(TypeKind.UNKNOWN)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info

        type_info = Type(TypeKind.UNKNOWN)
        ASTAnnotationStore.set_type(expr, type_info)
        return type_info

    def _get_expression_type(self, expr: astnodes.Node) -> Type:
        """Get type for an expression (public interface for generators)"""
        type_info = ASTAnnotationStore.get_type(expr)
        if type_info is None:
            type_info = Type(TypeKind.UNKNOWN)
        return type_info

    def expression_requires_lua_value(self, expr: astnodes.Node) -> bool:
        """Check if expression requires luaValue wrapper (public interface)"""
        return ASTAnnotationStore.get_requires_lua_value(expr)

    def _infer_arithmetic_result(self, left: Type, right: Type) -> Type:
        """Infer result type of arithmetic operation"""
        if left.kind == TypeKind.NUMBER and right.kind == TypeKind.NUMBER:
            return Type(TypeKind.NUMBER)
        return Type(TypeKind.UNKNOWN)

    def _merge_two_types(self, left: Type, right: Type) -> Type:
        """Merge two types into one"""
        if left.kind == right.kind:
            return Type(left.kind)
        elif left.kind == TypeKind.UNKNOWN:
            return right
        elif right.kind == TypeKind.UNKNOWN:
            return left
        else:
            return Type(TypeKind.VARIANT, subtypes=[left, right])

    def _infer_table_index(self, index_expr: astnodes.Index, value_expr: Optional[astnodes.Node] = None, parent_expr: Optional[astnodes.Node] = None) -> Type:
        """Analyze table indexing to determine array vs map

        Handles both regular variables and function parameters.
        For function parameters, updates table info in the function registry.

        Args:
            index_expr: Index expression (table[idx])
            value_expr: Value expression (for assignments like t[i] = val)
            parent_expr: Parent expression to infer element type from usage context

        Returns:
            Inferred element type (or UNKNOWN if unknown)
        """
        table_name = self._get_table_name(index_expr.value)
        if not table_name:
            return Type(TypeKind.UNKNOWN)

        # Check if this is a function parameter
        is_param = False
        param_index = -1
        if self._current_function:
            signature = self.func_registry.get_signature(self._current_function)
            if signature:
                param_index = signature.get_param_index(table_name)
                if param_index is not None:
                    is_param = True

        # Update table info for regular variables
        if not is_param:
            if table_name not in self.table_info:
                self.table_info[table_name] = TableTypeInfo()
            info = self.table_info[table_name]
        else:
            # Get or create parameter table info
            param_info = self.func_registry.get_param_table_info(
                self._current_function, param_index
            )
            if not param_info:
                param_info = TableTypeInfo()
                self.func_registry.update_param_table_info(
                    self._current_function, param_index, param_info
                )
            info = param_info

        # Track key usage
        key_expr = index_expr.idx
        if isinstance(key_expr, astnodes.Number):
            key_num = int(key_expr.n)
            if 1 <= key_num <= 10000:
                info.has_numeric_keys.add(key_num)
        elif isinstance(key_expr, astnodes.String):
            string_val = key_expr.s.decode() if isinstance(key_expr.s, bytes) else key_expr.s
            info.has_string_keys.add(string_val)
        elif isinstance(key_expr, astnodes.Name):
            # Field access like t.key is equivalent to t["key"]
            # Only track as string key if notation is DOT (not SQUARE bracket)
            if hasattr(index_expr, 'notation'):
                from luaparser.astnodes import IndexNotation
                if index_expr.notation == IndexNotation.DOT:
                    info.has_string_keys.add(key_expr.id)

        # Infer value type from assigned value
        if value_expr:
            value_type = self._infer_expression(value_expr)
            if info.value_type is None:
                info.value_type = value_type
            elif info.value_type.kind != value_type.kind:
                # Merge conflicting types into VARIANT
                info.value_type = Type(TypeKind.VARIANT, subtypes=[info.value_type, value_type])
        elif parent_expr and info.value_type is None:
            # No explicit value, but we have parent context - infer element type from usage
            if isinstance(parent_expr, (astnodes.AddOp, astnodes.SubOp, astnodes.MultOp,
                                        astnodes.FloatDivOp, astnodes.FloorDivOp,
                                        astnodes.ModOp, astnodes.ExpoOp)):
                # Used in arithmetic - element type is NUMBER
                info.value_type = Type(TypeKind.NUMBER)
            elif isinstance(parent_expr, astnodes.Concat):
                # Used in string concatenation - element type is STRING
                info.value_type = Type(TypeKind.STRING)

        # Return the inferred element type
        return info.value_type if info.value_type else Type(TypeKind.UNKNOWN)

    def _get_table_name(self, expr: astnodes.Node) -> Optional[str]:
        """Get the name of a table from an expression"""
        if isinstance(expr, astnodes.Name):
            return expr.id
        return None

    def _infer_table_constructor(self, var_name: str, table_expr: astnodes.Table) -> None:
        """Infer table structure from constructor"""
        # Initialize table info if not exists
        if var_name not in self.table_info:
            self.table_info[var_name] = TableTypeInfo()
        
        info = self.table_info[var_name]
        
        # Analyze array-part of table
        if not hasattr(table_expr, 'fields'):
            return
        
        # Check if it's an array (sequential numeric indices starting from 1)
        is_array = True
        expected_index = 1
        element_types = set()
        
        for field in table_expr.fields:
            # Check for explicit keys
            if hasattr(field, 'key') and field.key:
                is_array = False
                break
            
            # Track element types
            if hasattr(field, 'value'):
                value_type = self._infer_expression(field.value)
                if value_type.kind != TypeKind.UNKNOWN:
                    element_types.add(value_type.kind)
        
        # Determine if uniform type
        if len(element_types) == 1:
            info.value_type = Type(next(iter(element_types)))
        elif len(element_types) > 1:
            info.value_type = Type(TypeKind.VARIANT, 
                                   subtypes=[Type(k) for k in element_types])
        
        info.is_array = is_array
        info.has_numeric_keys = set(range(1, len(table_expr.fields) + 1)) if is_array else set()
    
    def _merge_type(self, symbol: str, new_type: Type) -> None:
        """Merge new type information for a symbol"""
        if symbol not in self.seen_types:
            self.seen_types[symbol] = set()

        if new_type.kind != TypeKind.UNKNOWN:
            self.seen_types[symbol].add(new_type.kind)

        seen = self.seen_types[symbol]

        if len(seen) == 0:
            self.inferred_types[symbol] = Type(TypeKind.UNKNOWN)
        elif len(seen) == 1:
            kind = next(iter(seen))
            if kind == TypeKind.NIL:
                self.inferred_types[symbol] = Type(TypeKind.UNKNOWN)
            else:
                self.inferred_types[symbol] = Type(kind)
        else:
            variant_types = [Type(kind) for kind in seen]
            self.inferred_types[symbol] = Type(TypeKind.VARIANT, subtypes=variant_types)

    def _get_symbol_type(self, name: str) -> Type:
        """Get inferred type for a symbol"""
        if name in self.inferred_types:
            return self.inferred_types[name]
        return Type(TypeKind.UNKNOWN)

    def get_type(self, symbol: str) -> Type:
        """Get type for a symbol (external interface)"""
        return self._get_symbol_type(symbol)

    def get_table_info(self, symbol: str) -> Optional[TableTypeInfo]:
        """Get table type info for a symbol"""
        if symbol in self.table_info:
            self.table_info[symbol].is_array = self.table_info[symbol].finalize_array()
        return self.table_info.get(symbol)

    def _track_param_array_usage(self, params: list, stmt: astnodes.Node, func_name: str) -> None:
        """Track if function parameters are used as arrays (heuristic for Fix 4)

        Analyzes statements within function bodies to detect when parameters
        are used with array indexing, marking them as typed arrays.
        Also infers element types from arithmetic operations.

        Args:
            params: List of function parameter AST nodes
            stmt: Statement to analyze for parameter usage
            func_name: Name of function containing these parameters
        """
        param_names = {p.id for p in params if hasattr(p, 'id')}

        # Check if this statement uses array indexing on parameters (both read and write)
        def check_for_param_array_index(node):
            if isinstance(node, astnodes.Index):
                if isinstance(node.value, astnodes.Name) and node.value.id in param_names:
                    # Parameter used with array indexing - mark as array
                    param_name = node.value.id
                    param_index = self.func_registry.get_signature(func_name).get_param_index(param_name)

                    if param_index is not None:
                        param_info = self.func_registry.get_param_table_info(func_name, param_index)
                        if param_info is None:
                            # Create table info for this parameter
                            table_info = TableTypeInfo()
                            table_info.is_array = True
                            # Infer element type from context if available
                            # Check if parameter is used in arithmetic operations
                            # This is handled in _infer_table_index
                            self.func_registry.update_param_table_info(func_name, param_index, table_info)
                        else:
                            # Ensure array flag is set
                            param_info.is_array = True

            # Recursively check children
            if hasattr(node, 'left'):
                check_for_param_array_index(node.left)
            if hasattr(node, 'right'):
                check_for_param_array_index(node.right)
            if hasattr(node, 'body'):
                for s in node.body.body:
                    check_for_param_array_index(s)
            if hasattr(node, 'target'):
                check_for_param_array_index(node.target)
            if hasattr(node, 'test'):
                check_for_param_array_index(node.test)
            if hasattr(node, 'expr'):
                check_for_param_array_index(node.expr)
            if hasattr(node, 'args'):
                for arg in node.args:
                    check_for_param_array_index(arg)
            if hasattr(node, 'values'):
                for val in node.values:
                    check_for_param_array_index(val)
            if hasattr(node, 'targets'):
                for t in node.targets:
                    check_for_param_array_index(t)

        check_for_param_array_index(stmt)

    def _get_function_name(self, call_expr: astnodes.Call) -> Optional[str]:
        """Extract function name from a call expression

        Handles simple name-based calls only. Complex expressions
        (e.g., "obj.method()", "table[key]()") are not supported
        for type propagation.

        Args:
            call_expr: Call AST node

        Returns:
            Function name or None if not a simple name
        """
        if isinstance(call_expr.func, astnodes.Name):
            return call_expr.func.id
        return None

    def _extract_arg_name(self, arg_expr: astnodes.Node) -> Optional[str]:
        """Extract symbol name from an argument expression

        Only extracts names for simple identifier arguments.
        Complex expressions return None.

        Args:
            arg_expr: Argument expression AST node

        Returns:
            Symbol name or None if not a simple name
        """
        if isinstance(arg_expr, astnodes.Name):
            return arg_expr.id
        return None

    def _mark_expr_chain_requires_lua_value(self, expr: astnodes.Node) -> None:
        """Mark an entire expression chain as requiring luaValue"""
        ASTAnnotationStore.set_requires_lua_value(expr, True)

        if isinstance(expr, astnodes.Name):
            return
        elif isinstance(expr, astnodes.Number):
            return
        elif isinstance(expr, astnodes.String):
            return
        elif isinstance(expr, astnodes.TrueExpr) or isinstance(expr, astnodes.FalseExpr):
            return
        elif isinstance(expr, astnodes.Nil):
            return
        elif isinstance(expr, astnodes.Call):
            self._mark_expr_chain_requires_lua_value(expr.func)
            for arg in expr.args:
                self._mark_expr_chain_requires_lua_value(arg)
        elif isinstance(expr, astnodes.Index):
            self._mark_expr_chain_requires_lua_value(expr.value)
            self._mark_expr_chain_requires_lua_value(expr.idx)
        elif isinstance(expr, astnodes.AnonymousFunction):
            return
        elif isinstance(expr, (astnodes.AddOp, astnodes.SubOp, astnodes.MultOp,
                                astnodes.FloatDivOp, astnodes.FloorDivOp,
                                astnodes.ModOp, astnodes.ExpoOp)):
            self._mark_expr_chain_requires_lua_value(expr.left)
            self._mark_expr_chain_requires_lua_value(expr.right)
        elif isinstance(expr, astnodes.Concat):
            self._mark_expr_chain_requires_lua_value(expr.left)
            self._mark_expr_chain_requires_lua_value(expr.right)
        elif isinstance(expr, (astnodes.EqToOp, astnodes.NotEqToOp, astnodes.LessThanOp,
                                astnodes.LessOrEqThanOp, astnodes.GreaterThanOp,
                                astnodes.GreaterOrEqThanOp)):
            self._mark_expr_chain_requires_lua_value(expr.left)
            self._mark_expr_chain_requires_lua_value(expr.right)
        elif isinstance(expr, (astnodes.AndLoOp, astnodes.OrLoOp)):
            self._mark_expr_chain_requires_lua_value(expr.left)
            self._mark_expr_chain_requires_lua_value(expr.right)
        elif isinstance(expr, astnodes.UMinusOp):
            self._mark_expr_chain_requires_lua_value(expr.operand)
        elif isinstance(expr, astnodes.ULNotOp):
            self._mark_expr_chain_requires_lua_value(expr.operand)
        elif isinstance(expr, astnodes.ULengthOP):
            self._mark_expr_chain_requires_lua_value(expr.operand)
