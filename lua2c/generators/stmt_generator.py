"""Statement generator for Lua2C transpiler

Translates Lua statements to C++ code.
Handles all statement types: assignment, control flow, loops, etc.
"""

from lua2c.core.context import TranslationContext
from lua2c.generators.expr_generator import ExprGenerator
try:
    from luaparser import astnodes
except ImportError:
    raise ImportError("luaparser is required. Install with: pip install luaparser")


class StmtGenerator:
    """Generates C++ code for Lua statements"""

    def __init__(self, context: TranslationContext) -> None:
        """Initialize statement generator

        Args:
            context: Translation context
        """
        self.context = context
        self.expr_gen = ExprGenerator(context)

    def generate(self, stmt: astnodes.Node) -> str:
        """Generate C++ code for a statement

        Args:
            stmt: Statement AST node

        Returns:
            C++ code string
        """
        method_name = f"visit_{stmt.__class__.__name__}"
        method = getattr(self, method_name, self._generic_visit)
        return method(stmt)

    def _generic_visit(self, stmt: astnodes.Node) -> str:
        """Default visitor for unhandled node types

        Args:
            stmt: Statement node

        Returns:
            C++ code string

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
                code_lines.append(f"luaValue {target_name} = luaValue();")

        return "\n".join(code_lines)

    def visit_Function(self, stmt: astnodes.Function) -> str:
        """Generate code for anonymous function"""
        raise NotImplementedError("Anonymous functions not yet implemented")

    def visit_LocalFunction(self, stmt: astnodes.LocalFunction) -> str:
        """Generate code for local function definition"""
        func_name = stmt.name.id if hasattr(stmt.name, 'id') else "anonymous"
        self.context.enter_function()

        # Handle parameters
        param_names = []
        for i, param in enumerate(stmt.args):
            if hasattr(param, 'id'):
                self.context.define_parameter(param.id, i)
                param_names.append(param.id)

        # Generate function body
        body_statements = [self.generate(s) for s in stmt.body.body]

        # Add return statement if function doesn't end with one
        if body_statements and not isinstance(stmt.body.body[-1], astnodes.Return):
            body_statements.append("return luaValue();")

        body_code = "\n".join(body_statements)
        self.context.exit_function()

        # Generate C function signature with parameters
        # Use luaValue& for reference semantics to match Lua's pass-by-reference for tables/functions
        params_str = ", ".join([f"luaValue& {p}" for p in param_names])
        return f"luaValue {func_name}(luaState* state{', ' + params_str if params_str else ''}) {{\n{body_code}\n}}"

    def visit_Call(self, stmt: astnodes.Call) -> str:
        """Generate code for function call statement"""
        expr_code = self.expr_gen.generate(stmt)
        return f"{expr_code};"

    def visit_Invoke(self, stmt: astnodes.Invoke) -> str:
        """Generate code for method invocation statement"""
        expr_code = self.expr_gen.generate(stmt)
        return f"{expr_code};"

    def visit_While(self, stmt: astnodes.While) -> str:
        """Generate code for while loop"""
        test = self.expr_gen.generate(stmt.test)
        body = "\n    ".join([self.generate(s) for s in stmt.body.body])
        return f"while ({test}.is_truthy()) {{\n    {body}\n}}"

    def visit_Repeat(self, stmt: astnodes.Repeat) -> str:
        """Generate code for repeat-until loop"""
        body = "\n    ".join([self.generate(s) for s in stmt.body.body])
        test = self.expr_gen.generate(stmt.test)
        return f"do {{\n    {body}\n}} while (!{test}.is_truthy());"

    def visit_If(self, stmt: astnodes.If) -> str:
        """Generate code for if statement"""
        test = self.expr_gen.generate(stmt.test)
        if_body = "\n    ".join([self.generate(s) for s in stmt.body.body])

        result = [f"if ({test}.is_truthy()) {{", f"    {if_body}", "}"]

        if stmt.orelse:
            if isinstance(stmt.orelse, list) and stmt.orelse:
                else_body = "\n    ".join([self.generate(s) for s in stmt.orelse])
                result.append(f"else {{")
                result.append(f"    {else_body}")
                result.append("}")
            elif isinstance(stmt.orelse, astnodes.Block) and stmt.orelse.body:
                else_body = "\n    ".join([self.generate(s) for s in stmt.orelse.body])
                result.append(f"else {{")
                result.append(f"    {else_body}")
                result.append("}")

        return "\n".join(result)

    def visit_Forin(self, stmt: astnodes.Forin) -> str:
        """Generate code for for-in loop"""
        iter_exprs = ", ".join([self.expr_gen.generate(e) for e in stmt.iter])
        target_names = ", ".join([t.id for t in stmt.targets if hasattr(t, 'id')])
        body = "\n    ".join([self.generate(s) for s in stmt.body.body])
        return f"for ({target_names} in {iter_exprs}) {{\n    {body}\n}}"

    def visit_Fornum(self, stmt: astnodes.Fornum) -> str:
        """Generate code for numeric for loop"""
        target_name = stmt.target.id if hasattr(stmt.target, 'id') else "i"
        self.context.enter_block()
        self.context.define_local(target_name)
        start = self.expr_gen.generate(stmt.start)
        stop = self.expr_gen.generate(stmt.stop)
        if stmt.step:
            if isinstance(stmt.step, (int, float)):
                step = f"luaValue({stmt.step})"
            else:
                step = self.expr_gen.generate(stmt.step)
        else:
            step = "luaValue(1)"
        body = "\n    ".join([self.generate(s) for s in stmt.body.body])
        self.context.exit_block()
        return f"for (luaValue {target_name} = {start}; {target_name} <= {stop}; {target_name} = {target_name} + {step}) {{\n    {body}\n}}"

    def visit_Return(self, stmt: astnodes.Return) -> str:
        """Generate code for return statement"""
        if not stmt.values:
            return "return luaValue();"

        if len(stmt.values) == 1:
            return f"return {self.expr_gen.generate(stmt.values[0])};"

        # Multiple return values - wrap in std::vector
        values = ", ".join([self.expr_gen.generate(v) for v in stmt.values])
        return f"return std::vector<luaValue>({{{values}}});"

    def visit_Break(self, stmt: astnodes.Break) -> str:
        """Generate code for break statement"""
        return "break;"

    def visit_Label(self, stmt: astnodes.Label) -> str:
        """Generate code for label"""
        raise NotImplementedError("Labels and goto not yet implemented")

    def visit_Goto(self, stmt: astnodes.Goto) -> str:
        """Generate code for goto statement"""
        raise NotImplementedError("Labels and goto not yet implemented")

    def visit_Do(self, stmt: astnodes.Do) -> str:
        """Generate code for do block"""
        body = "\n    ".join([self.generate(s) for s in stmt.body.body])
        return f"do {{\n    {body}\n}} while (0);"
