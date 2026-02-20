"""Class generator for Lua OOP to C++ transpilation

Detects Lua OOP patterns (Class = Parent:extend()) and generates C++ class declarations
with proper inheritance, constructors, and member methods.

Translation rules (from oop_translation_spec.md):
- Class = Parent:extend() -> class Class : public Parent { };
- function Class:init(...) -> Class::Class(...) constructor
- self.x -> this->x
- Parent.init(self, ...) -> parent constructor call in initializer list
"""

from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

try:
    from luaparser import astnodes
except ImportError:
    raise ImportError("luaparser is required. Install with: pip install luaparser")

from ..core.ast_visitor import ASTVisitor


@dataclass
class MethodInfo:
    """Represents a method in a Lua class"""
    name: str
    is_constructor: bool
    params: List[str]
    body: Any  # astnodes.Block
    parent_init_call: Optional[Tuple[str, List[Any]]] = None  # (parent_class, args)


@dataclass 
class ClassInfo:
    """Represents a Lua class for C++ generation"""
    name: str
    parent: str
    methods: List[MethodInfo] = field(default_factory=list)
    member_vars: Set[str] = field(default_factory=set)


class ClassDetector(ASTVisitor):
    """Detects OOP class definitions in Lua AST
    
    Detects patterns:
    - Class = Parent:extend() - class declaration with inheritance
    - function Class:method() - instance method
    - function Class.init(self, ...) - constructor pattern
    """
    
    def __init__(self):
        super().__init__()
        self.classes: Dict[str, ClassInfo] = {}
        self._current_class: Optional[str] = None
        
    def detect(self, chunk: astnodes.Chunk) -> Dict[str, ClassInfo]:
        """Scan AST and return detected classes"""
        self.visit(chunk)
        return self.classes
    
    def visit_Assign(self, node: astnodes.Assign) -> None:
        """Detect Class = Parent:extend() pattern"""
        if not node.targets:
            return
            
        target = node.targets[0]
        if not isinstance(target, astnodes.Name):
            return
            
        class_name = target.id
        
        # Check if value is Parent:extend()
        if isinstance(node.values[0], astnodes.Invoke):
            invoke = node.values[0]
            if (isinstance(invoke.func, astnodes.Name) and 
                invoke.func.id == "extend" and
                isinstance(invoke.source, astnodes.Name)):
                parent_name = invoke.source.id
                self.classes[class_name] = ClassInfo(
                    name=class_name,
                    parent=parent_name
                )
    
    def visit_Function(self, node: astnodes.Function) -> None:
        """Detect function Class.method() or function Class:method()"""
        # Handle function Class.method(self, ...) pattern
        if isinstance(node.name, astnodes.Index):
            if isinstance(node.name.value, astnodes.Name) and isinstance(node.name.idx, astnodes.Name):
                class_name = node.name.value.id
                method_name = node.name.idx.id
                
                if class_name in self.classes:
                    # Check if this is init (constructor)
                    is_constructor = method_name == "init"
                    
                    # Extract parameter names
                    params = []
                    for arg in node.args:
                        if isinstance(arg, astnodes.Name):
                            params.append(arg.id)
                    
                    # Look for Parent.init(self, ...) calls in the body
                    parent_init = self._find_parent_init_call(node.body, self.classes[class_name].parent)
                    
                    method = MethodInfo(
                        name=method_name,
                        is_constructor=is_constructor,
                        params=params,
                        body=node.body,
                        parent_init_call=parent_init
                    )
                    self.classes[class_name].methods.append(method)
        
        # Handle function Class:method(...) pattern (colon syntax in function name)
        elif hasattr(node.name, 'id') and ':' in str(type(node.name)):
            # This is rare in parsed AST, usually becomes Index
            pass
    
    def visit_Method(self, node) -> None:
        """Detect Method nodes (function Class:method() syntax)"""
        # Method nodes have: source (class name), name (method name), args, body
        if hasattr(node, 'source') and hasattr(node.source, 'id'):
            class_name = node.source.id
            method_name = node.name.id if hasattr(node.name, 'id') else str(node.name)
            
            if class_name in self.classes:
                # Check if this is init (constructor)
                is_constructor = method_name == "init"
                
                # Extract parameter names (self is implicit in Method, not in args)
                params = ['self']  # Add implicit self
                for arg in node.args:
                    if isinstance(arg, astnodes.Name):
                        params.append(arg.id)
                
                # Look for Parent.init(self, ...) calls in the body
                parent_init = self._find_parent_init_call(node.body, self.classes[class_name].parent)
                
                method = MethodInfo(
                    name=method_name,
                    is_constructor=is_constructor,
                    params=params,
                    body=node.body,
                    parent_init_call=parent_init
                )
                self.classes[class_name].methods.append(method)
    
    def _find_parent_init_call(self, body: astnodes.Block, parent_class: str) -> Optional[Tuple[str, List[Any]]]:
        """Find ParentClass.init(self, ...) call in function body"""
        if not body or not hasattr(body, 'body'):
            return None
            
        stmts = body.body if isinstance(body.body, list) else [body.body]
        
        for stmt in stmts:
            # Look for Call nodes
            if isinstance(stmt, astnodes.Call):
                call = stmt
                # Check for Parent.init(self, ...) pattern
                if isinstance(call.func, astnodes.Index):
                    if (isinstance(call.func.value, astnodes.Name) and
                        isinstance(call.func.idx, astnodes.Name) and
                        call.func.idx.id == "init"):
                        potential_parent = call.func.value.id
                        if potential_parent == parent_class:
                            # Found parent init call
                            return (parent_class, call.args)
            
            # Recursively check inside if/while/etc blocks
            if hasattr(stmt, 'body') and isinstance(stmt, astnodes.Block):
                result = self._find_parent_init_call(stmt, parent_class)
                if result:
                    return result
                     
        return None


