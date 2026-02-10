"""Statement generator for Lua2C++ transpiler

Generates C++ code from Lua AST statement nodes.
Implements double-dispatch pattern for local assignments and return statements.
"""

from typing import Any, Optional, List
from lua2cpp.core.ast_visitor import ASTVisitor
from lua2cpp.core.types import Type, ASTAnnotationStore
from lua2cpp.generators.expr_generator import ExprGenerator

try:
    from luaparser import astnodes
except ImportError:
    raise ImportError(
        "luaparser is required. Install with: pip install luaparser"
    )


class StmtGenerator(ASTVisitor):
    """Generates C++ code from Lua AST statement nodes

    Focuses on local variable declarations and return statements.
    Integrates with ExprGenerator for expression generation.
    """

    def __init__(self) -> None:
        """Initialize statement generator with expression generator"""
        super().__init__()
        self._expr_gen = ExprGenerator()

    def generate(self, node: Any) -> str:
        """Generate C++ code from a statement node using double-dispatch

        Args:
            node: AST node (statement node)

        Returns:
            str: Generated C++ code as a string
        """
        return self.visit(node)

    def visit_LocalAssign(self, node: astnodes.LocalAssign) -> str:
        """Generate C++ local variable declaration

        Format: <type> <name> = <expr>;
        If type is unknown, use 'auto' keyword.
        If no initialization, just declare without assignment.

        Args:
            node: LocalAssign AST node with .names (list of Name nodes)
                  and .exprs (list of expression nodes, can be empty)

        Returns:
            str: C++ local variable declaration(s)
        """
        # LocalAssign has .targets (list of Name nodes) and .values (list of expressions)
        # Multiple variables can be declared: local x, y = 1, 2
        lines = []

        for i, name_node in enumerate(node.targets):
            var_name = name_node.id
            init_expr = None
            if i < len(node.values):
                init_expr = node.values[i]

            # Try to get type information from the name node
            var_type = None
            type_info = ASTAnnotationStore.get_type(name_node)
            if type_info is not None:
                var_type = type_info.cpp_type()
            else:
                var_type = "auto"

            if init_expr is not None:
                # Generate the expression
                expr_code = self._expr_gen.generate(init_expr)
                lines.append(f"{var_type} {var_name} = {expr_code};")
            else:
                # Declaration without initialization
                lines.append(f"{var_type} {var_name};")

        # If only one variable, return single line; otherwise return all lines
        if len(lines) == 1:
            return lines[0]
        return "\n".join(lines)

    def visit_Return(self, node: astnodes.Return) -> str:
        """Generate C++ return statement

        Format: return <expr>; or return;
        Handles multiple return values by taking the first one.

        Args:
            node: Return AST node with .exprs (list of expression nodes, can be empty)

        Returns:
            str: C++ return statement
        """
        # Return has .values (list of expressions, can be empty)
        # For now, we only handle single return values or empty return
        if not node.values:
            return "return;"

        # Take the first expression (Lua can return multiple values,
        # but we only handle the first for now)
        expr_code = self._expr_gen.generate(node.values[0])
        return f"return {expr_code};"

    def _generate_block(self, block: astnodes.Block, indent: str = "    ") -> str:
        """Generate C++ code block from Lua Block node

        Args:
            block: Block AST node with .body (list of statements)
            indent: Indentation string for block content

        Returns:
            str: C++ code block as string with braces
        """
        statements = []
        for stmt in block.body:
            # Generate each statement using double-dispatch
            stmt_code = self.visit(stmt)
            statements.append(f"{indent}{stmt_code}")

        return "{\n" + "\n".join(statements) + "\n}"

    def visit_If(self, node: astnodes.If) -> str:
        """Generate C++ if-else statement

        Format:
            if (condition) { ... }
            else { ... }

        Args:
            node: If AST node with .test (condition), .body (if block),
                  .orelse (else block)

        Returns:
            str: C++ if-else statement
        """
        # Generate condition expression
        cond_code = self._expr_gen.generate(node.test)

        # Generate if body
        if_body = self._generate_block(node.body)

        # Build if statement
        result = f"if (is_truthy({cond_code})) {if_body}"

        # Handle else block
        if node.orelse and node.orelse.body:
            else_body = self._generate_block(node.orelse)
            result += f"\nelse {else_body}"

        return result

    def visit_While(self, node: astnodes.While) -> str:
        """Generate C++ while loop

        Format:
            while (condition) { ... }

        Args:
            node: While AST node with .test (condition), .body (loop body)

        Returns:
            str: C++ while loop
        """
        # Generate condition expression
        cond_code = self._expr_gen.generate(node.test)

        # Generate loop body
        loop_body = self._generate_block(node.body)

        return f"while (is_truthy({cond_code})) {loop_body}"

    def visit_Fornum(self, node: astnodes.Fornum) -> str:
        """Generate C++ for loop for numeric for loop

        Format:
            for (auto <name> = <start>; <name> <= <stop>; <name> += <step>) { ... }

        Args:
            node: Fornum AST node with .target (Name node), .start (init expr),
                  .stop (end expr), .step (step expr, optional), .body (loop body)

        Returns:
            str: C++ for loop
        """
        # Get loop variable name
        var_name = node.target.id

        # Get type for loop variable (number for numeric for)
        var_type = "double"

        # Generate start and stop expressions
        start_code = self._expr_gen.generate(node.start)
        stop_code = self._expr_gen.generate(node.stop)

        # Generate step expression (default is 1 if not provided)
        if node.step:
            step_code = self._expr_gen.generate(node.step)
        else:
            step_code = "1"

        # Generate loop body
        loop_body = self._generate_block(node.body)

        # C++ for loop: initialization; condition; increment
        # Lua's numeric for: for i = start, stop, step do
        # C++ equivalent: for (auto i = start; i <= stop; i += step)
        init = f"{var_type} {var_name} = {start_code}"
        cond = f"{var_name} <= {stop_code}"
        incr = f"{var_name} += {step_code}"

        return f"for ({init}; {cond}; {incr}) {loop_body}"

    def visit_Function(self, node: astnodes.Function) -> str:
        """Generate C++ function definition for global function

        Format: ReturnType func_name(State* state, param_type1 param1, ...) {
                    body
                }

        Args:
            node: Function AST node with .name (Name node), .args (list of Name nodes),
                  and .body (Block node)

        Returns:
            str: C++ function definition
        """
        # Get function name
        func_name = node.name.id

        # Get return type from type annotation
        return_type = "auto"  # Default to auto if type not specified
        type_info = ASTAnnotationStore.get_type(node)
        if type_info is not None:
            return_type = type_info.cpp_type()

        # Build parameter list
        params = ["State* state"]  # First parameter is always State*
        for arg in node.args:
            param_type = "auto"  # Default to auto if type not specified
            arg_type_info = ASTAnnotationStore.get_type(arg)
            if arg_type_info is not None:
                param_type = arg_type_info.cpp_type()
            params.append(f"{param_type} {arg.id}")

        params_str = ", ".join(params)

        # Generate function body
        body = self._generate_block(node.body, indent="    ")

        return f"{return_type} {func_name}({params_str}) {body}"

    def visit_LocalFunction(self, node: astnodes.LocalFunction) -> str:
        """Generate C++ function definition for local function

        Format: auto func_name = [](State* state, param_type1 param1, ...) -> ReturnType {
                    body
                };

        Args:
            node: LocalFunction AST node with .name (Name node), .args (list of Name nodes),
                  and .body (Block node)

        Returns:
            str: C++ local function definition (lambda expression)
        """
        # Get function name
        func_name = node.name.id

        # Get return type from type annotation
        return_type = "auto"  # Default to auto if type not specified
        type_info = ASTAnnotationStore.get_type(node)
        if type_info is not None:
            return_type = type_info.cpp_type()

        # Build parameter list
        params = ["State* state"]  # First parameter is always State*
        for arg in node.args:
            param_type = "auto"  # Default to auto if type not specified
            arg_type_info = ASTAnnotationStore.get_type(arg)
            if arg_type_info is not None:
                param_type = arg_type_info.cpp_type()
            params.append(f"{param_type} {arg.id}")

        params_str = ", ".join(params)

        # Generate function body
        body = self._generate_block(node.body, indent="    ")

        return f"auto {func_name} = []({params_str}) -> {return_type} {body};"

    def visit_Call(self, node: astnodes.Call) -> str:
        """Generate C++ function call statement

        Format: func_name(state, args...);
        Note: This handles Call as a statement, not an expression.

        Args:
            node: Call AST node with .func (expression) and .args (list of expressions)

        Returns:
            str: C++ function call statement
        """
        # Generate the call expression using ExprGenerator
        call_expr = self._expr_gen.generate(node)
        # Add semicolon to make it a statement
        return f"{call_expr};"
