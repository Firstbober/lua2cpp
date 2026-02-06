"""Type inference analyzer for Lua2C

Walks AST and infers types for all variables and expressions.
Tracks type usage to determine if types are stable or dynamic.
"""

from typing import Dict, Set, Optional, List
from lua2c.core.context import TranslationContext
from lua2c.core.type_system import Type, TypeKind, TableTypeInfo
from luaparser import astnodes


class TypeInference:
    """Infers types from Lua AST"""

    def __init__(self, context: TranslationContext) -> None:
        self.context = context
        self.inferred_types: Dict[str, Type] = {}
        self.table_info: Dict[str, TableTypeInfo] = {}
        self.seen_types: Dict[str, Set[TypeKind]] = {}
        self.expr_types: Dict[int, Type] = {}
        self.expr_requires_lua_value: Dict[int, bool] = {}
        self.expr_counter = 0

    def infer_chunk(self, chunk: astnodes.Chunk) -> None:
        """Perform type inference on entire chunk"""
        for stmt in chunk.body.body:
            self._infer_statement(stmt)

    def _infer_statement(self, stmt: astnodes.Node) -> None:
        """Infer types in a statement"""
        if isinstance(stmt, astnodes.LocalAssign):
            self._infer_local_assign(stmt)
        elif isinstance(stmt, astnodes.Assign):
            self._infer_assign(stmt)
        elif isinstance(stmt, astnodes.LocalFunction):
            self._infer_local_function(stmt)
        elif isinstance(stmt, astnodes.Call):
            self._infer_expression(stmt.func)
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
            self._infer_expression(stmt.start)
            self._infer_expression(stmt.stop)
            if stmt.step:
                self._infer_expression(stmt.step)
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

        for param in stmt.args:
            if hasattr(param, 'id'):
                self._merge_type(param.id, Type(TypeKind.UNKNOWN))

        for s in stmt.body.body:
            self._infer_statement(s)

    def _infer_expression(self, expr: astnodes.Node) -> Type:
        """Infer type of an expression"""
        if isinstance(expr, astnodes.Number):
            return Type(TypeKind.NUMBER, is_constant=True)
        elif isinstance(expr, astnodes.String):
            return Type(TypeKind.STRING, is_constant=True)
        elif isinstance(expr, astnodes.TrueExpr) or isinstance(expr, astnodes.FalseExpr):
            return Type(TypeKind.BOOLEAN, is_constant=True)
        elif isinstance(expr, astnodes.Nil):
            return Type(TypeKind.NIL, is_constant=True)
        elif isinstance(expr, astnodes.Name):
            return self._get_symbol_type(expr.id)
        elif isinstance(expr, astnodes.Call):
            return Type(TypeKind.UNKNOWN)
        elif isinstance(expr, astnodes.Table):
            return Type(TypeKind.TABLE)
        elif isinstance(expr, astnodes.Index):
            self._infer_table_index(expr)
            return Type(TypeKind.UNKNOWN)
        elif isinstance(expr, astnodes.AnonymousFunction):
            return Type(TypeKind.FUNCTION)
        elif isinstance(expr, (astnodes.AddOp, astnodes.SubOp, astnodes.MultOp,
                                astnodes.FloatDivOp, astnodes.FloorDivOp,
                                astnodes.ModOp, astnodes.ExpoOp)):
            left_type = self._infer_expression(expr.left)
            right_type = self._infer_expression(expr.right)
            return self._infer_arithmetic_result(left_type, right_type)
        elif isinstance(expr, (astnodes.Concat,)):
            return Type(TypeKind.STRING)
        elif isinstance(expr, (astnodes.EqToOp, astnodes.NotEqToOp, astnodes.LessThanOp,
                                astnodes.LessOrEqThanOp, astnodes.GreaterThanOp,
                                astnodes.GreaterOrEqThanOp)):
            return Type(TypeKind.BOOLEAN)
        elif isinstance(expr, (astnodes.AndLoOp, astnodes.OrLoOp)):
            left_type = self._infer_expression(expr.left)
            right_type = self._infer_expression(expr.right)
            return self._merge_two_types(left_type, right_type)
        elif isinstance(expr, astnodes.UMinusOp):
            return self._infer_expression(expr.operand)
        elif isinstance(expr, astnodes.ULNotOp):
            return Type(TypeKind.BOOLEAN)
        elif isinstance(expr, astnodes.ULengthOP):
            return Type(TypeKind.NUMBER)
        elif isinstance(expr, astnodes.Dots):
            return Type(TypeKind.UNKNOWN)
        elif isinstance(expr, astnodes.Field):
            return self._infer_expression(expr.value)
        elif isinstance(expr, astnodes.Invoke):
            return Type(TypeKind.UNKNOWN)

        return Type(TypeKind.UNKNOWN)

    def _get_expression_type(self, expr: astnodes.Node) -> Type:
        """Get type for an expression (public interface for generators)"""
        expr_id = self._get_expr_id(expr)

        import sys
        print(f"DEBUG TypeInference._get_expression_type: expr_id={expr_id}, in_cache={expr_id in self.expr_types}", file=sys.stderr)

        # If not found in cache, infer it
        if expr_id not in self.expr_types:
            self._infer_expression_with_context(expr)

        result = self.expr_types.get(expr_id, Type(TypeKind.UNKNOWN))
        print(f"DEBUG TypeInference._get_expression_type: result={result}", file=sys.stderr)
        return result

    def expression_requires_lua_value(self, expr: astnodes.Node) -> bool:
        """Check if expression requires luaValue wrapper (public interface)"""
        return self._expr_requires_lua_value(expr)

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

    def _infer_table_index(self, index_expr: astnodes.Index, value_expr: Optional[astnodes.Node] = None) -> None:
        """Analyze table indexing to determine array vs map"""
        table_name = self._get_table_name(index_expr.value)
        if not table_name:
            return

        if table_name not in self.table_info:
            self.table_info[table_name] = TableTypeInfo()

        info = self.table_info[table_name]

        key_expr = index_expr.idx
        if isinstance(key_expr, astnodes.Number):
            key_num = int(key_expr.n)
            if 1 <= key_num <= 10000:
                info.has_numeric_keys.add(key_num)
        elif isinstance(key_expr, astnodes.String):
            string_val = key_expr.s.decode() if isinstance(key_expr.s, bytes) else key_expr.s
            info.has_string_keys.add(string_val)

        if value_expr:
            value_type = self._infer_expression(value_expr)
            if info.value_type is None:
                info.value_type = value_type
            elif info.value_type.kind != value_type.kind:
                info.value_type = Type(TypeKind.VARIANT, subtypes=[info.value_type, value_type])

    def _get_table_name(self, expr: astnodes.Node) -> Optional[str]:
        """Get the name of a table from an expression"""
        if isinstance(expr, astnodes.Name):
            return expr.id
        return None

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

    def _get_expr_id(self, expr: astnodes.Node) -> int:
        """Get unique ID for an expression node"""
        return id(expr)

    def _infer_expression_with_context(self, expr: astnodes.Node) -> Type:
        """Infer expression type with context tracking"""
        expr_id = self._get_expr_id(expr)
        expr_type = self._infer_expression(expr)
        self.expr_types[expr_id] = expr_type
        return expr_type

    def _mark_expression_requires_lua_value(self, expr: astnodes.Node) -> None:
        """Mark that an expression must use luaValue wrapper"""
        expr_id = self._get_expr_id(expr)
        self.expr_requires_lua_value[expr_id] = True

    def _expr_requires_lua_value(self, expr: astnodes.Node) -> bool:
        """Check if expression requires luaValue wrapper"""
        expr_id = self._get_expr_id(expr)
        return self.expr_requires_lua_value.get(expr_id, False)

    def _get_expression_context_type(self, expr: astnodes.Node) -> Type:
        """Get the expected type for an expression in its context"""
        expr_id = self._get_expr_id(expr)
        if expr_id in self.expr_types:
            return self.expr_types[expr_id]

        if expr_id in self.expr_requires_lua_value:
            return Type(TypeKind.UNKNOWN)

        return Type(TypeKind.UNKNOWN)

    def _mark_expr_chain_requires_lua_value(self, expr: astnodes.Node) -> None:
        """Mark an entire expression chain as requiring luaValue"""
        self._mark_expression_requires_lua_value(expr)

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