class ClassGenerator:
    """Generates C++ class declarations from detected Lua OOP classes"""
    
    def __init__(self, stmt_generator=None, expr_generator=None):
        """Initialize with optional generators for body translation
        
        Args:
            stmt_generator: StmtGenerator for translating method bodies
            expr_generator: ExprGenerator for translating expressions
        """
        self._stmt_gen = stmt_generator
        self._expr_gen = expr_generator
    
    def generate_class_header(self, classes: Dict[str, ClassInfo], module_name: str) -> str:
        """Generate complete .hpp header file with all class declarations
        
        Args:
            classes: Dictionary of class name to ClassInfo
            module_name: Name for include guard
            
        Returns:
            Complete C++ header file content
        """
        lines = []
        
        # Include guard
        guard_name = f"{module_name.upper()}_HPP"
        lines.append(f"#ifndef {guard_name}")
        lines.append(f"#define {guard_name}")
        lines.append("")
        
        # Standard includes
        lines.append("#include <string>")
        lines.append("#include <functional>")
        lines.append("#include <memory>")
        lines.append("")
        
        # Forward declarations for all classes
        lines.append("// Forward declarations")
        for class_info in classes.values():
            lines.append(f"class {class_info.name};")
        lines.append("")
        
        # Generate each class
        for class_info in classes.values():
            lines.append(self._generate_class_declaration(class_info))
            lines.append("")
        
        # Close include guard
        lines.append(f"#endif // {guard_name}")
        
        return "\n".join(lines)
    
    def _generate_class_declaration(self, class_info: ClassInfo) -> str:
        """Generate single class declaration"""
        lines = []
        
        # Class header with inheritance
        if class_info.parent:
            lines.append(f"class {class_info.name} : public {class_info.parent} {{")
        else:
            lines.append(f"class {class_info.name} {{")
        
        lines.append("public:")
        
        # Generate methods
        for method in class_info.methods:
            if method.is_constructor:
                lines.append(self._generate_constructor(class_info, method))
            else:
                lines.append(self._generate_method(class_info, method))
        
        lines.append("};")
        
        return "\n".join(lines)
    
    def _generate_constructor(self, class_info: ClassInfo, method: MethodInfo) -> str:
        """Generate C++ constructor from init method"""
        lines = []

        # Build parameter list (skip 'self' parameter)
        params = [p for p in method.params if p != "self"]
        param_strs = [f"auto {p}" for p in params]
        params_str = ", ".join(param_strs) if param_strs else ""

        # Constructor signature (NO initializer list - parent init in body)
        lines.append(f"    {class_info.name}({params_str}) {{")

        # Translate body, including parent init call
        if self._stmt_gen and method.body:
            body_lines = self._translate_constructor_body(method.body, class_info.parent)
            for line in body_lines:
                lines.append(f"        {line}")

        lines.append("    }")

        return "\n".join(lines)
    
    def _generate_method(self, class_info: ClassInfo, method: MethodInfo) -> str:
        """Generate C++ method from Lua method"""
        lines = []
        
        # Build parameter list (skip 'self' parameter)
        params = [p for p in method.params if p != "self"]
        param_strs = [f"auto {p}" for p in params]
        params_str = ", ".join(param_strs) if param_strs else ""
        
        # Return type (void for now, could be inferred)
        return_type = "void"
        
        lines.append(f"    {return_type} {method.name}({params_str}) {{")
        
        # Translate body with self -> this
        if self._stmt_gen and method.body:
            body_lines = self._translate_body(method.body)
            for line in body_lines:
                lines.append(f"        {line}")
        
        lines.append("    }")
        
        return "\n".join(lines)
    
    def _translate_constructor_body(self, body: astnodes.Block, parent_class: str) -> List[str]:
        """Translate constructor body, including parent init call"""
        lines = []

        if not body or not hasattr(body, 'body'):
            return lines

        stmts = body.body if isinstance(body.body, list) else [body.body]

        for stmt in stmts:
            if self._stmt_gen:
                code = self._stmt_gen.generate(stmt)
                if code:
                    # Translate self -> this
                    code = self._translate_self_to_this(code)
                    lines.append(code)

        return lines
    
    def _translate_body(self, body: astnodes.Block) -> List[str]:
        """Translate method body with self -> this"""
        lines = []
        
        if not body or not hasattr(body, 'body'):
            return lines
            
        stmts = body.body if isinstance(body.body, list) else [body.body]
        
        for stmt in stmts:
            if self._stmt_gen:
                code = self._stmt_gen.generate(stmt)
                if code:
                    # Translate self -> this
                    code = self._translate_self_to_this(code)
                    lines.append(code)
        
        return lines
    
    def _translate_self_to_this(self, code: str) -> str:
        """Replace self. with this-> in generated code"""
        return code.replace("self.", "this->")
    
    def _translate_simple_expr(self, node: Any) -> str:
        """Simple expression translation without full generator"""
        if isinstance(node, astnodes.Name):
            return node.id
        elif isinstance(node, astnodes.Number):
            return str(node.n)
        elif isinstance(node, astnodes.String):
            content = node.s.decode() if isinstance(node.s, bytes) else node.s
            return f'"{content}"'
        elif isinstance(node, astnodes.TrueExpr):
            return "true"
        elif isinstance(node, astnodes.FalseExpr):
            return "false"
        elif isinstance(node, astnodes.Nil):
            return "nullptr"
        else:
            return "/* expr */"


