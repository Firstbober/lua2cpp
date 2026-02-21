"""Statement generator for Lua2C++ transpiler

Generates C++ code from Lua AST statement nodes.
Implements double-dispatch pattern for local assignments and return statements.
"""

from typing import Any, Optional, List, TYPE_CHECKING, Set
from ..core.ast_visitor import ASTVisitor
from ..core.types import Type, ASTAnnotationStore
from .expr_generator import ExprGenerator

try:
    from luaparser import astnodes
except ImportError:
    raise ImportError(
        "luaparser is required. Install with: pip install luaparser"
    )

if TYPE_CHECKING:
    from ..core.library_registry import LibraryFunctionRegistry

from ..core.call_convention import CallConventionRegistry, CallConvention, flatten_index_chain_parts, get_root_module


class StmtGenerator(ASTVisitor):
    """Generates C++ code from Lua AST statement nodes

    Focuses on local variable declarations and return statements.
    Integrates with ExprGenerator for expression generation.
    """

    def __init__(self, library_registry: Optional["LibraryFunctionRegistry"] = None,
                 convention_registry: Optional[CallConventionRegistry] = None) -> None:
        """Initialize statement generator with expression generator

        Args:
            library_registry: Optional registry for detecting library function calls.
            convention_registry: Optional registry for call conventions.
        """
        super().__init__()
        self._library_registry = library_registry
        self._convention_registry = convention_registry or CallConventionRegistry()
        self._expr_gen = ExprGenerator(library_registry, stmt_gen=self, convention_registry=self._convention_registry)
        # Track whether we're inside a function body
        self._in_function = False

    def set_module_context(self, prefix: str, module_state: Set) -> None:
        """Propagate module context to internal ExprGenerator"""
        self._expr_gen.set_module_context(prefix, module_state)

    def enter_function(self):
        self._in_function = True

    def exit_function(self):
        self._in_function = False

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

        For library function references (e.g., local x = math.sqrt),
        wrap in a lambda to handle overloaded functions.

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
                expr_code = self._expr_gen.generate(init_expr)

                # Check if this is a bare library function REFERENCE (e.g., math.floor, io.write)
                # This is a function REFERENCE, not a function CALL
                # Function REFERENCE: local f = math.sqrt (Index node)
                # Function CALL: local x = tonumber(y) (Call node)
                is_library_ref = (
                    isinstance(init_expr, astnodes.Index) and
                    (expr_code.startswith('math[') or  # e.g., math["floor"]
                     expr_code.startswith('string[') or  # e.g., string["format"]
                     expr_code.startswith('io[') or  # e.g., io["write"]
                     expr_code.startswith('table[') or  # e.g., table["concat"]
                     expr_code.startswith('os[') or  # e.g., os["time"]
                     '::' in expr_code)  # e.g., math_lib::floor
                )

                # At the start, determine if this is a module-level assignment to module state
                is_module_state_var = (
                    hasattr(self._expr_gen, '_module_state') and
                    hasattr(self._expr_gen, '_module_prefix') and
                    var_name in self._expr_gen._module_state and
                    not self._in_function
                )

                # If module-level assignment to module state var, generate assignment to static
                if is_module_state_var:
                    mangled_name = f"{self._expr_gen._module_prefix}_{var_name}"
                    if is_library_ref:
                        lambda_wrapper = f"[](auto... args) {{ return {expr_code}(args...); }}"
                        lines.append(f"{mangled_name} = {lambda_wrapper};")
                    else:
                        lines.append(f"{mangled_name} = {expr_code};")
                elif is_library_ref:
                    # Generate lambda wrapper: [](auto... args) { return <expr_code>(args...); }
                    lambda_wrapper = f"[](auto... args) {{ return {expr_code}(args...); }}"
                    lines.append(f"{var_type} {var_name} = {lambda_wrapper};")
                else:
                    lines.append(f"{var_type} {var_name} = {expr_code};")
            else:
                lines.append(f"TABLE {var_name};")

        # If only one variable, return single line; otherwise return all lines
        if len(lines) == 1:
            return lines[0]
        return "\n".join(lines)

    def visit_Assign(self, node: astnodes.Assign) -> str:
        """Generate C++ assignment statement

        Format: <target> = <expr>;
        Handles multiple targets/values pairs.

        Args:
            node: Assign AST node with .targets (list of target expressions)
                  and .values (list of value expressions)

        Returns:
            str: C++ assignment statement(s)
        """
        lines = []

        for i, target_node in enumerate(node.targets):
            init_expr = None
            if i < len(node.values):
                init_expr = node.values[i]

            target_code = self._expr_gen.generate(target_node)

            if init_expr is not None:
                value_code = self._expr_gen.generate(init_expr)
                if target_code != value_code:
                    lines.append(f"{target_code} = {value_code};")
            else:
                lines.append(f"{target_code} = TABLE();")

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

    def _normalize_block_body(self, block):
        """Normalize Block.body to a list for iteration.
        
        If block.body is a Block object, wrap it in a list.
        If it's already a list, return it as-is.
        """
        return block.body if isinstance(block.body, list) else [block.body]

    def _generate_block(self, block: astnodes.Block, indent: str = "    ") -> str:
        """Generate C++ code block from Lua Block node

        Args:
            block: Block AST node with .body (list of statements)
            indent: Indentation string for block content

        Returns:
            str: C++ code block as string with braces
        """
        statements = []
        for stmt in self._normalize_block_body(block):
            # Generate each statement using double-dispatch
            stmt_code = self.visit(stmt)
            statements.append(f"{indent}{stmt_code}")

        return "{\n" + "\n".join(statements) + "\n}"

    def _infer_return_type(self, block: astnodes.Block) -> str:
        has_return = False
        for stmt in self._normalize_block_body(block):
            if isinstance(stmt, astnodes.Return):
                has_return = True
                if not stmt.values:
                    return "void"
                for value in stmt.values:
                    expr_code = self._expr_gen.generate(value)
                    if "NEW_TABLE" in expr_code or "Table" in expr_code:
                        return "TABLE"
            elif isinstance(stmt, astnodes.If):
                body_result = self._infer_return_type(stmt.body)
                if body_result == "TABLE":
                    return "TABLE"
                if body_result != "void":
                    has_return = True
                if stmt.orelse and hasattr(stmt.orelse, 'body'):
                    else_result = self._infer_return_type(stmt.orelse)
                    if else_result == "TABLE":
                        return "TABLE"
                    if else_result != "void":
                        has_return = True
            elif isinstance(stmt, astnodes.Fornum):
                # Recursively check for returns inside for loops
                result = self._infer_return_type(stmt.body)
                if result == "TABLE":
                    return "TABLE"
                if result != "void":
                    has_return = True
            elif isinstance(stmt, astnodes.While):
                # Recursively check for returns inside while loops
                result = self._infer_return_type(stmt.body)
                if result == "TABLE":
                    return "TABLE"
                if result != "void":
                    has_return = True
            elif isinstance(stmt, astnodes.Repeat):
                # Recursively check for returns inside repeat loops
                result = self._infer_return_type(stmt.body)
                if result == "TABLE":
                    return "TABLE"
                if result != "void":
                    has_return = True
            elif isinstance(stmt, astnodes.Forin):
                # Recursively check for returns inside for-in loops
                result = self._infer_return_type(stmt.body)
                if result == "TABLE":
                    return "TABLE"
                if result != "void":
                    has_return = True

        return "void" if not has_return else "double"

    def visit_Do(self, node: astnodes.Do) -> str:
        return self._generate_block(node.body)

    def visit_If(self, node: astnodes.If) -> str:
        cond_code = self._expr_gen.generate(node.test)
        if_body = self._generate_block(node.body)
        result = f"if (l2c::is_truthy({cond_code})) {if_body}"
        if node.orelse and node.orelse.body:
            # Normalize orelse (could be Block or If node for elseif chains)
            orelse = node.orelse
            if hasattr(orelse, 'body') and orelse.body:
                if isinstance(orelse.body, list):
                    else_body = self._generate_block(orelse)
                else:
                    # orelse is itself an If node (elseif chain)
                    else_body = self.visit_If(orelse)
                result += f"\nelse {else_body}"
        return result

    def visit_While(self, node: astnodes.While) -> str:
        cond_code = self._expr_gen.generate(node.test)
        loop_body = self._generate_block(node.body)
        return f"while (l2c::is_truthy({cond_code})) {loop_body}"

    def visit_Fornum(self, node: astnodes.Fornum) -> str:
        var_name = node.target.id
        var_type = "double"
        start_code = self._expr_gen.generate(node.start)
        stop_code = self._expr_gen.generate(node.stop)
        if node.step is None:
            step_code = "1"
        elif isinstance(node.step, int):
            step_code = str(node.step)
        else:
            step_code = self._expr_gen.generate(node.step)
        loop_body = self._generate_block(node.body)
        init = f"{var_type} {var_name} = {start_code}"
        cond = f"{var_name} <= {stop_code}"
        incr = f"{var_name} += {step_code}"
        return f"for ({init}; {cond}; {incr}) {loop_body}"

    def visit_Function(self, node: astnodes.Function) -> str:
        # Handle both Name and Index (e.g., function Complex.conj() style)
        if isinstance(node.name, astnodes.Name):
            func_name = node.name.id
        elif isinstance(node.name, astnodes.Index):
            if isinstance(node.name.value, astnodes.Name) and isinstance(node.name.idx, astnodes.Name):
                table_name = node.name.value.id
                method_name = node.name.idx.id
                func_name = f"{table_name}_{method_name}"
            else:
                func_name = "anonymous_method"
        else:
            func_name = "anonymous"
        mangled_name = "_l2c_main" if func_name == "main" else func_name
        return_type = "auto"
        type_info = ASTAnnotationStore.get_type(node)
        if type_info is not None:
            return_type = type_info.cpp_type()
        
        template_params = []
        params = []
        param_idx = 1
        for arg in node.args:
            # Skip Varargs (...), can't generate C++ params for it
            if isinstance(arg, astnodes.Varargs):
                continue
            template_params.append(f"T{param_idx}")
            params.append(f"T{param_idx} {arg.id}")
            param_idx += 1
        
        template_str = ""
        if template_params:
            template_params_str = ", ".join(f"typename {tp}" for tp in template_params)
            template_str = f"template<{template_params_str}>\n"
        
        params_str = ", ".join(params)
        self.enter_function()
        body = self._generate_block(node.body, indent="    ")
        self.exit_function()
        return f"{template_str}{return_type} {mangled_name}({params_str}) {body}"

    def visit_LocalFunction(self, node: astnodes.LocalFunction) -> str:
        """Generate C++ function definition for local function

        Format: auto func_name = [](param_type1 param1, ...) -> ReturnType {
                    body
                }

        Args:
            node: LocalFunction AST node with .name (Name node), .args (list of Name nodes),
                  and .body (Block node)

        Returns:
            str: C++ local function definition (lambda expression)
        """
        # Get function name
        func_name = node.name.id
        mangled_name = "_l2c_main" if func_name == "main" else func_name

        # Get return type from type annotation
        return_type = "auto"
        type_info = ASTAnnotationStore.get_type(node)
        if type_info is not None:
            return_type = type_info.cpp_type()

        # Build parameter list with template parameters for C++17 compatibility
        params = []
        template_params = []
        for arg in node.args:
            # Skip Varargs (...), can't generate C++ params for it
            if isinstance(arg, astnodes.Varargs):
                continue
            template_params.append(f"{arg.id}_t")
            params.append(f"{arg.id}_t {arg.id}")
            arg_type_info = ASTAnnotationStore.get_type(arg)
            if arg_type_info is not None:
                param_type = arg_type_info.cpp_type()

        params_str = ", ".join(params)
        template_params_str = ", ".join([f"typename {p}" for p in template_params])

        # Generate function body
        self.enter_function()
        body = self._generate_block(node.body, indent="    ")
        self.exit_function()

        # Infer return type from function body
        inferred_return_type = self._infer_return_type(node.body)

        if template_params:
            return f"template<{template_params_str}>\n{inferred_return_type} {mangled_name}({params_str}) {body}"
        else:
            return f"{inferred_return_type} {mangled_name}() {body}"

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

    def visit_SemiColon(self, node: astnodes.SemiColon) -> str:
        return ""

    def visit_Repeat(self, node: astnodes.Repeat) -> str:
        body = self._generate_block(node.body)
        cond = self._expr_gen.generate(node.test)
        return f"do {body} while (!l2c::is_truthy({cond}));"

    def visit_Forin(self, node: astnodes.Forin) -> str:
        return "// for-in loop not implemented"

    def visit_Break(self, node: astnodes.Break) -> str:
        return "break;"

    def visit_Label(self, node: astnodes.Label) -> str:
        return f"/* label {node.id} */"

    def visit_Goto(self, node: astnodes.Goto) -> str:
        return f"/* goto {node.label} */"

    def _is_library_function_reference(self, node: Any) -> bool:
        """Check if the expression is a library function reference (e.g., math.sqrt, io.write)
        
        Args:
            node: AST node to check
            
        Returns:
            True if the node represents a library function reference, False otherwise
        """
        from luaparser import astnodes
        
        # Check if this is an Index node (library.func pattern)
        if isinstance(node, astnodes.Index):
            # Index.value must be a Name node (library name)
            if isinstance(node.value, astnodes.Name):
                library_name = node.value.id
                # Check if it's a standard library (math, io, string, table, os)
                return library_name in ('math', 'io', 'string', 'table', 'os')
        
        return False

    def visit_Invoke(self, node: astnodes.Invoke) -> str:
        # Handle library method calls like io.write, string.format, math.sqrt
        # These become: struct_name::method(args)
        from luaparser import astnodes
        
        if isinstance(node.func, astnodes.Index):
            # Get the library name and method name
            if isinstance(node.func.value, astnodes.Name):
                lib_name = node.func.value.id
                method_name = node.func.idx.id if hasattr(node.func.idx, 'id') else str(node.func.idx)
                
                # Map Lua library names to C++ struct names
                lib_map = {
                    'io': 'io',
                    'string': 'string_lib',
                    'math': 'math_lib',
                    'table': 'table_lib',
                    'os': 'os_lib',
                }
                
                cpp_lib = lib_map.get(lib_name, lib_name)
                
                # Generate arguments
                args = [self._expr_gen.generate(arg) for arg in node.args]
                args_str = ", ".join(args)
                
                return f"{cpp_lib}::{method_name}({args_str});"
        
        # Fallback for other invoke patterns
        func = self._expr_gen.generate(node.func)
        args = [self._expr_gen.generate(arg) for arg in node.args]
        args_str = ", ".join(args)
        return f"{func}({args_str});"

