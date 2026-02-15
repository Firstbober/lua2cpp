"""Expression generator for Lua2C++ transpiler

Generates C++ code from Lua AST expression nodes.
Implements double-dispatch pattern for literal and name expressions.
"""

from typing import Any, Optional, Set, TYPE_CHECKING
from lua2cpp.core.ast_visitor import ASTVisitor
from lua2cpp.core.library_registry import LibraryFunctionRegistry as _LibraryFunctionRegistry
from lua2cpp.core.types import ASTAnnotationStore, TypeKind

try:
    from luaparser import astnodes
except ImportError:
    raise ImportError(
        "luaparser is required. Install with: pip install luaparser"
    )

if TYPE_CHECKING:
    from lua2cpp.core.library_registry import LibraryFunctionRegistry


class ExprGenerator(ASTVisitor):
    """Generates C++ code from Lua AST expression nodes

    Focuses on literal expressions (Number, String, Boolean) and Name nodes.
    More complex expressions (operators, calls, indexing) are handled separately.
    """

    def __init__(self, library_registry: Optional[_LibraryFunctionRegistry] = None, stmt_gen: Optional[Any] = None) -> None:
        """Initialize expression generator

        Args:
            library_registry: Optional registry for detecting library function calls.
                            If provided, generates API syntax for library functions.
            stmt_gen: Optional statement generator for generating anonymous function bodies.
        """
        super().__init__()
        self._library_registry = library_registry
        self._stmt_gen = stmt_gen

        # Module context for name mangling
        self._module_prefix: str = ""
        self._module_state: Set[str] = set()

    def set_module_context(self, prefix: str, module_state: Set[str]) -> None:
        self._module_prefix = prefix
        self._module_state = module_state

    def generate(self, node: Any) -> str:
        """Generate C++ code from an expression node using double-dispatch

        Args:
            node: AST node (expression node)

        Returns:
            str: Generated C++ code as a string
        """
        return self.visit(node)

    def visit_Number(self, node: astnodes.Number) -> str:
        """Generate C++ number literal

        Args:
            node: Number AST node

        Returns:
            str: Number literal as raw value
        """
        # Lua numbers are always double in C++ representation
        # Return the numeric value as-is (Lua parser handles formatting)
        return str(node.n)

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
        if name in self._module_state:
            return f"{self._module_prefix}_{name}"
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
        return f"{left} + {right}"

    def visit_SubOp(self, node: astnodes.SubOp) -> str:
        """Generate C++ subtraction operation

        Args:
            node: SubOp AST node with left and right operands

        Returns:
            str: C++ subtraction expression
        """
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} - {right}"

    def visit_MultOp(self, node: astnodes.MultOp) -> str:
        """Generate C++ multiplication operation

        Args:
            node: MultOp AST node with left and right operands

        Returns:
            str: C++ multiplication expression
        """
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} * {right}"

    def visit_FloatDivOp(self, node: astnodes.FloatDivOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} / {right}"

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
        return f"{left} == {right}"

    def visit_LessThanOp(self, node: astnodes.LessThanOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} < {right}"

    def visit_GreaterThanOp(self, node: astnodes.GreaterThanOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} > {right}"

    def visit_LessOrEqThanOp(self, node: astnodes.LessOrEqThanOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} <= {right}"

    def visit_GreaterOrEqThanOp(self, node: astnodes.GreaterOrEqThanOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} >= {right}"

    def visit_NotEqToOp(self, node: astnodes.NotEqToOp) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} != {right}"

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
            return f"(is_truthy({cond}) ? ({truthy}) : ({falsy}))"
        
        if self._is_library_function_reference(node.left):
            return self.generate(node.right)
        
        # Regular or: (cond) ? (cond) : (fallback)
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"(({left}) ? ({left}) : ({right}))"

    def visit_UMinusOp(self, node: astnodes.UMinusOp) -> str:
        operand = self.generate(node.operand)
        return f"-({operand})"

    def visit_ULengthOP(self, node: astnodes.ULengthOP) -> str:
        operand = self.generate(node.operand)
        return f"l2c::get_length({operand})"

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
        lib_map = {
            'io': 'io',
            'string': 'string_lib',
            'math': 'math_lib',
            'table': 'table_lib',
            'os': 'os_lib',
        }
        cpp_lib = lib_map.get(lib_name, lib_name)
        args_str = ", ".join(args) if args else ""
        return f"{cpp_lib}::{method_name}({args_str})"

    def visit_Index(self, node: astnodes.Index) -> str:
        """Generate C++ index expression

        For library function calls (io.write, math.sqrt), generates member access
        syntax (io.write) instead of pointer access (io->write).

        For table member access, uses bracket notation (["key"]) instead of pointer
        access (->key) since TABLE is a value type, not a pointer.

        Args:
            node: Index AST node with value and idx

        Returns:
            str: Generated C++ code
        """
        value = self.generate(node.value)
        idx = self.generate(node.idx)

        if hasattr(node, 'notation') and str(node.notation) == "IndexNotation.DOT":
            if self._is_library_index(node):
                lib_map = {
                    'io': 'io',
                    'string': 'string_lib',
                    'math': 'math_lib',
                    'table': 'table_lib',
                    'os': 'os_lib',
                }
                lib_name = node.value.id if isinstance(node.value, astnodes.Name) else value
                cpp_lib = lib_map.get(lib_name, value)
                return f"{cpp_lib}::{idx}"
            else:
                # Default to bracket notation for table member access
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

        For now, always returns NEW_TABLE macro for simplicity.

        Args:
            node: Table AST node

        Returns:
            str: NEW_TABLE macro string
        """
        return "NEW_TABLE"

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