def generate_class_headers(classes: Dict[str, ClassInfo], output_dir: str, module_name: str = "lua_classes") -> Dict[str, str]:
    """Generate .hpp header files for all detected classes
    
    Args:
        classes: Dictionary of class name to ClassInfo
        output_dir: Directory to write .hpp files
        module_name: Name for include guard
        
    Returns:
        Dictionary mapping class name to generated .hpp content
    """
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    generated_files = {}
    
    for class_info in classes.values():
        # Generate .hpp file content
        header_content = _generate_class_header(class_info, classes, module_name)
        
        # Write to file
        filename = os.path.join(output_dir, f"{class_info.name}.hpp")
        with open(filename, 'w') as f:
            f.write(header_content)
        
        generated_files[class_info.name] = filename
    
    return generated_files


def generate_class_implementations(classes: Dict[str, ClassInfo], output_dir: str, module_name: str = "lua_classes") -> Dict[str, str]:
    """Generate .cpp implementation files for all detected classes
    
    Args:
        classes: Dictionary of class name to ClassInfo
        output_dir: Directory to write .cpp files
        module_name: Name for include guard (same as used for header)
        
    Returns:
        Dictionary mapping class name to generated .cpp content
    """
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    generated_files = {}
    
    for class_info in classes.values():
        # Generate .cpp file content
        cpp_content = _generate_class_implementation(class_info, classes, module_name)
        
        # Write to file
        filename = os.path.join(output_dir, f"{class_info.name}.cpp")
        with open(filename, 'w') as f:
            f.write(cpp_content)
        
        generated_files[class_info.name] = filename
    
    return generated_files


