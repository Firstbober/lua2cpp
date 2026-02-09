"""Statement generator for Lua2C transpiler

Translates Lua statements to C++ code.
Handles all statement types: assignment, control flow, loops, etc.
"""

from lua2c.core.context import TranslationContext
from lua2c.core.type_system import Type, TypeKind
from lua2c.core.type_conversion import TypeConverter
from lua2c.core.optimization_logger import OptimizationKind
from lua2c.core.ast_annotation import ASTAnnotationStore
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
        code_lines = []
        for i, (target, value) in enumerate(zip(stmt.targets, stmt.values)):
            # Track global variables (Bug #3 fix)
            if isinstance(target, astnodes.Name):
                var_name = target.id
                if not self.context.get_symbol_table().is_defined(var_name):
                    # Variable not defined as local - it's a global
                    inferred_type = None
                    type_inferencer = self.context.get_type_inferencer()
                    if type_inferencer:
                        inferred_type = type_inferencer.get_type(var_name)
                    self.context.define_global(var_name, inferred_type=inferred_type)
            
            # Track array usage for table type inference (Fix 4)
            if isinstance(target, astnodes.Index) and isinstance(target.value, astnodes.Name):
                table_name = target.value.id
                type_inferencer = self.context.get_type_inferencer()
                if type_inferencer:
                    table_info = type_inferencer.get_table_info(table_name)
                    if table_info:
                        # Mark this as an array table
                        table_info.is_array = True

            # Check if target is typed array assignment
            # This may return a complete statement for typed array writes
            assignment_code = self._handle_typed_array_assignment(target, value)

            # Check if it's a complete set() call (typed array write)
            if assignment_code and '.set(' in assignment_code:
                # _handle_typed_array_assignment generated the full assignment statement
                code_lines.append(assignment_code + ';')
            else:
                # Regular assignment: target_code = value_code;
                target_code = assignment_code if assignment_code else self.expr_gen.generate(target)

                # Set expected type for value if assigning to typed array element or typed variable
                expected_type = None
                if isinstance(target, astnodes.Index) and isinstance(target.value, astnodes.Name):
                    table_name = target.value.id
                    type_inferencer = self.context.get_type_inferencer()
                    if type_inferencer:
                        table_info = type_inferencer.get_table_info(table_name)
                        if table_info and table_info.is_array and table_info.value_type:
                            expected_type = table_info.value_type
                elif isinstance(target, astnodes.Name):
                    var_name = target.id
                    symbol = self.context.resolve_symbol(var_name)
                    if symbol and hasattr(symbol, 'inferred_type') and symbol.inferred_type:
                        expected_type = symbol.inferred_type

                if expected_type:
                    self.expr_gen._set_expected_type(value, expected_type)
                    value_code = self.expr_gen.generate(value)
                    self.expr_gen._clear_expected_type(value)
                else:
                    value_code = self.expr_gen.generate(value)

                code_lines.append(f"{target_code} = {value_code};")

        return "\n".join(code_lines)
    
    def _handle_typed_array_assignment(self, target: astnodes.Node, value: astnodes.Node) -> str:
        """Handle assignment to typed array element, adjusting for 1-based indexing

        For typed arrays like luaArray<double>, this generates:
            array.set(index, value)
        instead of:
            array[index] = value
        to avoid undefined behavior with const references.
        """
        if not isinstance(target, astnodes.Index):
            return self.expr_gen.generate(target)

        # Check if table is a typed array
        if isinstance(target.value, astnodes.Name):
            table_name = target.value.id
            type_inferencer = self.context.get_type_inferencer()
            if not type_inferencer:
                return self.expr_gen.generate(target)

            table_info = type_inferencer.get_table_info(table_name)
            if not table_info or not table_info.is_array:
                return self.expr_gen.generate(target)

            # It's a typed array - set expected type to generate native int key, then adjust for 1-based Lua to 0-based C++
            self.expr_gen._set_expected_type(target.idx, Type(TypeKind.NUMBER))
            idx_code = self.expr_gen.generate(target.idx)
            self.expr_gen._clear_expected_type(target.idx)

            # Get element type for value expression
            element_type = table_info.value_type if table_info.value_type else None
            if element_type:
                self.expr_gen._set_expected_type(value, element_type)
                value_code = self.expr_gen.generate(value)
                self.expr_gen._clear_expected_type(value)
            else:
                value_code = self.expr_gen.generate(value)

            # Use set() method for typed arrays
            return f"({self.expr_gen.generate(target.value)}).set({idx_code} - 1, {value_code})"

        return self.expr_gen.generate(target)

    def visit_LocalAssign(self, stmt: astnodes.LocalAssign) -> str:
        """Generate code for local variable assignment"""
        # Define variables first, before generating expressions
        target_names = []
        type_inferencer = self.context.get_type_inferencer()
        
        for target in stmt.targets:
            if hasattr(target, 'id'):
                var_name = target.id
                
                # Get inferred type for this variable (Fix 1)
                inferred_type = None
                if type_inferencer:
                    inferred_type = type_inferencer.get_type(var_name)
                
                self.context.define_local(var_name, inferred_type=inferred_type)
                target_names.append(var_name)
            else:
                target_names.append(self.expr_gen.generate(target))
        
        # Get type inferencer to access inferred types
        type_inferencer = self.context.get_type_inferencer()
        
        # Check if there are values
        has_values = stmt.values and len(stmt.values) > 0
        
        # Generate assignments
        code_lines = []
        if has_values:
            for i, (target, value) in enumerate(zip(stmt.targets, stmt.values)):
                # Get inferred type for target
                inferred_type = None
                var_name = None
                
                if hasattr(target, 'id'):
                    var_name = target.id
                    # First try to get from symbol
                    symbol = self.context.resolve_symbol(var_name)
                    if symbol and hasattr(symbol, 'inferred_type') and symbol.inferred_type:
                        inferred_type = symbol.inferred_type
                    
                    # If not found, try type inferencer
                    elif type_inferencer:
                        inferred_type = type_inferencer.get_type(var_name)
                
                # Generate target code based on type
                if hasattr(target, 'id'):
                    if inferred_type and inferred_type.can_specialize():
                        # Use concrete C++ type for any specialized type
                        if inferred_type.kind == TypeKind.TABLE:
                            # Check if it's a typed array
                            table_info = None
                            if type_inferencer:
                                table_info = type_inferencer.get_table_info(var_name)
                            
                            if table_info and table_info.is_array and table_info.value_type:
                                # Typed array - use luaArray container type (auto-grows on out-of-bounds access)
                                element_cpp_type = table_info.value_type.cpp_type()
                                cpp_type = f"luaArray<{element_cpp_type}>"
                                # Set expected type for value expression to generate native literals
                                self.expr_gen._set_expected_type(value, table_info.value_type)
                                # Attach table_info to the table expression for visit_Table to use
                                if isinstance(value, astnodes.Table):
                                    ASTAnnotationStore.set_annotation(value, "table_info", table_info)
                                value_code = self.expr_gen.generate(value)
                                self.expr_gen._clear_expected_type(value)
                                code_lines.append(f"{cpp_type} {var_name} = {value_code};")
                            elif table_info and table_info.is_array:
                                # Array but unknown element type - use luaValue for dynamic typing
                                value_code = self.expr_gen.generate(value)
                                code_lines.append(f"luaValue {var_name} = {value_code};")
                            else:
                                # Regular table or unknown type - use luaValue
                                value_code = self.expr_gen.generate(value)
                                code_lines.append(f"luaValue {var_name} = {value_code};")
                        else:
                            # NUMBER, STRING, BOOLEAN - use concrete type
                            cpp_type = inferred_type.cpp_type()
                            # Set expected type for value expression to generate native literals
                            self.expr_gen._set_expected_type(value, inferred_type)
                            value_code = self.expr_gen.generate(value)
                            self.expr_gen._clear_expected_type(value)
                            code_lines.append(f"{cpp_type} {var_name} = {value_code};")
                    else:
                        # Unknown/variant type - check for typed array reads or arithmetic
                        element_type_from_array = None
                        
                        # Check if value is reading from a typed array
                        if isinstance(value, astnodes.Index) and isinstance(value.value, astnodes.Name):
                            table_name = value.value.id
                            if type_inferencer:
                                table_info = type_inferencer.get_table_info(table_name)
                                if table_info and table_info.is_array and table_info.value_type:
                                    element_type_from_array = table_info.value_type
                        
                        # If value is arithmetic OR typed array read, use element type
                        is_arithmetic = isinstance(value, (astnodes.AddOp, astnodes.SubOp,
                                                         astnodes.MultOp, astnodes.FloatDivOp))
                        if is_arithmetic or element_type_from_array:
                            cpp_type = "double"
                            use_type = element_type_from_array if element_type_from_array else Type(TypeKind.NUMBER)
                            self.expr_gen._set_expected_type(value, use_type)
                            value_code = self.expr_gen.generate(value)
                            self.expr_gen._clear_expected_type(value)
                            code_lines.append(f"{cpp_type} {var_name} = {value_code};")
                        else:
                            value_code = self.expr_gen.generate(value)
                            if '\n' in value_code:
                                lines = value_code.split('\n')
                                code_lines.extend([line + ';' if not line.endswith(';') else line for line in lines[:-1]])
                                value_code = lines[-1].strip()
                            if isinstance(value, astnodes.Call) and isinstance(value.func, astnodes.Name):
                                symbol = self.context.resolve_symbol(value.func.id)
                                if symbol and not symbol.is_global and 'luaValue(' not in value_code:
                                    value_code = f'luaValue({value_code})'
                            code_lines.append(f"luaValue {var_name} = {value_code};")
                else:
                    # Complex target (not just Name) - use luaValue
                    value_code = self.expr_gen.generate(value)
                    code_lines.append(f"{self.expr_gen.generate(target)} = {value_code};")
        else:
            # No value - initialize with luaValue() (nil)
            for target in stmt.targets:
                if hasattr(target, 'id'):
                    var_name = target.id
                    code_lines.append(f"luaValue {var_name} = luaValue();")
                else:
                    code_lines.append(f"{self.expr_gen.generate(target)} = luaValue();")
        
        return "\n".join(code_lines)

    def visit_Function(self, stmt: astnodes.Function) -> str:
        """Generate code for global function definition"""
        func_name = stmt.name.id if hasattr(stmt.name, 'id') else "anonymous"
        self.context.enter_function()

        param_decls = []
        for i, param in enumerate(stmt.args):
            if hasattr(param, 'id'):
                param_name = param.id
                self.context.define_parameter(param_name, i)
                param_decls.append(f"luaValue {param_name}")

        body_statements = [self.generate(s) for s in stmt.body.body]

        if body_statements and not isinstance(stmt.body.body[-1], astnodes.Return):
            body_statements.append("return luaValue();")

        body_code = " ".join(body_statements)
        self.context.exit_function()

        params_str = ", ".join(param_decls)

        if params_str:
            return f"auto {func_name} = [=]({params_str}) {{ {body_code} }}"
        else:
            return f"auto {func_name} = [=]() {{ {body_code} }}"

    def visit_LocalFunction(self, stmt: astnodes.LocalFunction) -> str:
        """Generate code for local function definition"""
        func_name = stmt.name.id if hasattr(stmt.name, 'id') else "anonymous"
        self.context.enter_function()

        param_decls = []
        for i, param in enumerate(stmt.args):
            if hasattr(param, 'id'):
                param_name = param.id
                self.context.define_parameter(param_name, i)
                param_decls.append(f"luaValue {param_name}")

        body_statements = [self.generate(s) for s in stmt.body.body]

        if body_statements and not isinstance(stmt.body.body[-1], astnodes.Return):
            body_statements.append("return luaValue();")

        body_code = " ".join(body_statements)
        self.context.exit_function()

        params_str = ", ".join(param_decls)

        if params_str:
            return f"auto {func_name} = [=]({params_str}) {{ {body_code} }}"
        else:
            return f"auto {func_name} = [=]() {{ {body_code} }}"

    def visit_Call(self, stmt: astnodes.Call) -> str:
        """Generate code for function call statement"""
        # Check if this is a local function call (needs state parameter)
        is_local_call = False
        if isinstance(stmt.func, astnodes.Name):
            symbol = self.context.resolve_symbol(stmt.func.id)
            if symbol and not symbol.is_global:
                is_local_call = True

        if is_local_call:
            # For local functions, detect temporaries and wrap them
            func_code = self.expr_gen.generate(stmt.func)
            arg_codes = [self.expr_gen.generate(arg) for arg in stmt.args]
            
            wrapped_args = []
            temp_decls = []
            temp_counter = [0]
            
            for arg_code, arg in zip(arg_codes, stmt.args):
                if self.expr_gen._is_temporary_expression(arg):
                    temp_name = f"_l2c_tmp_arg_{temp_counter[0]}"
                    temp_counter[0] += 1
                    temp_decls.append(f"luaValue {temp_name} = {arg_code};")
                    wrapped_args.append(temp_name)
                else:
                    wrapped_args.append(arg_code)
            
            # Combine temporaries with call
            args_str = ", ".join(wrapped_args)
            if temp_decls:
                if args_str:
                    return "{\n    " + "\n    ".join(temp_decls) + "\n    " + f"{func_code}(state, {args_str});\n" + "}"
                else:
                    return "{\n    " + "\n    ".join(temp_decls) + "\n    " + f"{func_code}(state);\n" + "}"
            else:
                if args_str:
                    return f"{func_code}(state, {args_str});"
                else:
                    return f"{func_code}(state);"
        else:
            # Global/library function
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
        
        # Get inferred type for loop variable and define it
        target_type = None
        type_inferencer = self.context.get_type_inferencer()
        if type_inferencer:
            target_type = type_inferencer.get_type(target_name)
        
        # Define local with inferred type (Fix 1)
        self.context.define_local(target_name, inferred_type=target_type)
        
        # Fall back to symbol's inferred_type
        if not target_type:
            symbol = self.context.resolve_symbol(target_name)
            if symbol and hasattr(symbol, 'inferred_type') and symbol.inferred_type:
                target_type = symbol.inferred_type
        
        # Generate start/stop/step with type hints
        if target_type and target_type.kind == TypeKind.NUMBER:
            # Use type hints to generate native literals
            self.expr_gen._set_expected_type(stmt.start, target_type)
            start = self.expr_gen.generate(stmt.start)
            self.expr_gen._clear_expected_type(stmt.start)
            
            self.expr_gen._set_expected_type(stmt.stop, target_type)
            stop = self.expr_gen.generate(stmt.stop)
            self.expr_gen._clear_expected_type(stmt.stop)
        else:
            start = self.expr_gen.generate(stmt.start)
            stop = self.expr_gen.generate(stmt.stop)
        
        if stmt.step:
            if isinstance(stmt.step, (int, float)):
                step_val = stmt.step
                if target_type and target_type.kind == TypeKind.NUMBER:
                    step = f"{step_val}" if step_val == 1 else f"{step_val}"
                else:
                    step = f"luaValue({step_val})"
            else:
                if target_type and target_type.kind == TypeKind.NUMBER:
                    self.expr_gen._set_expected_type(stmt.step, target_type)
                    step = self.expr_gen.generate(stmt.step)
                    self.expr_gen._clear_expected_type(stmt.step)
                else:
                    step = self.expr_gen.generate(stmt.step)
        else:
            if target_type and target_type.kind == TypeKind.NUMBER:
                step = "1"
            else:
                step = "luaValue(1)"
        
        body = "\n    ".join([self.generate(s) for s in stmt.body.body])
        self.context.exit_block()
        
        # Use native double type if inferred type is NUMBER
        if target_type and target_type.kind == TypeKind.NUMBER:
            if step == "1":
                return f"for (double {target_name} = {start}; {target_name} <= {stop}; {target_name}++) {{\n    {body}\n}}"
            else:
                return f"for (double {target_name} = {start}; {target_name} <= {stop}; {target_name} += {step}) {{\n    {body}\n}}"
        else:
            # Fallback to luaValue for non-numeric loops
            if step == "luaValue(1)":
                return f"for (luaValue {target_name} = {start}; {target_name} <= {stop}; {target_name}++) {{\n    {body}\n}}"
            else:
                return f"for (luaValue {target_name} = {start}; {target_name} <= {stop}; {target_name} = {target_name} + {step}) {{\n    {body}\n}}"

    def visit_Return(self, stmt: astnodes.Return) -> str:
        """Generate code for return statement"""
        if not stmt.values:
            return "return luaValue()"

        if len(stmt.values) == 1:
            expr_code = self.expr_gen.generate(stmt.values[0])

            # Check if expression is a lambda (contains [=]( or [&]( )
            # Lambdas should not be wrapped in do-while block
            is_lambda = '[=](' in expr_code or '[&](' in expr_code

            if '\n' in expr_code and not is_lambda:
                lines = expr_code.split('\n')
                if len(lines) > 1:
                    temp_lines = lines[:-1]
                    final_expr = lines[-1].strip(';').strip()
                    temp_code = "    ".join(temp_lines)
                    # temp_code already contains semicolons from each statement
                    return f"do {{\n    {temp_code}\n    return {final_expr};\n}} while (0);"
            return f"return {expr_code};"

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

    def visit_SemiColon(self, stmt: astnodes.SemiColon) -> str:
        """Generate code for empty statement (semicolon)"""
        return ""
