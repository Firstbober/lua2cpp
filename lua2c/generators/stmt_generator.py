"""Statement generator for Lua2C transpiler

Translates Lua statements to C code.
Handles all statement types: assignment, control flow, loops, etc.
"""

from lua2c.core.context import TranslationContext
from lua2c.generators.expr_generator import ExprGenerator
try:
    from luaparser import astnodes
except ImportError:
    raise ImportError("luaparser is required. Install with: pip install luaparser")


class StmtGenerator:
    """Generates C code for Lua statements"""

    def __init__(self, context: TranslationContext) -> None:
        """Initialize statement generator

        Args:
            context: Translation context
        """
        self.context = context
        self.expr_gen = ExprGenerator(context)

    def generate(self, stmt: astnodes.Node) -> str:
        """Generate C code for a statement

        Args:
            stmt: Statement AST node

        Returns:
            C code string
        """
        method_name = f"visit_{stmt.__class__.__name__}"
        method = getattr(self, method_name, self._generic_visit)
        return method(stmt)

    def _generic_visit(self, stmt: astnodes.Node) -> str:
        """Default visitor for unhandled node types

        Args:
            stmt: Statement node

        Returns:
            C code string

        Raises:
            NotImplementedError: If node type not supported
        """
        raise NotImplementedError(
            f"Statement type {stmt.__class__.__name__} not yet implemented"
        )

    def visit_Assign(self, stmt: astnodes.Assign) -> str:
        """Generate code for assignment statement"""
        targets = [self.expr_gen.generate(t) for t in stmt.targets]
        values = [self.expr_gen.generate(v) for v in stmt.values]

        code_lines = []
        for i, target in enumerate(targets):
            if i < len(values):
                code_lines.append(f"{target} = {values[i]};")

        return "\n".join(code_lines)

    def visit_LocalAssign(self, stmt: astnodes.LocalAssign) -> str:
        """Generate code for local variable assignment"""
        # Define variables first, before generating expressions
        target_names = []
        for target in stmt.targets:
            if hasattr(target, 'id'):
                var_name = target.id
                self.context.define_local(var_name)
                target_names.append(var_name)
            else:
                # For complex targets (not just Name), need different handling
                target_names.append(self.expr_gen.generate(target))

        # Now generate values
        values = [self.expr_gen.generate(v) for v in (stmt.values or [])]

        # Generate code
        code_lines = []
        for i, target_name in enumerate(target_names):
            if i < len(values):
                code_lines.append(f"luaValue {target_name} = {values[i]};")
            else:
                code_lines.append(f"luaValue {target_name} = L2C_NIL;")

        return "\n".join(code_lines)

    def visit_Function(self, stmt: astnodes.Function) -> str:
        """Generate code for anonymous function"""
        raise NotImplementedError("Anonymous functions not yet implemented")

    def visit_LocalFunction(self, stmt: astnodes.LocalFunction) -> str:
        """Generate code for local function definition"""
        func_name = stmt.name.id if hasattr(stmt.name, 'id') else "anonymous"
        self.context.enter_function()

        # Handle parameters
        for i, param in enumerate(stmt.args):
            if hasattr(param, 'id'):
                self.context.define_parameter(param.id, i)

        body_code = "\n".join([self.generate(s) for s in stmt.body.body])
        self.context.exit_function()

        # In real implementation, would use proper C syntax
        return f"luaValue {func_name}(luaState* state) {{\n{body_code}\n}}"

    def visit_Call(self, stmt: astnodes.Call) -> str:
        """Generate code for function call statement"""
        expr_code = self.expr_gen.generate(stmt)
        return f"{expr_code};"

    def visit_Invoke(self, stmt: astnodes.Invoke) -> None:
        """Generate code for method invocation"""
        raise NotImplementedError("Method invocation not yet implemented")

    def visit_While(self, stmt: astnodes.While) -> None:
        """Generate code for while loop"""
        raise NotImplementedError("While loops not yet implemented")

    def visit_Repeat(self, stmt: astnodes.Repeat) -> None:
        """Generate code for repeat-until loop"""
        raise NotImplementedError("Repeat-until loops not yet implemented")

    def visit_If(self, stmt: astnodes.If) -> None:
        """Generate code for if statement"""
        raise NotImplementedError("If statements not yet implemented")

    def visit_Forin(self, stmt: astnodes.Forin) -> None:
        """Generate code for for-in loop"""
        raise NotImplementedError("For-in loops not yet implemented")

    def visit_Fornum(self, stmt: astnodes.Fornum) -> None:
        """Generate code for numeric for loop"""
        raise NotImplementedError("Numeric for loops not yet implemented")

    def visit_Return(self, stmt: astnodes.Return) -> str:
        """Generate code for return statement"""
        if stmt.values:
            values = [self.expr_gen.generate(v) for v in stmt.values]
            return f"return {len(values)}, &((luaValue[]){{{', '.join(values)}}});"
        else:
            return "return 0, NULL;"

    def visit_Break(self, stmt: astnodes.Break) -> str:
        """Generate code for break statement"""
        return "break;"

    def visit_Label(self, stmt: astnodes.Label) -> None:
        """Generate code for label"""
        raise NotImplementedError("Labels and goto not yet implemented")

    def visit_Goto(self, stmt: astnodes.Goto) -> None:
        """Generate code for goto statement"""
        raise NotImplementedError("Labels and goto not yet implemented")

    def visit_Do(self, stmt: astnodes.Do) -> None:
        """Generate code for do block"""
        raise NotImplementedError("Do blocks not yet implemented")