def _generate_class_header(class_info: ClassInfo, all_classes: Dict[str, ClassInfo], module_name: str, stmt_gen=None, expr_gen=None) -> str:
    """Generate single .hpp header file for a class with proper includes and forward declarations"""
    lines = []
    
    # Include guard - pragma once for modern C++
    lines.append(f"#pragma once")
    lines.append("")
    
    # Include Object base class
    lines.append('#include "../runtime/object.hpp"')
    
    # Include parent class header if parent exists
    if class_info.parent and class_info.parent != "Object":
        lines.append(f'#include "{class_info.parent}.hpp"')
    
    # Add standard includes
    lines.append("#include <string>")
    lines.append("#include <functional>")
    lines.append("#include <memory>")
    lines.append("")
    
    # Forward declarations for other classes
    lines.append("// Forward declarations")
    for other_class in all_classes.values():
        if other_class.name != class_info.name:
            lines.append(f"class {other_class.name};")
    lines.append("")
    
    # Create generator instance for class declaration
    generator = ClassGenerator(stmt_gen, expr_gen)
    lines.append(generator._generate_class_declaration(class_info))
    lines.append("")
    
    return "\n".join(lines)


def _generate_class_implementation(class_info: ClassInfo, all_classes: Dict[str, ClassInfo], module_name: str) -> str:
    """Generate single .cpp implementation file for a class"""
    lines = []
    
    # Include guard and header
    guard_name = f"{module_name.upper()}_CPP"
    lines.append(f"#ifndef {guard_name}")
    lines.append(f"#define {guard_name}")
    lines.append("")
    
    # Include the corresponding .hpp
    lines.append(f'#include "{class_info.name}.hpp"')
    
    # Add includes for parent class if exists
    if class_info.parent:
        lines.append("")
        # Check if parent class is in our detected classes
        if class_info.parent in all_classes:
            lines.append(f'#include "{class_info.parent}.hpp"')
    
    # Add includes for base Object class
    lines.append("")
    lines.append("#include <string>")
    lines.append("#include <functional>")
    lines.append("")
    
    # Generate methods (constructors first, then regular methods)
    for method in sorted(class_info.methods, key=lambda m: m.is_constructor, reverse=True):
        if method.is_constructor:
            lines.append(_generate_constructor_body(class_info, method))
        else:
            lines.append(_generate_method_body(class_info, method))
    
    # Close include guard
    lines.append("")
    lines.append(f"#endif // {guard_name}")
    
    return "\n".join(lines)


    def _generate_constructor_body(class_info: ClassInfo, method: MethodInfo) -> str:
        """Generate constructor implementation body (parent init in body, no initializer list)"""
        lines = []

        # Build parameter list (skip 'self' parameter)
        params = [p for p in method.params if p != "self"]
        param_strs = [f"auto {p}" for p in params]
        params_str = ", ".join(param_strs) if param_strs else ""

        lines.append(f"{class_info.name}::{class_info.name}({params_str}) {{")

        # Call parent init if parent is Object (the base class)
        if class_info.parent == "Object":
            lines.append("    Object::init(this);")

        # Translate body (include parent init call)
        if method.body and hasattr(method.body, 'body'):
            body_stmts = method.body.body if isinstance(method.body.body, list) else [method.body.body]
            for stmt in body_stmts:
                # Translate statement with self -> this
                code = _translate_statement(stmt)
                if code:
                    lines.append(f"    {code}")

        lines.append("}")

        return "\n".join(lines)


