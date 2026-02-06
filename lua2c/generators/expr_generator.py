"""Expression generator for Lua2C transpiler

Translates Lua expressions to C++ code.
Handles all expression types: literals, variables, operations, calls, etc.
"""

from typing import Optional
from lua2c.core.context import TranslationContext
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
        return f'luaValue(string_pool[{index}])'

    def visit_Nil(self, expr: astnodes.Nil) -> str:
        """Generate code for nil

        Args:
            expr: Nil node

        Returns:
            C++ code for nil
        """
        return "luaValue()"

    def visit_TrueExpr(self, expr: astnodes.TrueExpr) -> str:
        """Generate code for true

        Args:
            expr: TrueExpr node

        Returns:
            C++ code for true
        """
        return "luaValue(true)"

    def visit_FalseExpr(self, expr: astnodes.FalseExpr) -> str:
        """Generate code for false

        Args:
            expr: FalseExpr node

        Returns:
            C++ code for false
        """
        return "luaValue(false)"

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
        left = self.generate_with_parentheses(expr.left, 'AddOp')
        right = self.generate_with_parentheses(expr.right, 'AddOp')
        return f"{left} + {right}"

    def visit_SubOp(self, expr: astnodes.SubOp) -> str:
        """Generate code for subtraction operation"""
        left = self.generate_with_parentheses(expr.left, 'SubOp')
        right = self.generate_with_parentheses(expr.right, 'SubOp')
        return f"{left} - {right}"

    def visit_MultOp(self, expr: astnodes.MultOp) -> str:
        """Generate code for multiplication operation"""
        left = self.generate_with_parentheses(expr.left, 'MultOp')
        right = self.generate_with_parentheses(expr.right, 'MultOp')
        return f"{left} * {right}"

    def visit_FloatDivOp(self, expr: astnodes.FloatDivOp) -> str:
        """Generate code for division operation"""
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
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"{left} == {right}"

    def visit_NotEqToOp(self, expr: astnodes.NotEqToOp) -> str:
        """Generate code for inequality operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"{left} != {right}"

    def visit_LessThanOp(self, expr: astnodes.LessThanOp) -> str:
        """Generate code for less-than operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"{left} < {right}"

    def visit_LessOrEqThanOp(self, expr: astnodes.LessOrEqThanOp) -> str:
        """Generate code for less-than-or-equal operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"{left} <= {right}"

    def visit_GreaterThanOp(self, expr: astnodes.GreaterThanOp) -> str:
        """Generate code for greater-than operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"{left} > {right}"

    def visit_GreaterOrEqThanOp(self, expr: astnodes.GreaterOrEqThanOp) -> str:
        """Generate code for greater-than-or-equal operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"{left} >= {right}"

    def visit_Concat(self, expr: astnodes.Concat) -> str:
        """Generate code for string concatenation"""
        left = self.generate_with_parentheses(expr.left, 'Concat')
        right = self.generate_with_parentheses(expr.right, 'Concat')
        return f"l2c_concat({left}, {right})"

    def visit_AndLoOp(self, expr: astnodes.AndLoOp) -> str:
        """Generate code for logical and (short-circuit)

        Lua's 'and': return right if left is truthy, else return left
        C++: left.is_truthy() ? right : left

        Note: This uses a lambda to avoid double evaluation of expressions with side effects.
        """
        left_has_side_effects = self._has_side_effects(expr.left)
        right_has_side_effects = self._has_side_effects(expr.right)

        if left_has_side_effects or right_has_side_effects:
            left = self.generate_with_parentheses(expr.left, 'AndLoOp')
            right = self.generate_with_parentheses(expr.right, 'AndLoOp')
            return f"[&]() {{ auto _l2c_tmp_left = {left}; auto _l2c_tmp_right = {right}; return _l2c_tmp_left.is_truthy() ? _l2c_tmp_right : _l2c_tmp_left; }}()"
        else:
            left = self.generate_with_parentheses(expr.left, 'AndLoOp')
            right = self.generate_with_parentheses(expr.right, 'AndLoOp')
            return f"({left}).is_truthy() ? ({right}) : ({left})"

    def visit_OrLoOp(self, expr: astnodes.OrLoOp) -> str:
        """Generate code for logical or (short-circuit)

        Lua's 'or': return left if left is truthy, else return right
        C++: left.is_truthy() ? left : right

        Note: This uses a lambda to avoid double evaluation of expressions with side effects.
        """
        left_has_side_effects = self._has_side_effects(expr.left)
        right_has_side_effects = self._has_side_effects(expr.right)

        if left_has_side_effects or right_has_side_effects:
            left = self.generate_with_parentheses(expr.left, 'OrLoOp')
            right = self.generate_with_parentheses(expr.right, 'OrLoOp')
            return f"[&]() {{ auto _l2c_tmp_left = {left}; auto _l2c_tmp_right = {right}; return _l2c_tmp_left.is_truthy() ? _l2c_tmp_left : _l2c_tmp_right; }}()"
        else:
            left = self.generate_with_parentheses(expr.left, 'OrLoOp')
            right = self.generate_with_parentheses(expr.right, 'OrLoOp')
            return f"({left}).is_truthy() ? ({left}) : ({right})"

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
        args = ", ".join([self.generate(arg) for arg in expr.args])
        
        # Check if this is a local function call (needs state parameter)
        if isinstance(expr.func, astnodes.Name):
            symbol = self.context.resolve_symbol(expr.func.id)
            if symbol and not symbol.is_global:
                # Local function: func(state, arg1, arg2, ...)
                return f"{func}(state, {args})"
        
        # Global/library function: func({arg1, arg2, ...})
        return f"({func})({{{args}}})"

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

    def visit_Index(self, expr: astnodes.Index) -> str:
        """Generate code for table index (table[key])"""
        if self._is_library_function_index(expr):
            lib_name = expr.value.id
            func_name = expr.idx.id
            return f'state->get_global("{lib_name}.{func_name}")'

        table = self.generate(expr.value)
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
        return "luaValue::new_table()"

    def visit_AnonymousFunction(self, expr: astnodes.AnonymousFunction) -> str:
        """Generate code for anonymous function"""
        return "luaValue::new_closure()"

    def visit_Dots(self, expr: astnodes.Dots) -> str:
        """Generate code for varargs"""
        return "luaValue::varargs()"

    def visit_Function(self, expr: astnodes.Function) -> str:
        """Generate code for function definition"""
        raise NotImplementedError("Function definitions not yet implemented")
