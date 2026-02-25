"""Expression generator for Lua2C++ transpiler

Generates C++ code from Lua AST expression nodes.
Implements double-dispatch pattern for literal and name expressions.
"""

from typing import Any, Optional, Set, TYPE_CHECKING
from ..core.ast_visitor import ASTVisitor
from ..core.library_registry import LibraryFunctionRegistry as _LibraryFunctionRegistry
from ..core.call_convention import CallConventionRegistry, CallConvention, flatten_index_chain_parts, get_root_module
from ..core.types import ASTAnnotationStore, TypeKind

try:
    from luaparser import astnodes
except ImportError:
    raise ImportError(
        "luaparser is required. Install with: pip install luaparser"
    )

if TYPE_CHECKING:
    from ..core.library_registry import LibraryFunctionRegistry


class ExprGenerator(ASTVisitor):
    """Generates C++ code from Lua AST expression nodes

    Focuses on literal expressions (Number, String, Boolean) and Name nodes.
    More complex expressions (operators, calls, indexing) are handled separately.
    """

    def __init__(self, library_registry: Optional[_LibraryFunctionRegistry] = None, 
                 stmt_gen: Optional[Any] = None,
                 convention_registry: Optional[CallConventionRegistry] = None) -> None:
        """Initialize expression generator

        Args:
            library_registry: Optional registry for detecting library function calls.
                            If provided, generates API syntax for library functions.
            stmt_gen: Optional statement generator for generating anonymous function bodies.
        """
        super().__init__()
        self._library_registry = library_registry
        self._stmt_gen = stmt_gen
        self._convention_registry = convention_registry or CallConventionRegistry()

        # Module context for name mangling
        self._module_prefix: str = ""
        self._module_state: Set[str] = set()
        # Function-local variable tracking for proper scoping
        self._function_locals: Set[str] = set()

    def set_module_context(self, prefix: str, module_state: Set[str]) -> None:
        self._module_prefix = prefix
        self._module_state = module_state

    def enter_function(self, local_names: Set[str] = None):
        """Enter function scope with optional local variable names.

        Args:
            local_names: Set of local variable names to track.
        """
        self._function_locals = local_names if local_names else set()

    def exit_function(self):
        """Exit function scope, clear local variables."""
        self._function_locals = set()

    def generate(self, node: Any) -> str:
        """Generate C++ code from an expression node using double-dispatch

        Args:
            node: AST node (expression node)

        Returns:
            str: Generated C++ code as a string
        """
        return self.visit(node)

    def visit_Number(self, node: astnodes.Number) -> str:
        return f"NUMBER({node.n})"

    def visit_String(self, node: astnodes.String) -> str:
        """Generate C++ string literal with proper escaping

        Args:
            node: String AST node

        Returns:
            str: C++ string literal with escaped quotes and special characters
        """
        # String node's .s attribute contains bytes, need to decode
        content = node.s.decode() if isinstance(node.s, bytes) else node.s

        # Escape special characters for C++ output
        # C++ string literals need escapes for: ", \, newline, tab, etc.
        escaped = (
            content
            .replace('\\', '\\\\')
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
            .replace('\t', '\\t')
        )
        return f'"{escaped}"'

    def visit_TrueExpr(self, node: astnodes.TrueExpr) -> str:
        """Generate C++ true boolean literal

        Args:
            node: TrueExpr AST node

        Returns:
            str: C++ true keyword
        """
        return "true"

    def visit_FalseExpr(self, node: astnodes.FalseExpr) -> str:
        """Generate C++ false boolean literal

        Args:
            node: FalseExpr AST node

        Returns:
            str: C++ false keyword
        """
        return "false"

    def visit_Nil(self, node: astnodes.Nil) -> str:
        """Generate C++ representation of Lua nil literal

        Args:
            node: Nil AST node

        Returns:
            str: NIL constant (defined in stub header as empty Table)
        """
        return "NIL"

    def visit_Name(self, node: astnodes.Name) -> str:
        """Generate C++ variable name reference

        Args:
            node: Name AST node

        Returns:
            str: Variable name as-is
        """
        name = node.id
        # Check function-local variables first (they shadow module state)
        if name in self._function_locals:
            return name
        # Then check module state
        if name in self._module_state:
            return f"{self._module_prefix}_{name}"
        # Check for known global functions that need l2c:: prefix
        # These are Lua built-in functions that exist in the l2c namespace
        global_functions = {'loadstring', 'load', 'print', 'tostring', 'tonumber', 
                            'type', 'pairs', 'ipairs', 'next', 'error', 'assert',
                            'pcall', 'xpcall', 'rawget', 'rawset', 'rawequal', 'rawlen',
                            'setmetatable', 'getmetatable', 'select', 'unpack', 'require',
                            'collectgarbage', 'getfenv', 'setfenv', 'gcinfo'}
        if name in global_functions:
            return f"l2c::{name}"
        return name

    def visit_AddOp(self, node: astnodes.AddOp) -> str:
        """Generate C++ addition operation

        Args:
            node: AddOp AST node with left and right operands

        Returns:
            str: C++ addition expression
        """
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"({left} + {right})"

    def visit_SubOp(self, node: astnodes.SubOp) -> str:
        """Generate C++ subtraction operation

        Args:
            node: SubOp AST node with left and right operands

        Returns:
            str: C++ subtraction expression
        """
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"({left} - {right})"

    def visit_MultOp(self, node: astnodes.MultOp) -> str:
        """Generate C++ multiplication operation

        Args:
            node: MultOp AST node with left and right operands

        Returns:
            str: C++ multiplication expression
        """
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"({left} * {right})"

    def visit_FloatDivOp(self, node: astnodes.FloatDivOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"({left} / {right})"

    def visit_ModOp(self, node: astnodes.ModOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"l2c::mod({left}, {right})"

    def visit_ExpoOp(self, node: astnodes.ExpoOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"std::pow({left}, {right})"

    def visit_Concat(self, node: astnodes.Concat) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"table_lib::concat({left}, {right})"

    def visit_EqToOp(self, node: astnodes.EqToOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"({left} == {right})"

    def visit_LessThanOp(self, node: astnodes.LessThanOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"({left} < {right})"

    def visit_GreaterThanOp(self, node: astnodes.GreaterThanOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"({left} > {right})"

    def visit_LessOrEqThanOp(self, node: astnodes.LessOrEqThanOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"({left} <= {right})"

    def visit_GreaterOrEqThanOp(self, node: astnodes.GreaterOrEqThanOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"({left} >= {right})"

    def visit_NotEqToOp(self, node: astnodes.NotEqToOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"({left} != {right})"

    def visit_AndLoOp(self, node: astnodes.AndLoOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"(({left}) ? ({right}) : ({left}))"

    def visit_OrLoOp(self, node: astnodes.OrLoOp) -> str:
        # Check if left is AndLoOp (ternary pattern: cond and x or y)
        if isinstance(node.left, astnodes.AndLoOp):
            cond = self.generate(node.left.left)
            truthy = self.generate(node.left.right)
            falsy = self.generate(node.right)
            if isinstance(node.right, astnodes.Number):
                falsy = f"TABLE({falsy})"
            return f"(l2c::is_truthy({cond}) && l2c::is_truthy({truthy}) ? ({truthy}) : ({falsy}))"
        
        if self._is_library_function_reference(node.left):
            return self.generate(node.right)
        
        # Regular or: (cond) ? (cond) : (fallback)
        left = self.generate(node.left)
        right = self.generate(node.right)
        if isinstance(node.right, astnodes.Number):
            right = f"TABLE({right})"
        return f"(({left}) ? ({left}) : ({right}))"

    def visit_UMinusOp(self, node: astnodes.UMinusOp) -> str:
        operand = self.generate(node.operand)
        return f"-({operand})"

    def visit_ULengthOP(self, node: astnodes.ULengthOP) -> str:
        operand = self.generate(node.operand)
        return f"l2c::get_length({operand})"

    def visit_ULNotOp(self, node: astnodes.ULNotOp) -> str:
        operand = self.generate(node.operand)
        return f"(!{operand})"

    def visit_Call(self, node: astnodes.Call) -> str:
        func = self.generate(node.func)
        # Mangle 'main' function call to avoid C++ ::main conflict
        func = "_l2c_main" if func == "main" else func
        args = []
        for i, arg in enumerate(node.args):
            generated = self.generate(arg)
            if generated is None:
                raise TypeError(f"Cannot generate code for argument {i} of type {type(arg).__name__} in Call to {func}")
            args.append(generated)

        # Check if this is a call to a global library function (e.g., print, tonumber)
        if self._is_global_function_call(node):
            # Global library functions are in l2c namespace and don't need state parameter
            args_str = ", ".join(args) if args else ""
            # Global library functions are in l2c namespace and don't need state parameter
            # Check if func already has l2c:: prefix (from visit_Name)
            if func.startswith("l2c::"):
                return f"{func}({args_str})"
            return f"l2c::{func}({args_str})"
        elif self._is_library_method_call(node):
            # Library method calls like io.write, string.format, math.sqrt
            # These become: struct_name::method(args)
            return self._generate_library_method_call(node, args)
        else:
            # Regular function calls don't include state parameter
            args_str = ", ".join(args) if args else ""
            return f"{func}({args_str})"

    def visit_Invoke(self, node: astnodes.Invoke) -> str:
        """Handle method calls like obj:method(args) as expressions.
        
        In Lua, obj:method(args) is sugar for obj.method(obj, args).
        For Invoke nodes: node.source = object, node.func = method name, node.args = arguments
        """
        # Known string methods that should use string_lib::
        STRING_METHODS = {'sub', 'find', 'gmatch', 'gsub', 'format', 'lower', 'upper', 
                         'len', 'rep', 'reverse', 'byte', 'char', 'match', 'dump'}
        
        # For Invoke nodes, node.source is the object, node.func is the method name
        obj = node.source
        method = node.func
        
        # Get object name
        if isinstance(obj, astnodes.Name):
            obj_name = obj.id
        else:
            obj_name = self.generate(obj)
        
        # Get method name
        if isinstance(method, astnodes.Name):
            method_name = method.id
        else:
            method_name = str(method)
        
        # Check if this is a string method on a variable
        if method_name in STRING_METHODS:
            # String method: seq:sub(a,b) -> string_lib::sub(seq, a, b)
            args = [self.generate(arg) for arg in node.args]
            args_str = ", ".join(args) if args else ""
            return f"string_lib::{method_name}({obj_name}{', ' if args_str else ''}{args_str})"
        else:
            # Generic method call: obj:method() -> obj.method(obj)
            args = [self.generate(arg) for arg in node.args]
            args_str = ", ".join(args) if args else ""
            return f"{obj_name}.{method_name}({obj_name}{', ' if args_str else ''}{args_str})"

    def visit_Dots(self, node: astnodes.Dots) -> str:
        """Handle ... (varargs) in expressions.
        
        In Lua, ... expands to all varargs passed to the function.
        For now, generate a placeholder since C++ variadic templates are complex.
        """
        # Generate a placeholder that won't break compilation
        return "/* variadic args */"

    def _is_global_function_call(self, node: astnodes.Call) -> bool:
        """Check if this is a call to a global Lua library function

        Global functions like print, tonumber, tostring, etc. are in l2c namespace
        and don't require the state parameter.

        Args:
            node: Call AST node

        Returns:
            True if this is a global library function call, False otherwise
        """
        if self._library_registry is None:
            return False

        # Check if func is a Name node (direct function call like print())
        if isinstance(node.func, astnodes.Name):
            func_name = node.func.id
            return self._library_registry.is_global_function(func_name)

        return False

    def _is_library_method_call(self, node: astnodes.Call) -> bool:
        if not isinstance(node.func, astnodes.Index):
            return False
        if not isinstance(node.func.value, astnodes.Name):
            return False
        lib_name = node.func.value.id
        return self._library_registry.is_standard_library(lib_name) if self._library_registry else False

    def _generate_library_method_call(self, node: astnodes.Call, args: list) -> str:
        lib_name = node.func.value.id
        method_name = node.func.idx.id if hasattr(node.func.idx, 'id') else str(node.func.idx)
        
        lib_func_map = {
            'io': {'write': 'io_write', 'flush': 'io_flush', 'read': 'io_read'},
            'string': {'format': 'string_format', 'len': 'string_len', 'sub': 'string_sub', 
                       'upper': 'string_upper', 'lower': 'string_lower', 'byte': 'string_byte',
                       'char': 'string_char', 'rep': 'string_rep', 'find': 'string_find',
                       'gsub': 'string_gsub', 'match': 'string_match', 'gmatch': 'string_gmatch'},
            'math': {'sqrt': 'math_sqrt', 'abs': 'math_abs', 'floor': 'math_floor',
                     'ceil': 'math_ceil', 'sin': 'math_sin', 'cos': 'math_cos',
                     'tan': 'math_tan', 'log': 'math_log', 'exp': 'math_exp',
                     'pow': 'math_pow', 'min': 'math_min', 'max': 'math_max',
                     'random': 'math_random', 'randomseed': 'math_randomseed',
                     'modf': 'math_modf', 'fmod': 'math_fmod', 'atan': 'math_atan',
                     'asin': 'math_asin', 'acos': 'math_acos', 'deg': 'math_deg',
                     'rad': 'math_rad', 'huge': 'math_huge'},
            'table': {'unpack': 'table_unpack', 'remove': 'table_remove', 'sort': 'table_sort',
                      'concat': 'table_concat', 'insert': 'table_insert', 'pack': 'table_pack'},
            'os': {'clock': 'os_clock', 'time': 'os_time', 'date': 'os_date', 'exit': 'os_exit',
                   'difftime': 'os_difftime', 'getenv': 'os_getenv', 'remove': 'os_remove',
                   'rename': 'os_rename', 'tmpname': 'os_tmpname'},
        }
        
        # Use appropriate namespace based on library
        args_str = ", ".join(args) if args else ""
        
        # String library uses string_lib:: namespace (has TValue-aware implementations)
        if lib_name == 'string':
            method_map = {
                'format': 'format', 'len': 'len', 'sub': 'sub',
                'upper': 'upper', 'lower': 'lower', 'byte': 'byte',
                'char': 'char_', 'rep': 'rep', 'find': 'find',
                'gsub': 'gsub', 'match': 'match', 'gmatch': 'gmatch'
            }
            func_name = method_map.get(method_name, method_name)
            return f"string_lib::{func_name}({args_str})"
        
        # Table, io, math, os libraries use l2c:: namespace
        lib_func_map = {
            'io': {'write': 'io_write', 'flush': 'io_flush', 'read': 'io_read'},
            'math': {'sqrt': 'math_sqrt', 'abs': 'math_abs', 'floor': 'math_floor',
                     'ceil': 'math_ceil', 'sin': 'math_sin', 'cos': 'math_cos',
                     'tan': 'math_tan', 'log': 'math_log', 'exp': 'math_exp',
                     'pow': 'math_pow', 'min': 'math_min', 'max': 'math_max',
                     'random': 'math_random', 'randomseed': 'math_randomseed',
                     'modf': 'math_modf', 'fmod': 'math_fmod', 'atan': 'math_atan',
                     'asin': 'math_asin', 'acos': 'math_acos', 'deg': 'math_deg',
                     'rad': 'math_rad', 'huge': 'math_huge'},
            'table': {'unpack': 'table_unpack', 'remove': 'table_remove', 'sort': 'table_sort',
                      'concat': 'table_concat', 'insert': 'table_insert', 'pack': 'table_pack'},
            'os': {'clock': 'os_clock', 'time': 'os_time', 'date': 'os_date', 'exit': 'os_exit',
                   'difftime': 'os_difftime', 'getenv': 'os_getenv', 'remove': 'os_remove',
                   'rename': 'os_rename', 'tmpname': 'os_tmpname'},
        }
        func_name = lib_func_map.get(lib_name, {}).get(method_name, f"{lib_name}_{method_name}")
        return f"l2c::{func_name}({args_str})"

    def _generate_g_table_access(self, node: astnodes.Index) -> str:
        """Generate C++ code for G table access using bracket notation

        G table access uses bracket notation for all levels:
        - G.C.HAND_LEVELS[0] → G["C"]["HAND_LEVELS"][0]
        - G["key"] → G["key"]
        - G.key → G["key"] (both work uniformly)

        Args:
            node: Index AST node

        Returns:
            str: Generated C++ code with bracket notation
        """
        parts = []
        current = node

        while current is not None:
            if isinstance(current.value, astnodes.Name):
                if current.value.id == "G" and isinstance(current.idx, astnodes.Name):
                    parts.append(f'"{current.idx.id}"')
                elif isinstance(current.idx, astnodes.Name):
                    parts.append(f'"{current.idx.id}"')
                elif isinstance(current.idx, astnodes.Number):
                    parts.append(f"{current.idx.n}")
                elif isinstance(current.idx, astnodes.String):
                    idx_content = current.idx.s.decode() if isinstance(current.idx.s, bytes) else current.idx.s
                    idx_content = idx_content.replace('\\', '\\\\').replace('"', '\\"')
                    parts.append(f'"{idx_content}"')
                else:
                    parts.append(self.generate(current.idx))
            else:
                parts.append(self.generate(current.idx))

            if hasattr(current, 'value') and isinstance(current.value, astnodes.Index):
                current = current.value
            else:
                break

        parts.reverse()
        if len(parts) == 1:
            return 'G[' + parts[0] + ']'  # G[0] or G["key"]
        else:
            return 'G[' + ']['.join(parts) + ']'  # G["A"]["B"]



    def visit_Index(self, node: astnodes.Index) -> str:
        """Generate C++ index expression

        Uses call convention registry to determine how to generate access:
        - NAMESPACE: X::Y() for standard libraries
        - FLAT: X_Y() for flat function names
        - FLAT_NESTED: X_Y_Z() for flattened nested paths
        - TABLE: X["Y"] for dynamic table access

        Special handling for G table: uses bracket notation G["x"] for all access patterns

        Args:
            node: Index AST node with value and idx

        Returns:
            str: Generated C++ code
        """
        # Check if this is a G table access
        if isinstance(node.value, astnodes.Name) and node.value.id == "G":
            return self._generate_g_table_access(node)

        # Get root module and its convention
        root_module = get_root_module(node)
        config = self._convention_registry.get_config(root_module)
        
        if config.convention == CallConvention.NAMESPACE:
            # For NAMESPACE: generate X::Y or use cpp_namespace if specified
            if isinstance(node.value, astnodes.Name) and isinstance(node.idx, astnodes.Name):
                cpp_ns = config.cpp_namespace or node.value.id
                return f"{cpp_ns}::{node.idx.id}"
            # Nested index - use namespace for first level, then ::
            parts = flatten_index_chain_parts(node)
            if len(parts) >= 2:
                cpp_ns = config.cpp_namespace or parts[0]
                return cpp_ns + "::" + "::".join(parts[1:])
            # Fall through to table access
            value = self.generate(node.value)
            idx = self.generate(node.idx)
            return f'{value}["{idx}"]'
        
        elif config.convention in (CallConvention.FLAT, CallConvention.FLAT_NESTED):
            # For FLAT/FLAT_NESTED: generate flattened name like love_timer_step
            parts = flatten_index_chain_parts(node)
            if len(parts) >= 2:
                prefix = config.cpp_prefix or f"{parts[0]}_"
                if config.convention == CallConvention.FLAT and len(parts) > 2:
                    # FLAT: only flatten one level (X.Y -> X_Y, X.Y.Z -> X_Y["Z"])
                    return prefix + parts[1]
                else:
                    # FLAT_NESTED: flatten all levels (X.Y.Z -> X_Y_Z)
                    return prefix + "_".join(parts[1:])
            # Single element - shouldn't happen for Index, but handle gracefully
            value = self.generate(node.value)
            idx = self.generate(node.idx)
            return f'{value}["{idx}"]'
        
        else:
            # TABLE or unknown convention: use bracket notation
            value = self.generate(node.value)
            idx = self.generate(node.idx)
            
            if hasattr(node, 'notation') and str(node.notation) == "IndexNotation.DOT":
                return f'{value}["{idx}"]'
            else:
                return f"{value}[{idx}]"

    def _is_library_index(self, node: astnodes.Index) -> bool:
        """Check if Index node represents a library function reference

        Library functions have pattern: Index.value is Name with library name.
        Examples: io.write, math.sqrt, string.format

        Args:
            node: Index AST node

        Returns:
            True if this is a library function reference, False otherwise
        """
        if self._library_registry is None:
            return False

        if not isinstance(node.value, astnodes.Name):
            return False

        library_name = node.value.id
        return self._library_registry.is_standard_library(library_name)

    def _is_library_function_reference(self, node) -> bool:
        """Check if node is a library function reference like math.floor

        For 'or' expressions where left is a library function (e.g., math.ifloor),
        we can emit the function directly since stub functions always "exist".

        Args:
            node: AST node to check

        Returns:
            True if this is a library function reference, False otherwise
        """
        if not isinstance(node, astnodes.Index):
            return False
        if not isinstance(node.value, astnodes.Name):
            return False
        lib_name = node.value.id
        return lib_name in ('math', 'io', 'string', 'table', 'os')

    def visit_Table(self, node: astnodes.Table) -> str:
        """Generate C++ table constructor

        Handles Lua table constructors like:
        - { a, b, c } - array part
        - { x = 1, y = 2 } - hash part
        - { a, x = 1, b } - mixed

        Args:
            node: Table AST node with fields list

        Returns:
            str: C++ expression that creates and initializes the table
        """
        if not node.fields:
            return "NEW_TABLE"

        # Build table initialization as a lambda expression
        # [=]() { TABLE t = NEW_TABLE; t[1] = a; t[2] = b; return t; }()
        lines = []
        lines.append("[=]() {")
        lines.append("    TABLE t = NEW_TABLE;")

        array_index = 1  # Lua arrays are 1-indexed
        for field in node.fields:
            value = self.generate(field.value)

            if field.key is None:
                # Array part: t[1] = value, t[2] = value, ...
                lines.append(f"    t[NUMBER({array_index})] = {value};")
                array_index += 1
            else:
                # Hash part: t["key"] = value or t[key] = value
                key = self.generate(field.key)
                if hasattr(field.key, 'id'):
                    # Simple name key: t["key"] = value
                    lines.append(f"    t[STRING(\"{field.key.id}\")] = {value};")
                else:
                    # Expression key: t[key] = value
                    lines.append(f"    t[{key}] = {value};")

        lines.append("    return t;")
        lines.append("}()")

        return "\n".join(lines)

    def visit_AnonymousFunction(self, node: astnodes.AnonymousFunction) -> str:
        """Generate C++ lambda expression for anonymous function"""
        params = []
        for arg in node.args:
            if hasattr(arg, 'id'):
                params.append(f"const auto& {arg.id}")
            else:
                params.append("const auto& arg")

        params_str = ", ".join(params)

        return_type = "auto"
        type_info = ASTAnnotationStore.get_type(node)
        if type_info is not None:
            return_type = type_info.cpp_type()

        if self._stmt_gen is None:
            body_str = "    /* Anonymous function body - stmt_gen not available */"
        else:
            body_lines = []
            for stmt in node.body.body:
                body_lines.append(f"    {self._stmt_gen.generate(stmt)}")
            body_str = "\n".join(body_lines) if body_lines else ""

        return f"[&]({params_str}) -> {return_type} {{\n{body_str}\n}}"

    def visit_Assign(self, node: astnodes.Assign) -> str:
        """Generate C++ assignment expression

        Args:
            node: Assign AST node with targets and values

        Returns:
            str: C++ assignment expression (target = value, no semicolon)
        """
        target = self.generate(node.targets[0])
        value = self.generate(node.values[0])
        return f"{target} = {value}"