def _generate_method_body(class_info: ClassInfo, method: MethodInfo) -> str:
    """Generate method implementation body with self -> this translation"""
    lines = []
    
    # Build parameter list (skip 'self' parameter)
    params = [p for p in method.params if p != "self"]
    param_strs = [f"auto {p}" for p in params]
    params_str = ", ".join(param_strs) if param_strs else ""
    
    lines.append(f"void {class_info.name}::{method.name}({params_str}) {{")
    
    # Translate body with self -> this
    if method.body and hasattr(method.body, 'body'):
        body_stmts = method.body.body if isinstance(method.body.body, list) else [method.body.body]
        for stmt in body_stmts:
            code = _translate_statement(stmt)
            if code:
                lines.append(f"    {code}")
    
    lines.append("}")
    
    return "\n".join(lines)


def _translate_statement(stmt: Any) -> Optional[str]:
    """Translate a single statement to C++"""
    if not hasattr(stmt, '__class__'):
        return None
    
    class_name = stmt.__class__.__name__
    
    if class_name == 'Assignment':
        var = stmt.var
        val = stmt.val
        var_str = _translate_expression(var)
        val_str = _translate_expression(val)
        return f"{var_str} = {val_str}"
    
    elif class_name == 'Call':
        func = stmt.func
        args = []
        for arg in stmt.args:
            args.append(_translate_expression(arg))
        func_str = _translate_expression(func)
        return f"{func_str}({', '.join(args)})"
    
    elif class_name == 'If':
        test = _translate_expression(stmt.test)
        lines = []
        lines.append(f"if ({test}) {{")
        if hasattr(stmt, 'body') and stmt.body and hasattr(stmt.body, 'body'):
            for sub_stmt in stmt.body.body:
                code = _translate_statement(sub_stmt)
                if code:
                    lines.append(f"    {code}")
        lines.append("}")
        if hasattr(stmt, 'orelse') and stmt.orelse and hasattr(stmt.orelse, 'body'):
            lines.append("else {{")
            for sub_stmt in stmt.orelse.body:
                code = _translate_statement(sub_stmt)
                if code:
                    lines.append(f"    {code}")
            lines.append("}")
        return "\n".join(lines)
    
    elif class_name == 'While':
        test = _translate_expression(stmt.test)
        lines = []
        lines.append(f"while ({test}) {{")
        if hasattr(stmt, 'body') and stmt.body and hasattr(stmt.body, 'body'):
            for sub_stmt in stmt.body.body:
                code = _translate_statement(sub_stmt)
                if code:
                    lines.append(f"    {code}")
        lines.append("}")
        return "\n".join(lines)
    
    elif class_name == 'Block':
        lines = []
        if hasattr(stmt, 'body') and stmt.body:
            for sub_stmt in stmt.body:
                code = _translate_statement(sub_stmt)
                if code:
                    lines.append(code)
        return "\n".join(lines)
    
    elif class_name == 'Return':
        val = _translate_expression(stmt.val)
        return f"return {val}"
    
    elif class_name == 'Index':
        base = _translate_expression(stmt.value)
        idx = _translate_expression(stmt.idx)
        return f"{base}[{idx}]"
    
    elif class_name == 'Concat':
        left = _translate_expression(stmt.left)
        right = _translate_expression(stmt.right)
        return f"{left} + {right}"
    
    elif class_name == 'Unop':
        op = stmt.op
        arg = _translate_expression(stmt.arg)
        if op == 'not':
            return f"!{arg}"
        elif op == 'minus':
            return f"-{arg}"
        elif op == 'plus':
            return f"+{arg}"
        elif op == 'length':
            return f"({arg}).length()"
        return f"{op}({arg})"
    
    elif class_name == 'Binop':
        left = _translate_expression(stmt.left)
        right = _translate_expression(stmt.right)
        op = stmt.op
        if op == 'add':
            return f"{left} + {right}"
        elif op == 'sub':
            return f"{left} - {right}"
        elif op == 'mul':
            return f"{left} * {right}"
        elif op == 'div':
            return f"{left} / {right}"
        elif op == 'mod':
            return f"{left} % {right}"
        elif op == 'eq':
            return f"{left} == {right}"
        elif op == 'neq':
            return f"{left} != {right}"
        elif op == 'lt':
            return f"{left} < {right}"
        elif op == 'lte':
            return f"{left} <= {right}"
        elif op == 'gt':
            return f"{left} > {right}"
        elif op == 'gte':
            return f"{left} >= {right}"
        return f"{left} {op} {right}"
    
    return None


