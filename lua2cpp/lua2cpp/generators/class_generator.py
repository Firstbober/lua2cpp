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

from lua2cpp.core.ast_visitor import ASTVisitor


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
                        elif hasattr(arg, 'id'):
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
            if hasattr(stmt, 'body') and stmt.body:
                result = self._find_parent_init_call(stmt.body, parent_class)
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
        
        # Check for parent init call
        init_list = []
        if method.parent_init_call:
            parent_class, parent_args = method.parent_init_call
            # Skip 'self' argument, translate rest
            arg_strs = []
            for arg in parent_args:
                if isinstance(arg, astnodes.Name) and arg.id == "self":
                    continue
                if self._expr_gen:
                    arg_strs.append(self._expr_gen.generate(arg))
                else:
                    arg_strs.append(self._translate_simple_expr(arg))
            if arg_strs:
                init_list.append(f": {parent_class}({', '.join(arg_strs)})")
        
        # Constructor signature
        init_list_str = " " + " ".join(init_list) if init_list else ""
        lines.append(f"    {class_info.name}({params_str}){init_list_str} {{")
        
        # Translate body (skip parent init call which goes to init list)
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
        """Translate constructor body, skipping parent init call"""
        lines = []
        
        if not body or not hasattr(body, 'body'):
            return lines
            
        stmts = body.body if isinstance(body.body, list) else [body.body]
        
        for stmt in stmts:
            # Skip the Parent.init(self, ...) call - it's in the init list
            if self._is_parent_init_call(stmt, parent_class):
                continue
            
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
    
    def _is_parent_init_call(self, stmt: Any, parent_class: str) -> bool:
        """Check if statement is ParentClass.init(self, ...) call"""
        if not isinstance(stmt, astnodes.Call):
            return False
            
        call = stmt
        if not isinstance(call.func, astnodes.Index):
            return False
            
        if (isinstance(call.func.value, astnodes.Name) and
            isinstance(call.func.idx, astnodes.Name) and
            call.func.idx.id == "init"):
            return call.func.value.id == parent_class
            
        return False
    
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
