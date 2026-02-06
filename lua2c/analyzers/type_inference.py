"""Type inference analyzer for Lua2C

Walks AST and infers types for all variables and expressions.
Tracks type usage to determine if types are stable or dynamic.
"""

from typing import Dict, Set, Optional, List
from lua2c.core.context import TranslationContext
from lua2c.core.type_system import Type, TypeKind, TableTypeInfo
from lua2c.core.ast_annotation import ASTAnnotationStore
from luaparser import astnodes


class TypeInference:
    """Infers types from Lua AST"""

    def __init__(self, context: TranslationContext) -> None:
        self.context = context
        self.inferred_types: Dict[str, Type] = {}
        self.table_info: Dict[str, TableTypeInfo] = {}
        self.seen_types: Dict[str, Set[TypeKind]] = {}

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
            type_info = Type(TypeKind.UNKNOWN)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Table):
            type_info = Type(TypeKind.TABLE)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, astnodes.Index):
            self._infer_table_index(expr)
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
            right_type = self._infer_expression(expr.right)
            type_info = self._infer_arithmetic_result(left_type, right_type)
            ASTAnnotationStore.set_type(expr, type_info)
            return type_info
        elif isinstance(expr, (astnodes.Concat,)):
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