def _translate_expression(expr: Any) -> Optional[str]:
    """Translate a single expression to C++"""
    if not hasattr(expr, '__class__'):
        return None
    
    class_name = expr.__class__.__name__
    
    if class_name == 'Name':
        return expr.id
    
    elif class_name == 'Number':
        return str(expr.n)
    
    elif class_name == 'String':
        content = expr.s.decode() if isinstance(expr.s, bytes) else expr.s
        return f'"{content}"'
    
    elif class_name == 'TrueExpr':
        return "true"
    
    elif class_name == 'FalseExpr':
        return "false"
    
    elif class_name == 'Nil':
        return "nullptr"
    
    elif class_name == 'Vararg':
        return "..."  # Lua vararg
    
    elif class_name == 'Table':
        # Simple table with string keys: { "x" = 5 }
        lines = ["{"]
        for i, field in enumerate(expr.fields):
            key = _translate_expression(field.key) if field.key else str(i)
            val = _translate_expression(field.value)
            lines.append(f"    {{ {key} = {val} }}")
        lines.append("}")
        return "\n".join(lines)
    
    elif class_name == 'Call':
        func = _translate_expression(expr.func)
        args = []
        for arg in expr.args:
            args.append(_translate_expression(arg))
        return f"{func}({', '.join(args)})"
    
    elif class_name == 'Index':
        base = _translate_expression(expr.value)
        idx = _translate_expression(expr.idx)
        return f"{base}[{idx}]"
    
    elif class_name == 'Concat':
        left = _translate_expression(expr.left)
        right = _translate_expression(expr.right)
        return f"{left} + {right}"
    
    elif class_name == 'Unop':
        op = expr.op
        arg = _translate_expression(expr.arg)
        if op == 'not':
            return f"!{arg}"
        elif op == 'minus':
            return f"-{arg}"
        elif op == 'plus':
            return f"+{arg}"
        elif op == 'length':
            return f"({arg}).length()"
        return f"{op}({arg})"
    
    elif class_name == 'Binop':
        left = _translate_expression(expr.left)
        right = _translate_expression(expr.right)
        op = expr.op
        if op == 'add':
            return f"{left} + {right}"
        elif op == 'sub':
            return f"{left} - {right}"
        elif op == 'mul':
            return f"{left} * {right}"
        elif op == 'div':
            return f"{left} / {right}"
        elif op == 'mod':
            return f"{left} % {right}"
        elif op == 'eq':
            return f"{left} == {right}"
        elif op == 'neq':
            return f"{left} != {right}"
        elif op == 'lt':
            return f"{left} < {right}"
        elif op == 'lte':
            return f"{left} <= {right}"
        elif op == 'gt':
            return f"{left} > {right}"
        elif op == 'gte':
            return f"{left} >= {right}"
        return f"{left} {op} {right}"
    
    return None


def generate_classes_from_ast(chunk: astnodes.Chunk, stmt_gen=None, expr_gen=None) -> Tuple[Dict[str, ClassInfo], str]:
    """Convenience function to detect and generate classes from AST
    
    Args:
        chunk: Parsed Lua AST
        stmt_gen: Optional statement generator for body translation
        expr_gen: Optional expression generator
        
    Returns:
        Tuple of (detected classes dict, generated header content)
    """
    detector = ClassDetector()
    classes = detector.detect(chunk)
    
    generator = ClassGenerator(stmt_gen, expr_gen)
    header = generator.generate_class_header(classes, "lua_classes")
    
    return classes, header
