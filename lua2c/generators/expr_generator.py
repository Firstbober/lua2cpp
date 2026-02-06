"""Expression generator for Lua2C transpiler

Translates Lua expressions to C code.
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
    """Generates C code for Lua expressions"""

    def __init__(self, context: TranslationContext) -> None:
        """Initialize expression generator

        Args:
            context: Translation context
        """
        self.context = context

    def generate(self, expr: astnodes.Node) -> str:
        """Generate C code for an expression

        Args:
            expr: Expression AST node

        Returns:
            C code string
        """
        method_name = f"visit_{expr.__class__.__name__}"
        method = getattr(self, method_name, self._generic_visit)
        return method(expr)

    def _generic_visit(self, expr: astnodes.Node) -> str:
        """Default visitor for unhandled node types

        Args:
            expr: Expression node

        Returns:
            C code string

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
            C code for number literal
        """
        value = expr.n
        if isinstance(value, int):
            return f"L2C_NUMBER_INT({value})"
        elif isinstance(value, float):
            return f"L2C_NUMBER_FLOAT({value})"
        else:
            return f"L2C_NUMBER_INT({value})"

    def visit_String(self, expr: astnodes.String) -> str:
        """Generate code for string literal

        Args:
            expr: String node

        Returns:
            C code for string literal
        """
        index = self.context.add_string_literal(expr.s)
        return f"L2C_STRING_LITERAL({index})"

    def visit_Nil(self, expr: astnodes.Nil) -> str:
        """Generate code for nil

        Args:
            expr: Nil node

        Returns:
            C code for nil
        """
        return "L2C_NIL"

    def visit_TrueExpr(self, expr: astnodes.TrueExpr) -> str:
        """Generate code for true

        Args:
            expr: TrueExpr node

        Returns:
            C code for true
        """
        return "L2C_TRUE"

    def visit_FalseExpr(self, expr: astnodes.FalseExpr) -> str:
        """Generate code for false

        Args:
            expr: FalseExpr node

        Returns:
            C code for false
        """
        return "L2C_FALSE"

    def visit_Name(self, expr: astnodes.Name) -> str:
        """Generate code for variable reference

        Args:
            expr: Name node

        Returns:
            C code for variable reference
        """
        name = expr.id
        symbol = self.context.resolve_symbol(name)

        if symbol is None:
            return f"L2C_GET_GLOBAL(\"{name}\")"

        if symbol.is_global:
            return f"L2C_GET_GLOBAL(\"{name}\")"
        else:
            return name

    def visit_AddOp(self, expr: astnodes.AddOp) -> str:
        """Generate code for addition operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_ADD, {right})"

    def visit_SubOp(self, expr: astnodes.SubOp) -> str:
        """Generate code for subtraction operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_SUB, {right})"

    def visit_MultOp(self, expr: astnodes.MultOp) -> str:
        """Generate code for multiplication operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_MUL, {right})"

    def visit_FloatDivOp(self, expr: astnodes.FloatDivOp) -> str:
        """Generate code for division operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_DIV, {right})"

    def visit_FloorDivOp(self, expr: astnodes.FloorDivOp) -> str:
        """Generate code for floor division operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_FLOOR_DIV, {right})"

    def visit_ModOp(self, expr: astnodes.ModOp) -> str:
        """Generate code for modulo operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_MOD, {right})"

    def visit_ExpoOp(self, expr: astnodes.ExpoOp) -> str:
        """Generate code for exponentiation operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_POW, {right})"

    def visit_EqToOp(self, expr: astnodes.EqToOp) -> str:
        """Generate code for equality operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_EQ, {right})"

    def visit_NotEqToOp(self, expr: astnodes.NotEqToOp) -> str:
        """Generate code for inequality operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_NE, {right})"

    def visit_LessThanOp(self, expr: astnodes.LessThanOp) -> str:
        """Generate code for less-than operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_LT, {right})"

    def visit_LessOrEqThanOp(self, expr: astnodes.LessOrEqThanOp) -> str:
        """Generate code for less-than-or-equal operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_LE, {right})"

    def visit_GreaterThanOp(self, expr: astnodes.GreaterThanOp) -> str:
        """Generate code for greater-than operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_GT, {right})"

    def visit_GreaterOrEqThanOp(self, expr: astnodes.GreaterOrEqThanOp) -> str:
        """Generate code for greater-than-or-equal operation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_GE, {right})"

    def visit_Concat(self, expr: astnodes.Concat) -> str:
        """Generate code for string concatenation"""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        return f"L2C_BINOP({left}, L2C_OP_CONCAT, {right})"

    def visit_AndLoOp(self, expr: astnodes.AndLoOp) -> str:
        """Generate code for logical and (short-circuit)"""
        raise NotImplementedError("Short-circuit and operation needs special handling")

    def visit_OrLoOp(self, expr: astnodes.OrLoOp) -> str:
        """Generate code for logical or (short-circuit)"""
        raise NotImplementedError("Short-circuit or operation needs special handling")

    def visit_UMinusOp(self, expr: astnodes.UMinusOp) -> str:
        """Generate code for unary negation"""
        operand = self.generate(expr.operand)
        return f"L2C_UNOP(L2C_OP_NEG, {operand})"

    def visit_ULNotOp(self, expr: astnodes.ULNotOp) -> str:
        """Generate code for unary logical not"""
        operand = self.generate(expr.operand)
        return f"L2C_UNOP(L2C_OP_NOT, {operand})"

    def visit_ULengthOP(self, expr: astnodes.ULengthOP) -> str:
        """Generate code for unary length"""
        operand = self.generate(expr.operand)
        return f"L2C_UNOP(L2C_OP_LEN, {operand})"

    def visit_Call(self, expr: astnodes.Call) -> str:
        """Generate code for function call"""
        func = self.generate(expr.func)
        args = ", ".join([self.generate(arg) for arg in expr.args])
        return f"L2C_CALL({func}, {len(expr.args)}, &((luaValue[]){{{args}}}))"

    def visit_Invoke(self, expr: astnodes.Invoke) -> None:
        """Generate code for method invocation"""
        raise NotImplementedError("Method invocation not yet implemented")

    def visit_Index(self, expr: astnodes.Index) -> None:
        """Generate code for table index"""
        raise NotImplementedError("Table indexing not yet implemented")

    def visit_Field(self, expr: astnodes.Field) -> None:
        """Generate code for table field access"""
        raise NotImplementedError("Table field access not yet implemented")

    def visit_Table(self, expr: astnodes.Table) -> None:
        """Generate code for table constructor"""
        raise NotImplementedError("Table constructors not yet implemented")

    def visit_AnonymousFunction(self, expr: astnodes.AnonymousFunction) -> None:
        """Generate code for anonymous function"""
        raise NotImplementedError("Anonymous functions not yet implemented")

    def visit_Dots(self, expr: astnodes.Dots) -> str:
        """Generate code for varargs"""
        return "L2C_VARARGS"

    def visit_Function(self, expr: astnodes.Function) -> None:
        """Generate code for function definition"""
        raise NotImplementedError("Function definitions not yet implemented")
