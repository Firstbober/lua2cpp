"""Expression generator for Lua2C transpiler

Translates Lua expressions to C++ code.
Handles all expression types: literals, variables, operations, calls, etc.
"""

from typing import Optional
from lua2c.core.context import TranslationContext
from lua2c.core.type_system import Type, TypeKind, TableTypeInfo
from lua2c.core.type_conversion import TypeConverter
from lua2c.core.ast_annotation import ASTAnnotationStore
from lua2c.generators.naming import NamingScheme
try:
    from luaparser import astnodes
except ImportError:
    raise ImportError("luaparser is required. Install with: pip install luaparser")


class ExprGenerator:
    """Generates C++ code for Lua expressions"""

    LIBRARY_FUNCTIONS = {
        'io': ['write', 'read', 'open', 'close', 'flush', 'type'],
        'string': ['format', 'sub', 'upper', 'lower', 'rep', 'find', 'match', 'gmatch', 'gsub', 'byte', 'char', 'len'],
        'math': ['abs', 'acos', 'asin', 'atan', 'ceil', 'cos', 'deg', 'exp', 'floor', 'fmod', 'log', 'max', 'min', 'modf', 'rad', 'random', 'randomseed', 'sin', 'sqrt', 'tan'],
        'table': ['insert', 'remove', 'concat', 'sort', 'pack', 'unpack'],
        'os': ['clock', 'date', 'difftime', 'time'],
    }

    PRECEDENCE = {
        'ExpoOp': 10,
        'MultOp': 9,
        'FloatDivOp': 9,
        'FloorDivOp': 9,
        'ModOp': 9,
        'AddOp': 8,
        'SubOp': 8,
        'Concat': 7,
        'LessThanOp': 6,
        'LessOrEqThanOp': 6,
        'GreaterThanOp': 6,
        'GreaterOrEqThanOp': 6,
        'EqToOp': 6,
        'NotEqToOp': 6,
        'AndLoOp': 5,
        'OrLoOp': 4,
    }

    def __init__(self, context: TranslationContext) -> None:
        """Initialize expression generator

        Args:
            context: Translation context
        """
        self.context = context
        self._type_inferencer = None
        self._expected_types = {}

    def set_type_inferencer(self, type_inferencer) -> None:
        """Set the type inferencer for expression type queries

        Args:
            type_inferencer: TypeInference instance
        """
        self._type_inferencer = type_inferencer

    def _get_inferred_expression_type(self, expr: astnodes.Node) -> Type:
        """Get inferred type for an expression

        Args:
            expr: Expression node

        Returns:
            Inferred type
        """
        type_info = ASTAnnotationStore.get_type(expr)
        if type_info is None:
            return Type(TypeKind.UNKNOWN)
        return type_info

    def _set_expected_type(self, expr: astnodes.Node, type_hint: Optional[Type]) -> None:
        """Set expected type for an expression

        Args:
            expr: Expression node
            type_hint: Expected type
        """
        if type_hint:
            expr_id = id(expr)
            self._expected_types[expr_id] = type_hint

    def _get_expected_type(self, expr: astnodes.Node) -> Optional[Type]:
        """Get expected type for an expression

        Args:
            expr: Expression node

        Returns:
            Expected type or None
        """
        expr_id = id(expr)
        return self._expected_types.get(expr_id)

    def _clear_expected_type(self, expr: astnodes.Node) -> None:
        """Clear expected type for an expression

        Args:
            expr: Expression node
        """
        expr_id = id(expr)
        self._expected_types.pop(expr_id, None)

    def _get_symbol_type(self, name: str) -> Optional[Type]:
        """Get inferred type for a symbol"""
        symbol = self.context.resolve_symbol(name)
        if symbol and hasattr(symbol, 'inferred_type') and symbol.inferred_type:
            return symbol.inferred_type
        return None

    def _get_table_info(self, name: str):
        """Get table info for a symbol"""
        symbol = self.context.resolve_symbol(name)
        if symbol and hasattr(symbol, 'table_info') and symbol.table_info:
            return symbol.table_info
        return None

    def _should_use_lua_value(self, type_hint: Optional[Type]) -> bool:
        """Check if we should use luaValue for this type"""
        if type_hint is None:
            return True  # Default to luaValue for safety
        return type_hint.kind == TypeKind.UNKNOWN or type_hint.kind == TypeKind.VARIANT

    def generate(self, expr: astnodes.Node) -> str:
        """Generate C++ code for an expression

        Args:
            expr: Expression AST node

        Returns:
            C++ code string
        """
        method_name = f"visit_{expr.__class__.__name__}"
        method = getattr(self, method_name, self._generic_visit)
        return method(expr)

    def generate_with_parentheses(self, node: astnodes.Node, parent_op: str) -> str:
        """Generate C++ code for an expression, adding parentheses if needed

        Args:
            node: Expression AST node
            parent_op: Parent operator type name (for precedence checking)

        Returns:
            C++ code string with appropriate parentheses
        """
        code = self.generate(node)
        node_op = node.__class__.__name__

        if node_op in self.PRECEDENCE and parent_op in self.PRECEDENCE:
            if self.PRECEDENCE[node_op] < self.PRECEDENCE[parent_op]:
                return f"({code})"

        return code

    def _generic_visit(self, expr: astnodes.Node) -> str:
        """Default visitor for unhandled node types

        Args:
            expr: Expression node

        Returns:
            C++ code string

        Raises:
            NotImplementedError: If node type not supported
        """
        raise NotImplementedError(
            f"Expression type {expr.__class__.__name__} not yet implemented"
        )

    def visit_Number(self, expr: astnodes.Number) -> str:
        """Generate code for number literal

        Args:
            expr: Number node

        Returns:
            C++ code for number literal
        """
        value = expr.n
        type_hint = self._get_expected_type(expr) or self._get_symbol_type_from_context(expr)

        if not self._should_use_lua_value(type_hint) and type_hint:
            return f"{value}"

        return f"luaValue({value})"

    def visit_String(self, expr: astnodes.String) -> str:
        """Generate code for string literal

        Args:
            expr: String node

        Returns:
            C++ code for string literal
        """
        string_value = expr.s.decode() if isinstance(expr.s, bytes) else expr.s
        index = self.context.add_string_literal(string_value)
        type_hint = self._get_expected_type(expr) or self._get_symbol_type_from_context(expr)

        if not self._should_use_lua_value(type_hint) and type_hint:
            return f'std::string(string_pool[{index}])'

        return f'luaValue(string_pool[{index}])'

    def visit_TrueExpr(self, expr: astnodes.TrueExpr) -> str:
        """Generate code for true

        Args:
            expr: TrueExpr node

        Returns:
            C++ code for true
        """
        type_hint = self._get_expected_type(expr) or self._get_symbol_type_from_context(expr)

        if not self._should_use_lua_value(type_hint) and type_hint:
            return "true"

        return "luaValue(true)"

    def visit_FalseExpr(self, expr: astnodes.FalseExpr) -> str:
        """Generate code for false

        Args:
            expr: FalseExpr node

        Returns:
            C++ code for false
        """
        type_hint = self._get_expected_type(expr) or self._get_symbol_type_from_context(expr)

        if not self._should_use_lua_value(type_hint) and type_hint:
            return "false"

        return "luaValue(false)"

    def _get_symbol_type_from_context(self, expr: astnodes.Node) -> Optional[Type]:
        """Get type hint from surrounding context"""
        return None

    def visit_Nil(self, expr: astnodes.Nil) -> str:
        """Generate code for nil

        Args:
            expr: Nil node

        Returns:
            C++ code for nil
        """
        return "luaValue()"

    def visit_Name(self, expr: astnodes.Name) -> str:
        """Generate code for variable reference

        Args:
            expr: Name node

        Returns:
            C++ code for variable reference
        """
        name = expr.id
        symbol = self.context.resolve_symbol(name)

        if symbol is None:
            return f'state->get_global("{name}")'

        if symbol.is_global:
            return f'state->get_global("{name}")'
        else:
            return name

    def visit_AddOp(self, expr: astnodes.AddOp) -> str:
        """Generate code for addition operation"""
        left_type = self._get_inferred_expression_type(expr.left)
        right_type = self._get_inferred_expression_type(expr.right)
        result_type = self._get_expected_type(expr) or self._get_inferred_expression_type(expr)

        # Set expected type for this result expression (Fix 2)
        if result_type and result_type.kind == TypeKind.NUMBER:
            self._set_expected_type(expr, result_type)
        else:
            self._set_expected_type(expr, Type(TypeKind.NUMBER))

        # Set expected types for operands BEFORE checking (fixes order bug)
        # This ensures recursive calls can use the expected type as a hint
        left_type_hint = left_type if left_type.kind == TypeKind.NUMBER else Type(TypeKind.NUMBER)
        right_type_hint = right_type if right_type.kind == TypeKind.NUMBER else Type(TypeKind.NUMBER)
        self._set_expected_type(expr.left, left_type_hint)
        self._set_expected_type(expr.right, right_type_hint)

        # Get expected types for operands (use as hints when inferred is UNKNOWN)
        left_expected = self._get_expected_type(expr.left)
        right_expected = self._get_expected_type(expr.right)

        # If both operands and result are numbers (or expected to be), use native operator
        left_is_number = left_type.kind == TypeKind.NUMBER or (left_expected and left_expected.kind == TypeKind.NUMBER)
        right_is_number = right_type.kind == TypeKind.NUMBER or (right_expected and right_expected.kind == TypeKind.NUMBER)
        result_is_number = not result_type or result_type.kind == TypeKind.NUMBER

        if left_is_number and right_is_number and result_is_number:
            left = self.generate(expr.left)
            right = self.generate(expr.right)

            self._clear_expected_type(expr.left)
            self._clear_expected_type(expr.right)

            return f"{left} + {right}"

        # Otherwise use luaValue operator
        left = self.generate_with_parentheses(expr.left, 'AddOp')
        right = self.generate_with_parentheses(expr.right, 'AddOp')
        return f"{left} + {right}"

    def visit_SubOp(self, expr: astnodes.SubOp) -> str:
        """Generate code for subtraction operation"""
        left_type = self._get_inferred_expression_type(expr.left)
        right_type = self._get_inferred_expression_type(expr.right)
        result_type = self._get_expected_type(expr) or self._get_inferred_expression_type(expr)

        # Set expected type for this result expression (Fix 2)
        if result_type and result_type.kind == TypeKind.NUMBER:
            self._set_expected_type(expr, result_type)
        else:
            self._set_expected_type(expr, Type(TypeKind.NUMBER))

        # Set expected types for operands BEFORE checking (fixes order bug)
        # This ensures recursive calls can use the expected type as a hint
        left_type_hint = left_type if left_type.kind == TypeKind.NUMBER else Type(TypeKind.NUMBER)
        right_type_hint = right_type if right_type.kind == TypeKind.NUMBER else Type(TypeKind.NUMBER)
        self._set_expected_type(expr.left, left_type_hint)
        self._set_expected_type(expr.right, right_type_hint)

        # Get expected types for operands (use as hints when inferred is UNKNOWN)
        left_expected = self._get_expected_type(expr.left)
        right_expected = self._get_expected_type(expr.right)

        # If both operands and result are numbers (or expected to be), use native operator
        left_is_number = left_type.kind == TypeKind.NUMBER or (left_expected and left_expected.kind == TypeKind.NUMBER)
        right_is_number = right_type.kind == TypeKind.NUMBER or (right_expected and right_expected.kind == TypeKind.NUMBER)
        result_is_number = not result_type or result_type.kind == TypeKind.NUMBER

        if left_is_number and right_is_number and result_is_number:
            left = self.generate(expr.left)
            right = self.generate(expr.right)

            self._clear_expected_type(expr.left)
            self._clear_expected_type(expr.right)

            return f"{left} - {right}"

        # Otherwise use luaValue operator
        left = self.generate_with_parentheses(expr.left, 'SubOp')
        right = self.generate_with_parentheses(expr.right, 'SubOp')
        return f"{left} - {right}"

    def visit_MultOp(self, expr: astnodes.MultOp) -> str:
        """Generate code for multiplication operation"""
        left_type = self._get_inferred_expression_type(expr.left)
        right_type = self._get_inferred_expression_type(expr.right)
        result_type = self._get_expected_type(expr) or self._get_inferred_expression_type(expr)

        # Set expected type for this result expression (Fix 2)
        if result_type and result_type.kind == TypeKind.NUMBER:
            self._set_expected_type(expr, result_type)
        else:
            self._set_expected_type(expr, Type(TypeKind.NUMBER))

        # Set expected types for operands BEFORE checking (fixes order bug)
        # This ensures recursive calls can use the expected type as a hint
        left_type_hint = left_type if left_type.kind == TypeKind.NUMBER else Type(TypeKind.NUMBER)
        right_type_hint = right_type if right_type.kind == TypeKind.NUMBER else Type(TypeKind.NUMBER)
        self._set_expected_type(expr.left, left_type_hint)
        self._set_expected_type(expr.right, right_type_hint)

        # Get expected types for operands (use as hints when inferred is UNKNOWN)
        left_expected = self._get_expected_type(expr.left)
        right_expected = self._get_expected_type(expr.right)

        # If both operands and result are numbers (or expected to be), use native operator
        left_is_number = left_type.kind == TypeKind.NUMBER or (left_expected and left_expected.kind == TypeKind.NUMBER)
        right_is_number = right_type.kind == TypeKind.NUMBER or (right_expected and right_expected.kind == TypeKind.NUMBER)
        result_is_number = not result_type or result_type.kind == TypeKind.NUMBER

        if left_is_number and right_is_number and result_is_number:
            # Add parentheses for subtractions/divisions to preserve precedence
            left = self.generate(expr.left)
            if isinstance(expr.left, (astnodes.SubOp, astnodes.AddOp, astnodes.FloatDivOp)):
                left = f"({left})"
            right = self.generate(expr.right)
            if isinstance(expr.right, (astnodes.SubOp, astnodes.AddOp, astnodes.FloatDivOp)):
                right = f"({right})"

            self._clear_expected_type(expr.left)
            self._clear_expected_type(expr.right)

            return f"{left} * {right}"

        # Otherwise use luaValue operator
        left = self.generate_with_parentheses(expr.left, 'MultOp')
        right = self.generate_with_parentheses(expr.right, 'MultOp')
        return f"{left} * {right}"

    def visit_FloatDivOp(self, expr: astnodes.FloatDivOp) -> str:
        """Generate code for division operation"""
        left_type = self._get_inferred_expression_type(expr.left)
        right_type = self._get_inferred_expression_type(expr.right)
        result_type = self._get_expected_type(expr) or self._get_inferred_expression_type(expr)

        # Set expected type for this result expression (Fix 2)
        if result_type and result_type.kind == TypeKind.NUMBER:
            self._set_expected_type(expr, result_type)
        else:
            self._set_expected_type(expr, Type(TypeKind.NUMBER))

        # Set expected types for operands BEFORE checking (fixes order bug)
        # This ensures recursive calls can use the expected type as a hint
        left_type_hint = left_type if left_type.kind == TypeKind.NUMBER else Type(TypeKind.NUMBER)
        right_type_hint = right_type if right_type.kind == TypeKind.NUMBER else Type(TypeKind.NUMBER)
        self._set_expected_type(expr.left, left_type_hint)
        self._set_expected_type(expr.right, right_type_hint)

        # Get expected types for operands (use as hints when inferred is UNKNOWN)
        left_expected = self._get_expected_type(expr.left)
        right_expected = self._get_expected_type(expr.right)

        # If both operands and result are numbers (or expected to be), use native operator
        left_is_number = left_type.kind == TypeKind.NUMBER or (left_expected and left_expected.kind == TypeKind.NUMBER)
        right_is_number = right_type.kind == TypeKind.NUMBER or (right_expected and right_expected.kind == TypeKind.NUMBER)
        result_is_number = not result_type or result_type.kind == TypeKind.NUMBER

        if left_is_number and right_is_number and result_is_number:
            left = self.generate(expr.left)
            right = self.generate(expr.right)

            self._clear_expected_type(expr.left)
            self._clear_expected_type(expr.right)

            return f"{left} / {right}"

        # Otherwise use luaValue operator
        left = self.generate_with_parentheses(expr.left, 'FloatDivOp')
        right = self.generate_with_parentheses(expr.right, 'FloatDivOp')
        return f"{left} / {right}"

    def visit_FloorDivOp(self, expr: astnodes.FloorDivOp) -> str:
        """Generate code for floor division operation"""
        left = self.generate_with_parentheses(expr.left, 'FloorDivOp')
        right = self.generate_with_parentheses(expr.right, 'FloorDivOp')
        return f"l2c_floor_div({left}, {right})"

    def visit_ModOp(self, expr: astnodes.ModOp) -> str:
        """Generate code for modulo operation"""
        left = self.generate_with_parentheses(expr.left, 'ModOp')
        right = self.generate_with_parentheses(expr.right, 'ModOp')
        return f"{left} % {right}"

    def visit_ExpoOp(self, expr: astnodes.ExpoOp) -> str:
        """Generate code for exponentiation operation"""
        left = self.generate_with_parentheses(expr.left, 'ExpoOp')
        right = self.generate_with_parentheses(expr.right, 'ExpoOp')
        return f"l2c_pow({left}, {right})"

    def visit_EqToOp(self, expr: astnodes.EqToOp) -> str:
        """Generate code for equality operation"""
        left = self.generate_with_parentheses(expr.left, 'EqToOp')
        right = self.generate_with_parentheses(expr.right, 'EqToOp')
        return f"luaValue({left} == {right})"

    def visit_NotEqToOp(self, expr: astnodes.NotEqToOp) -> str:
        """Generate code for inequality operation"""
        left = self.generate_with_parentheses(expr.left, 'NotEqToOp')
        right = self.generate_with_parentheses(expr.right, 'NotEqToOp')
        return f"luaValue({left} != {right})"

    def visit_LessThanOp(self, expr: astnodes.LessThanOp) -> str:
        """Generate code for less-than operation"""
        left = self.generate_with_parentheses(expr.left, 'LessThanOp')
        right = self.generate_with_parentheses(expr.right, 'LessThanOp')
        return f"luaValue({left} < {right})"

    def visit_LessOrEqThanOp(self, expr: astnodes.LessOrEqThanOp) -> str:
        """Generate code for less-than-or-equal operation"""
        left = self.generate_with_parentheses(expr.left, 'LessOrEqThanOp')
        right = self.generate_with_parentheses(expr.right, 'LessOrEqThanOp')
        return f"luaValue({left} <= {right})"

    def visit_GreaterThanOp(self, expr: astnodes.GreaterThanOp) -> str:
        """Generate code for greater-than operation"""
        left = self.generate_with_parentheses(expr.left, 'GreaterThanOp')
        right = self.generate_with_parentheses(expr.right, 'GreaterThanOp')
        return f"luaValue({left} > {right})"

    def visit_GreaterOrEqThanOp(self, expr: astnodes.GreaterOrEqThanOp) -> str:
        """Generate code for greater-than-or-equal operation"""
        left = self.generate_with_parentheses(expr.left, 'GreaterOrEqThanOp')
        right = self.generate_with_parentheses(expr.right, 'GreaterOrEqThanOp')
        return f"luaValue({left} >= {right})"

    def visit_Concat(self, expr: astnodes.Concat) -> str:
        """Generate code for string concatenation"""
        left = self.generate_with_parentheses(expr.left, 'Concat')
        right = self.generate_with_parentheses(expr.right, 'Concat')
        return f"l2c_concat({left}, {right})"

    def visit_AndLoOp(self, expr: astnodes.AndLoOp) -> str:
        """Generate code for logical and (short-circuit)

        Lua's 'and': return right if left is truthy, else return left
        C++: luaValue(left.is_truthy() ? right : left)

        Note: This uses a lambda to avoid double evaluation of expressions with side effects.
        """
        left_has_side_effects = self._has_side_effects(expr.left)
        right_has_side_effects = self._has_side_effects(expr.right)

        if left_has_side_effects or right_has_side_effects:
            left = self.generate(expr.left)
            right = self.generate(expr.right)
            return f"[&]() {{ auto _l2c_tmp_left = {left}; auto _l2c_tmp_right = {right}; return luaValue(_l2c_tmp_left.is_truthy() ? _l2c_tmp_right : _l2c_tmp_left); }}()"
        else:
            left = self.generate(expr.left)
            right = self.generate(expr.right)
            return f"luaValue(({left}).is_truthy() ? ({right}) : ({left}))"

    def visit_OrLoOp(self, expr: astnodes.OrLoOp) -> str:
        """Generate code for logical or (short-circuit)

        Lua's 'or': return left if left is truthy, else return right
        C++: luaValue(left.is_truthy() ? left : right)

        Note: This uses a lambda to avoid double evaluation of expressions with side effects.
        """
        left_has_side_effects = self._has_side_effects(expr.left)
        right_has_side_effects = self._has_side_effects(expr.right)

        if left_has_side_effects or right_has_side_effects:
            left = self.generate(expr.left)
            right = self.generate(expr.right)
            return f"[&]() {{ auto _l2c_tmp_left = {left}; auto _l2c_tmp_right = {right}; return luaValue(_l2c_tmp_left.is_truthy() ? _l2c_tmp_left : _l2c_tmp_right); }}()"
        else:
            left = self.generate(expr.left)
            right = self.generate(expr.right)
            return f"luaValue(({left}).is_truthy() ? ({left}) : ({right}))"

    def visit_UMinusOp(self, expr: astnodes.UMinusOp) -> str:
        """Generate code for unary negation"""
        operand = self.generate(expr.operand)
        return f"-({operand})"

    def visit_ULNotOp(self, expr: astnodes.ULNotOp) -> str:
        """Generate code for unary logical not"""
        operand = self.generate(expr.operand)
        return f"!({operand}).is_truthy()"

    def visit_ULengthOP(self, expr: astnodes.ULengthOP) -> str:
        """Generate code for unary length"""
        operand = self.generate(expr.operand)
        return f"l2c_len({operand})"

    def visit_Call(self, expr: astnodes.Call) -> str:
        """Generate code for function call"""
        func = self.generate(expr.func)

        # Check if this is a local function call (needs state parameter)
        if isinstance(expr.func, astnodes.Name):
            symbol = self.context.resolve_symbol(expr.func.id)
            if symbol and not symbol.is_global:
                # Local function: func(state, arg1, arg2, ...)
                # Handle temporaries for non-const lvalue reference binding
                wrapped_args = []
                temp_decls = []
                temp_counter = [0]

                for arg in expr.args:
                    arg_code = self.generate(arg)
                    if self._is_temporary_expression(arg):
                        temp_name = f"_l2c_tmp_arg_{temp_counter[0]}"
                        temp_counter[0] += 1
                        temp_decls.append(f"auto {temp_name} = {arg_code}")
                        wrapped_args.append(temp_name)
                    else:
                        wrapped_args.append(arg_code)

                args_str = ", ".join(wrapped_args)
                if temp_decls:
                    # Need to wrap in block scope for temporaries
                    temps = "; ".join(temp_decls)
                    return f"[&] {{ {temps}; return {func}(state, {args_str}); }}()"
                else:
                    return f"{func}(state, {args_str})"

        # Global/library function: func({arg1, arg2, ...})
        # Need to wrap arguments in luaValue
        args = []
        for arg in expr.args:
            arg_code = self.generate(arg)
            type_hint = self._get_symbol_type_from_context(arg)
            if not self._should_use_lua_value(type_hint):
                # Need to convert to luaValue for library functions
                args.append(f"luaValue({arg_code})")
            else:
                args.append(arg_code)
        args_str = ", ".join(args)
        return f"({func})({{{args_str}}})"

    def visit_Invoke(self, expr: astnodes.Invoke) -> str:
        """Generate code for method invocation (obj:method(args))

        Lua: obj:method(args)
        C++: obj["method"]({obj, args})
        """
        source = self.generate(expr.source)
        method = self.generate(expr.func)
        args = ", ".join([self.generate(arg) for arg in expr.args])
        return f"({source})[{method}]({{{source}, {args}}})"

    def _is_library_function_index(self, expr: astnodes.Index) -> bool:
        """Check if this Index expression represents a library function access (e.g., io.write)

        Args:
            expr: Index node to check

        Returns:
            True if this is a library function access
        """
        if not isinstance(expr.value, astnodes.Name):
            return False

        if not isinstance(expr.idx, astnodes.Name):
            return False

        lib_name = expr.value.id if hasattr(expr.value, 'id') else None
        func_name = expr.idx.id if hasattr(expr.idx, 'id') else None

        if lib_name is None or func_name is None:
            return False

        return lib_name in self.LIBRARY_FUNCTIONS and func_name in self.LIBRARY_FUNCTIONS[lib_name]

    def _has_side_effects(self, expr: astnodes.Node) -> bool:
        """Check if an expression has side effects (e.g., function call, get_global)

        Args:
            expr: Expression node to check

        Returns:
            True if expression has side effects
        """
        if isinstance(expr, astnodes.Call):
            return True
        if isinstance(expr, astnodes.Name):
            name = expr.id if hasattr(expr, 'id') else None
            if name:
                symbol = self.context.resolve_symbol(name)
                if symbol is None or symbol.is_global:
                    return True
        if isinstance(expr, astnodes.Index):
            return self._has_side_effects(expr.value)
        if isinstance(expr, astnodes.Field):
            return self._has_side_effects(expr.value)
        return False

    def _is_temporary_expression(self, expr: astnodes.Node) -> bool:
        """Check if an expression generates a temporary/rvalue

        Args:
            expr: Expression node to check

        Returns:
            True if expression is an rvalue that can't bind to non-const reference
        """
        if isinstance(expr, astnodes.Table):
            return True
        if isinstance(expr, astnodes.Call):
            return True
        if isinstance(expr, astnodes.AnonymousFunction):
            return True
        if isinstance(expr, (astnodes.Number, astnodes.String, astnodes.TrueExpr, astnodes.FalseExpr, astnodes.Nil)):
            return True
        if isinstance(expr, (astnodes.AndLoOp, astnodes.OrLoOp)):
            return True
        return False

    def visit_Index(self, expr: astnodes.Index) -> str:
        """Generate code for table index (table[key])"""
        if self._is_library_function_index(expr):
            lib_name = expr.value.id
            func_name = expr.idx.id
            return f'state->get_global("{lib_name}.{func_name}")'
        
        table = self.generate(expr.value)
        
        # Check if table is a typed array
        if isinstance(expr.value, astnodes.Name):
            table_name = expr.value.id
            table_info = self._get_table_info_for_symbol(table_name)
            
            if table_info and table_info.is_array:
                # Array access - convert Lua's 1-based indexing to C++'s 0-based indexing
                key = self.generate(expr.idx)
                return f"({table})[{key} - 1]"
        
        # Default: luaValue indexing
        key = self.generate(expr.idx)
        return f"({table})[{key}]"

    def visit_Field(self, expr: astnodes.Field) -> str:
        """Generate code for table field access (table.field)"""
        table = self.generate(expr.value)
        if expr.key and isinstance(expr.key, astnodes.Name):
            field_name = expr.key.id
            index = self.context.add_string_literal(field_name)
            return f'({table})[string_pool[{index}]]'
        else:
            return f'({table})[luaValue(1)]'

    def visit_Table(self, expr: astnodes.Table) -> str:
        """Generate code for table constructor"""
        # Get table info from type inference
        table_info = self._get_table_info_from_context(expr)
        
        if not table_info:
            # Fall back to heuristics for anonymous tables
            is_array = self._is_array_table(expr)
            element_type = self._infer_array_element_type(expr)
        else:
            is_array = table_info.is_array
            element_type = table_info.value_type
        
        # Generate typed table when possible
        if is_array:
            # Handle typed array
            if element_type and element_type.can_specialize():
                cpp_type = element_type.cpp_type()
                if cpp_type == "auto":
                    return "luaValue::new_table()"
                
                # Set expected type for all elements to generate native literals
                elements = []
                if hasattr(expr, 'fields') and expr.fields:
                    for field in expr.fields:
                        if hasattr(field, 'value'):
                            self._set_expected_type(field.value, element_type)
                            elements.append(self.generate(field.value))
                            self._clear_expected_type(field.value)
                
                # Annotate the table expression with its concrete type
                # This helps downstream code generation know what type this expression has
                table_type = Type(TypeKind.TABLE)
                ASTAnnotationStore.set_type(expr, table_type)
                
                if elements:
                    return f"luaArray<{cpp_type}>{{{{{', '.join(elements)}}}}}"
                return f"luaArray<{cpp_type}>{{{{}}}}"
            # Handle array with unknown element type - use luaValue for dynamic typing
            elif element_type is None:
                return "luaValue::new_table()"
        
        # Fall back to luaValue table (for maps or unknown types)
        return "luaValue::new_table()"

    def _get_table_info_from_context(self, expr: astnodes.Node) -> Optional['TableTypeInfo']:
        """Get table info from context or annotation"""
        # First check if table_info is attached as annotation
        table_info = ASTAnnotationStore.get_annotation(expr, "table_info")
        if table_info:
            return table_info
        
        # Fall back to heuristics for anonymous tables
        return None
    
    def _get_table_info_for_symbol(self, name: str) -> Optional['TableTypeInfo']:
        """Get table info for a named symbol"""
        type_inferencer = self.context.get_type_inferencer()
        if not type_inferencer:
            return None
        return type_inferencer.get_table_info(name)

    def _is_array_table(self, expr: astnodes.Table) -> bool:
        """Check if table is an array based on heuristics"""
        if not hasattr(expr, 'fields') or not expr.fields:
            return True

        has_explicit_keys = any(hasattr(f, 'key') and f.key for f in expr.fields)
        if has_explicit_keys:
            return False

        return True

    def _infer_array_element_type(self, expr: astnodes.Table) -> Optional[Type]:
        """Infer element type for array table"""
        if not hasattr(expr, 'fields') or not expr.fields:
            return None

        seen_kinds = set()
        for field in expr.fields:
            if hasattr(field, 'value'):
                if isinstance(field.value, astnodes.Number):
                    seen_kinds.add(TypeKind.NUMBER)
                elif isinstance(field.value, astnodes.String):
                    seen_kinds.add(TypeKind.STRING)
                elif isinstance(field.value, (astnodes.TrueExpr, astnodes.FalseExpr)):
                    seen_kinds.add(TypeKind.BOOLEAN)
                elif isinstance(field.value, astnodes.Nil):
                    seen_kinds.add(TypeKind.NIL)

        if len(seen_kinds) == 1:
            return Type(next(iter(seen_kinds)))
        elif len(seen_kinds) > 1:
            return Type(TypeKind.VARIANT, subtypes=[Type(k) for k in seen_kinds])

        return None

    def visit_AnonymousFunction(self, expr: astnodes.AnonymousFunction) -> str:
        """Generate code for anonymous function"""
        return "luaValue::new_closure()"

    def visit_Dots(self, expr: astnodes.Dots) -> str:
        """Generate code for varargs"""
        return "luaValue::varargs()"

    def visit_Function(self, expr: astnodes.Function) -> str:
        """Generate code for function definition"""
        raise NotImplementedError("Function definitions not yet implemented")
