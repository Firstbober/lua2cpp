# Lua to C Transpiler - Complete Implementation Plan

## Project Overview

A maintainable, extensible transpiler from Lua 5.4 to C using the py-lua-parser library.

## Key Design Principles

1. **Modular Architecture** - Each component has a single responsibility
2. **Visitor Pattern** - AST traversal using visitor pattern for extensibility
3. **Type System** - Static type inference where possible, dynamic fallback
4. **VTable System** - Custom luaState implementation via function pointers
5. **Module System** - Handle require() with return values and dependencies
6. **External Libraries via VTable** - Built-in libraries (math, string, love, etc.) provided by luaState implementer

---

## Architecture Overview

```
lua2c/
├── core/
│   ├── ast_visitor.py           # Base visitor pattern for AST traversal
│   ├── context.py               # Translation context (state during compilation)
│   ├── scope.py                # Variable scope management
│   ├── type_inference.py       # Static type inference engine
│   └── symbol_table.py         # Symbol resolution and tracking
├── generators/
│   ├── c_emitter.py            # Main C code generator
│   ├── expr_generator.py       # Expression translation
│   ├── stmt_generator.py       # Statement translation
│   ├── decl_generator.py       # Declaration translation
│   ├── string_pool.py          # String literal pooling system
│   └── naming.py              # Naming scheme: _l2c__dir__dir__file_export
├── runtime/
│   ├── lua_value.h             # Lua value type representation
│   ├── lua_value.c             # Value operations
│   ├── lua_table.h             # Table/metatable implementation
│   ├── lua_table.c
│   ├── lua_state.h             # Custom luaState with VTable
│   ├── lua_state.c
│   ├── closure.h               # Closure support (non-generated header)
│   ├── closure.c
│   ├── gc.h                    # Garbage collector interface
│   ├── gc.c
│   ├── error.h                 # Error handling (longjmp/setjmp)
│   ├── error.c
│   └── module_loader.h         # Module loading for require()
├── module_system/
│   ├── dependency_graph.py     # Build dependency graph from require()
│   ├── module_resolver.py     # Resolve module paths and return types
│   ├── package_config.py      # Track package.path/cpath modifications
│   └── cyclic_detector.py      # Detect circular require() calls
├── cli/
│   ├── main.py                 # Command-line interface
│   ├── config.py               # Compiler configuration
│   └── batch_compiler.py       # Compile multiple modules
├── tests/
│   ├── unit/                   # Unit tests for each component
│   ├── integration/            # End-to-end tests
│   └── fixtures/               # Test Lua files
└── output/
    └── template/               # C header/footer templates
```

---

## Naming Scheme

**Module Export Functions**: `_l2c__<path_parts>__<filename>_export`

**Internal Module Functions**: `_l2c__<path_parts>__<filename>_<funcname>`

**Examples**:
- `require "engine/object"` → calls `_l2c__engine__object_export(L)`
- `require "game"` → calls `_l2c__game_export(L)`
- `require "functions/button_callbacks"` → calls `_l2c__functions__button_callbacks_export(L)`
- Local function `add()` in `engine/object` → `_l2c__engine__object_add`

**Module Path to C Function Mapping**:
```python
def mangle_module_name(require_path: str) -> str:
    """
    Convert require path to C function name.
    "engine/object" → "_l2c__engine__object_export"
    """
    parts = require_path.split('/')
    path_part = '__'.join(parts) if parts else 'main'
    return f'_l2c__{path_part}_export'

def mangle_function_name(module_path: str, func_name: str) -> str:
    """
    Convert module path + function name to C function name.
    "engine/object", "new" → "_l2c__engine__object_new"
    """
    parts = module_path.split('/')
    path_part = '__'.join(parts) if parts else 'main'
    return f'_l2c__{path_part}_{func_name}'
```

---

## Phase 1: Core Infrastructure

### 1.1 AST Visitor System (ast_visitor.py)

```python
class ASTVisitor:
    """Base visitor for AST traversal with extensibility hooks."""
    
    def visit(self, node):
        """Dispatch to appropriate visit method based on node type."""
        method_name = f'visit_{node.__class__.__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node):
        """Default traversal - visit all child nodes."""
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    self.visit(item)
            elif isinstance(value, Node):
                self.visit(value)
    
    # Specific visit methods for each AST node type...
    def visit_Chunk(self, node): ...
    def visit_Block(self, node): ...
    def visit_Assign(self, node): ...
    # ... (all 60+ AST node types)
```

### 1.2 Translation Context (context.py)

```python
class TranslationContext:
    """Shared state during transpilation."""
    
    def __init__(self, config: CompilerConfig):
        self.config = config
        self.current_module: str = None
        self.output = CodeBuilder()
        self.scope_stack: List[Scope] = []
        self.string_pool = StringPool()
        self.error_handler = ErrorHandler()
        self.temp_var_counter = 0
        self.label_counter = 0
        
        # Package configuration (package.path, package.cpath)
        self.package_config = PackageConfig()
        
        # Debug info
        self.line_mapping: Dict[int, int] = {}  # Lua line -> C line
        
    def push_scope(self, scope_type: str):
        """Enter new scope."""
        scope = Scope(self.current_scope_depth + 1, scope_type)
        self.scope_stack.append(scope)
        
    def pop_scope(self):
        """Exit current scope."""
        self.scope_stack.pop()
    
    def get_current_scope(self) -> Scope:
        """Get current scope for symbol lookup."""
        return self.scope_stack[-1]
    
    def gen_temp_var(self, type_hint: str = 'lua_value') -> str:
        """Generate unique temporary variable name."""
        name = f'_t{self.temp_var_counter}'
        self.temp_var_counter += 1
        return name
    
    def gen_label(self, prefix: str = 'L') -> str:
        """Generate unique label."""
        name = f'{prefix}{self.label_counter}'
        self.label_counter += 1
        return name
```

### 1.3 Scope Management (scope.py)

```python
class Scope:
    """Lexical scope with symbol table."""
    
    def __init__(self, depth: int, scope_type: str):
        self.depth = depth
        self.scope_type = scope_type  # 'function', 'block', 'module'
        self.symbols: Dict[str, Symbol] = {}
        self.is_loop = False
        self.needs_cleanup = False
    
    def add_symbol(self, name: str, symbol: Symbol):
        """Add symbol to current scope."""
        self.symbols[name] = symbol
    
    def lookup(self, name: str) -> Optional[Symbol]:
        """Lookup symbol in this scope only."""
        return self.symbols.get(name)
    
    def has_symbol(self, name: str) -> bool:
        """Check if symbol exists in this scope."""
        return name in self.symbols

class Symbol:
    """Symbol information."""
    
    def __init__(self, name: str, symbol_type: SymbolType, 
                 lua_type: Optional[Type] = None, is_const: bool = False):
        self.name = name
        self.symbol_type = symbol_type  # 'local', 'global', 'upvalue', 'param'
        self.lua_type = lua_type  # Inferred type
        self.is_const = is_const
        self.declared_at = None  # Source line
        self.used_at = []        # Usage locations for analysis
        self.is_upvalue = False # Captured by inner function (closure)
```

### 1.4 Type Inference (type_inference.py)

```python
class TypeInferencer(ASTVisitor):
    """Static type inference for Lua code."""
    
    def __init__(self, context: TranslationContext):
        self.context = context
        self.type_env: Dict[str, Type] = {}
    
    def infer(self, node: Node) -> Type:
        """Infer type of expression."""
        result = self.visit(node)
        self.type_env[id(node)] = result
        return result
    
    def visit_Number(self, node) -> Type:
        return Type('number', is_known=True)
    
    def visit_String(self, node) -> Type:
        return Type('string', is_known=True)
    
    def visit_Call(self, node) -> Type:
        # Try to resolve function return type
        func_type = self.infer(node.func)
        if func_type.return_type:
            return func_type.return_type
        return Type('any', is_known=False)
    
    # ... all node types
```

### 1.5 String Pool (string_pool.py)

```python
class StringPool:
    """Pool all string literals for static allocation."""
    
    def __init__(self):
        self.strings: Dict[str, int] = {}
        self.next_index = 0
    
    def intern(self, s: str) -> int:
        """Get index for string literal, add if new."""
        if s not in self.strings:
            self.strings[s] = self.next_index
            self.next_index += 1
        return self.strings[s]
    
    def generate_c_static(self) -> str:
        """Generate C static array declarations."""
        lines = ['static const char *string_pool[] = {']
        for s, idx in sorted(self.strings.items(), key=lambda x: x[1]):
            # Escape string for C
            escaped = s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            lines.append(f'    "{escaped}",  // #{idx}')
        lines.append('    NULL')
        lines.append('};')
        return '\n'.join(lines)
```

---

## Phase 2: C Code Generation

### 2.1 Main C Emitter (c_emitter.py)

```python
class CEmitter:
    """Main C code generator."""
    
    def __init__(self, context: TranslationContext):
        self.context = context
        self.expr_gen = ExpressionGenerator(context)
        self.stmt_gen = StatementGenerator(context)
        self.decl_gen = DeclarationGenerator(context)
        self.naming = NamingScheme()
    
    def generate_module(self, lua_ast: Chunk, module_name: str) -> str:
        """Generate complete C file for a Lua module."""
        self.context.current_module = module_name
        self.context.push_scope('module')
        
        output = CodeBuilder()
        
        # Header includes
        output.extend(self._generate_includes())
        
        # String pool
        output.extend(self.context.string_pool.generate_c_static())
        
        # Module export function declaration
        export_name = self.naming.mangle_module_name(module_name)
        output.add(f'lua_value {export_name}(lua_State *L);')
        
        # Local function declarations
        output.extend(self._generate_forward_declarations())
        
        # Module export function implementation
        output.add(f'\nlua_value {export_name}(lua_State *L)')
        output.add('{')
        
        # Generate body
        self.stmt_gen.generate_block(lua_ast.body, output)
        
        output.add('}')
        
        self.context.pop_scope()
        return output.to_string()
    
    def _generate_includes(self) -> List[str]:
        """Generate #include directives."""
        return [
            '#include "lua_value.h"',
            '#include "lua_table.h"',
            '#include "lua_state.h"',
            '#include "closure.h"',
            '#include "error.h"',
            '#include "module_loader.h"',
            ''
        ]
    
    def _generate_forward_declarations(self) -> List[str]:
        """Generate forward declarations for all local functions."""
        # Collect functions from symbol table
        decls = []
        for scope in self.context.scope_stack:
            for name, symbol in scope.symbols.items():
                if symbol.symbol_type == 'local' and symbol.lua_type == Type('function'):
                    func_name = self.naming.mangle_function_name(
                        self.context.current_module, name
                    )
                    decls.append(f'static lua_value {func_name}(lua_State *L, ...);')
        return decls
```

### 2.2 Expression Generator (expr_generator.py)

```python
class ExpressionGenerator(ASTVisitor):
    """Generate C code for Lua expressions."""
    
    def __init__(self, context: TranslationContext):
        self.context = context
        self.naming = NamingScheme()
    
    def generate(self, expr: Node, output: CodeBuilder, 
                 target_var: Optional[str] = None) -> str:
        """Generate expression C code.
        
        Returns the variable name containing the result.
        """
        if target_var:
            result_var = target_var
        else:
            result_var = self.context.gen_temp_var()
        
        code = self.visit(expr)
        
        if target_var:
            output.add(f'{code};  // expr:{type(expr).__name__}')
        else:
            output.add(f'lua_value {result_var} = {code};  // expr:{type(expr).__name__}')
        
        return result_var
    
    def visit_Name(self, node: Name) -> str:
        """Generate variable reference."""
        # Look up in symbol table
        scope = self.context.get_current_scope()
        
        # Search upward through scopes
        for s in reversed(self.context.scope_stack):
            symbol = s.lookup(node.id)
            if symbol:
                # Check if it's an upvalue (captured in closure)
                if symbol.is_upvalue:
                    return f'l2c_get_upvalue(L, "{node.id}")'
                return node.id  # Simple variable name
        
        # Global - access via VTable
        return f'L2C_GET_GLOBAL(L, "{node.id}")'
    
    def visit_Number(self, node: Number) -> str:
        """Generate number literal."""
        if isinstance(node.n, int):
            return f'L2C_MAKE_INT({node.n})'
        else:
            return f'L2C_MAKE_FLOAT({node.n})'
    
    def visit_String(self, node: String) -> str:
        """Generate string literal using string pool."""
        idx = self.context.string_pool.intern(node.raw)
        return f'L2C_MAKE_STR(string_pool[{idx}])'
    
    def visit_Call(self, node: Call) -> str:
        """Generate function call."""
        # Check if it's require("module") - translate to direct function call
        if isinstance(node.func, Name) and node.func.id == 'require':
            if node.args and isinstance(node.args[0], String):
                module_path = node.args[0].s.decode()
                # At transpile time, resolve to module export function
                export_name = self.naming.mangle_module_name(module_path)
                return f'{export_name}(L)'
        
        # Translate function expression
        func_expr = self.generate(node.func, CodeBuilder())
        
        # Translate arguments
        args = []
        for arg in node.args:
            arg_var = self.generate(arg, CodeBuilder())
            args.append(f'&{arg_var}')
        
        args_str = ', '.join(args) if args else 'NULL, 0'
        
        temp = self.context.gen_temp_var()
        return f'l2c_call_value(L, {func_expr}, (lua_value*[]){{{args_str}}}, {len(args)})'
    
    def visit_Index(self, node: Index) -> str:
        """Generate table indexing."""
        table = self.generate(node.value, CodeBuilder())
        key = self.generate(node.idx, CodeBuilder())
        
        # Always do metamethod dispatch (no optimization for now)
        temp = self.context.gen_temp_var()
        return f'l2c_get_table_with_meta(L, {table}, {key})'
    
    def visit_Invoke(self, node: Invoke) -> str:
        """Generate method call (obj:method(args))."""
        # obj:method(args) → obj.method(obj, args)
        source = self.generate(node.source, CodeBuilder())
        func = self.generate(node.func, CodeBuilder())
        
        # Translate arguments
        args = [f'&{source}']  # self is first argument
        for arg in node.args:
            arg_var = self.generate(arg, CodeBuilder())
            args.append(f'&{arg_var}')
        
        args_str = ', '.join(args)
        
        temp = self.context.gen_temp_var()
        return f'l2c_call_value(L, {func}, (lua_value*[]){{{args_str}}}, {len(args) + 1})'
    
    def visit_AddOp(self, node: AddOp) -> str:
        """Generate addition with metamethod dispatch."""
        left = self.generate(node.left, CodeBuilder())
        right = self.generate(node.right, CodeBuilder())
        temp = self.context.gen_temp_var()
        # Use metamethod-aware addition
        return f'l2c_add_with_meta(L, {left}, {right})'
    
    def visit_AndLoOp(self, node: AndLoOp) -> str:
        """Generate logical AND with short-circuit."""
        # Lua's 'and' short-circuits: if left is falsy, return left; otherwise return right
        # Must NOT evaluate right if left is falsy
        temp = self.context.gen_temp_var()
        left = self.generate(node.left, CodeBuilder())
        
        # Generate: lua_value temp = left; l2c_is_truthy(L, temp) ? right : temp
        return f'lua_value {temp} = {left}; l2c_is_truthy(L, {temp}) ? ({self.generate(node.right, CodeBuilder())}) : {temp}'
    
    def visit_OrLoOp(self, node: OrLoOp) -> str:
        """Generate logical OR with short-circuit."""
        # Lua's 'or' short-circuits: if left is truthy, return left; otherwise return right
        # Must NOT evaluate right if left is truthy
        temp = self.context.gen_temp_var()
        left = self.generate(node.left, CodeBuilder())
        
        # Generate: lua_value temp = left; l2c_is_truthy(L, temp) ? temp : right
        return f'lua_value {temp} = {left}; l2c_is_truthy(L, {temp}) ? {temp} : ({self.generate(node.right, CodeBuilder())})'
    
    # ... all other expression types
```

### 2.3 Statement Generator (stmt_generator.py)

```python
class StatementGenerator(ASTVisitor):
    """Generate C code for Lua statements."""
    
    def __init__(self, context: TranslationContext):
        self.context = context
        self.expr_gen = ExpressionGenerator(context)
        self.naming = NamingScheme()
    
    def generate_block(self, block: Block, output: CodeBuilder, 
                       indent: int = 1) -> None:
        """Generate block of statements."""
        self.context.push_scope('block')
        
        for stmt in block.body:
            self.generate(stmt, output, indent)
        
        self.context.pop_scope()
    
    def generate(self, stmt: Node, output: CodeBuilder, 
                 indent: int = 1) -> None:
        """Generate statement C code."""
        # Add debug line directive
        if stmt.line:
            output.add(f'#line {stmt.line} "{self.context.current_module}.lua"', indent=0)
        
        result = self.visit(stmt)
        if result:
            output.add(result, indent)
    
    def visit_Assign(self, node: Assign) -> str:
        """Generate assignment statement."""
        # Generate values
        value_vars = []
        for val in node.values:
            v = self.expr_gen.generate(val, CodeBuilder())
            value_vars.append(v)
        
        # Generate assignments
        assigns = []
        for i, target in enumerate(node.targets):
            if isinstance(target, Name):
                # Skip _ underscore (discard pattern)
                if target.id == '_':
                    continue
                assigns.append(f'{target.id} = {value_vars[i]};')
            elif isinstance(target, Index):
                table = self.expr_gen.generate(target.value, CodeBuilder())
                key = self.expr_gen.generate(target.idx, CodeBuilder())
                # Use metamethod-aware set
                assigns.append(f'l2c_set_table_with_meta(L, {table}, {key}, {value_vars[i]});')
        
        return '\n    '.join(assigns) if assigns else ''
    
    def visit_LocalAssign(self, node: LocalAssign) -> str:
        """Generate local variable declaration."""
        lines = []
        
        for i, target in enumerate(node.targets):
            # Skip _ underscore (discard pattern)
            if target.id == '_':
                continue
            
            scope = self.context.get_current_scope()
            scope.add_symbol(target.id, Symbol(target.id, 'local'))
            
            if node.values and i < len(node.values):
                value = self.expr_gen.generate(node.values[i], CodeBuilder())
                lines.append(f'lua_value {target.id} = {value};')
            else:
                lines.append(f'lua_value {target.id} = L2C_MAKE_NIL();')
        
        return '\n    '.join(lines) if lines else ''
    
    def visit_Function(self, node: Function) -> str:
        """Generate function definition."""
        func_name = self.naming.mangle_function_name(
            self.context.current_module,
            self._get_func_name(node.name)
        )
        
        # Collect parameters
        params = []
        for arg in node.args:
            if isinstance(arg, Name):
                params.append(arg.id)
            elif isinstance(arg, Varargs):
                params.append('...')  # Use varargs
        
        # Generate function signature
        param_decls = ', '.join(f'lua_value {p}' for p in params)
        lines = [f'static lua_value {func_name}(lua_State *L, {param_decls})']
        lines.append('{')
        
        # Parameter scope
        self.context.push_scope('function')
        for p in params:
            self.context.get_current_scope().add_symbol(p, Symbol(p, 'param'))
        
        # Function body
        body = CodeBuilder()
        self.generate_block(node.body, body)
        lines.extend(body.lines)
        
        # Default return (nil)
        lines.append('    return L2C_MAKE_NIL();')
        lines.append('}')
        
        self.context.pop_scope()
        return '\n'.join(lines)
    
    def visit_LocalFunction(self, node: LocalFunction) -> str:
        """Generate local function definition."""
        func_name = node.name.id
        scope = self.context.get_current_scope()
        scope.add_symbol(func_name, Symbol(func_name, 'local', Type('function')))
        
        # Generate static function
        return self._generate_function_impl(func_name, node.args, node.body, is_static=True)
    
    def visit_AnonymousFunction(self, node: AnonymousFunction) -> str:
        """Generate anonymous function (closure)."""
        # Create closure
        func_name = self.context.gen_temp_var('closure')
        
        # Identify upvalues (variables from outer scopes)
        upvalues = self._identify_upvalues(node)
        
        # Generate closure
        lines = [
            f'struct closure *{func_name} = l2c_create_closure(',
            f'    _l2c__{self.context.current_module}_anon_{self.context.temp_counter},',
            f'    {len(upvalues)}',
            f');'
        ]
        
        # Capture upvalues
        for i, uv in enumerate(upvalues):
            lines.append(f'{func_name}->upvalues[{i}] = &{uv};')
        
        # Generate function implementation
        self._generate_anon_function_impl(node, func_name, upvalues)
        
        return '\n'.join(lines)
    
    def visit_If(self, node: If) -> str:
        """Generate if statement."""
        lines = []
        
        # Condition
        cond_var = self.expr_gen.generate(node.test, CodeBuilder())
        test = f'l2c_is_truthy(L, {cond_var})'
        
        # If branch
        lines.append(f'if ({test}) {{')
        if_body = CodeBuilder()
        self.generate_block(node.body, if_body)
        lines.extend(if_body.lines)
        
        # Else/elseif branches
        if node.orelse:
            if isinstance(node.orelse, list) and node.orelse:
                # Single else block
                lines.append('} else {')
                else_body = CodeBuilder()
                for stmt in node.orelse:
                    self.generate(stmt, else_body)
                lines.extend(else_body.lines)
                lines.append('}')
            elif isinstance(node.orelse, ElseIf):
                # elseif chain
                lines.append('} else {')
                lines.append(self.visit_ElseIf(node.orelse))
                lines.append('}')
        
        return '\n'.join(lines)
    
    def visit_While(self, node: While) -> str:
        """Generate while loop."""
        self.context.get_current_scope().is_loop = True
        
        cond_var = self.expr_gen.generate(node.test, CodeBuilder())
        test = f'l2c_is_truthy(L, {cond_var})'
        
        lines = [
            f'while ({test}) {{',
        ]
        
        body = CodeBuilder()
        self.generate_block(node.body, body)
        lines.extend(body.lines)
        
        lines.append('}')
        
        return '\n'.join(lines)
    
    def visit_Forin(self, node: Forin) -> str:
        """Generate for-in loop (iterators)."""
        self.context.get_current_scope().is_loop = True
        
        # Generate iterator expressions
        iter_vars = []
        for expr in node.iter:
            v = self.expr_gen.generate(expr, CodeBuilder())
            iter_vars.append(v)
        
        # Loop variables
        loop_vars = [t.id for t in node.targets]
        
        # Setup iterator state
        iterator_var = self.context.gen_temp_var()
        state_var = self.context.gen_temp_var()
        control_var = self.context.gen_temp_var()
        
        lines = [
            f'lua_value {iterator_var} = {iter_vars[0]};',
            f'lua_value {state_var} = {iter_vars[1] if len(iter_vars) > 1 else "L2C_MAKE_NIL()"};',
            f'lua_value {control_var} = L2C_MAKE_NIL();',
            '',
            f'while (1) {{',
            f'    lua_value _result = l2c_next(L, {iterator_var}, {state_var}, {control_var});',
            f'    if (l2c_is_nil(L, _result)) break;',
            f'',
        ]
        
        # Assign loop variables
        for i, var in enumerate(loop_vars):
            if i == 0:
                lines.append(f'    lua_value {var} = {control_var};')
            else:
                lines.append(f'    lua_value {var} = _result;')
        
        lines.append('')
        
        # Loop body
        body = CodeBuilder()
        self.generate_block(node.body, body)
        lines.extend(['    ' + line for line in body.lines])
        
        lines.append('}')
        
        return '\n'.join(lines)
    
    def visit_Return(self, node: Return) -> str:
        """Generate return statement."""
        if not node.values:
            return 'return L2C_MAKE_NIL();'
        
        if len(node.values) == 1:
            val = self.expr_gen.generate(node.values[0], CodeBuilder())
            return f'return {val};'
        
        # Multiple return values
        lines = []
        temp_vals = []
        for val in node.values:
            v = self.expr_gen.generate(val, CodeBuilder())
            temp_vals.append(v)
        
        # Pack into table
        result_var = self.context.gen_temp_var()
        args = ', '.join(f'&{v}' for v in temp_vals)
        lines.append(f'lua_value {result_var} = l2c_pack_values(L, (lua_value*[]){{{args}}}, {len(temp_vals)});')
        lines.append(f'return {result_var};')
        
        return '\n'.join(lines)
    
    # ... other statement types
```

### 2.4 Iterator Protocol

The `visit_Forin` method in StatementGenerator handles generic iterators. Here are the specific details for pairs/ipairs:

**Lua Iterator Pattern**:
- `for k, v in pairs(t)` → iterate all key-value pairs
- `for i, v in ipairs(t)` → iterate array-style tables (1, 2, 3, ...)
- `for k, v in t, init` → custom iterators via `next(t, k)`

**Code Generation**:
```python
    def visit_Forin(self, node: Forin) -> str:
        """Generate for-in loop (iterators)."""
        self.context.get_current_scope().is_loop = True
        
        # Generate iterator expressions
        iter_vars = []
        for expr in node.iter:
            v = self.expr_gen.generate(expr, CodeBuilder())
            iter_vars.append(v)
        
        # Loop variables
        loop_vars = [t.id for t in node.targets]
        
        # Setup iterator state
        iterator_var = self.context.gen_temp_var()
        state_var = self.context.gen_temp_var()
        control_var = self.context.gen_temp_var()
        
        lines = [
            f'lua_value {iterator_var} = {iter_vars[0]};',
            f'lua_value {state_var} = {iter_vars[1] if len(iter_vars) > 1 else "L2C_MAKE_NIL()"};',
            f'lua_value {control_var} = L2C_MAKE_NIL();',
            '',
            f'while (1) {{',
            f'    lua_value _result = l2c_next(L, {iterator_var}, {state_var}, {control_var});',
            f'    if (l2c_is_nil(L, _result)) break;',
            f'',
        ]
        
        # Assign loop variables (skip _ underscore)
        for i, var in enumerate(loop_vars):
            if var == '_':
                continue
            if i == 0:
                lines.append(f'    lua_value {var} = {control_var};')
            else:
                lines.append(f'    lua_value {var} = _result;')
        
        lines.append('')
        
        # Loop body
        body = CodeBuilder()
        self.generate_block(node.body, body)
        lines.extend(['    ' + line for line in body.lines])
        
        lines.append('}')
        
        return '\n'.join(lines)
```

**Runtime Functions Required** (add to lua_value.h/c):
```c
/* Iterator protocol - called by generated for loops */
lua_value l2c_next(lua_state *L, lua_value table, lua_value prev_key);
```

**Pairs/IPairs Implementation**:
- `pairs(t)` → equivalent to `next, t, nil`
- `ipairs(t)` → returns iterator function (optimized for integer keys)
- `next(t, k)` → returns (next_key, value) or nil

### 2.5 OOP Pattern Support

The nonred codebase uses a custom OOP system based on metatables. The transpiler must handle:

**OOP Pattern in nonred**:
- `Object:extend()` → Creates new class with inheritance
- `setmetatable(cls, self)` → Sets up prototype chain
- `getmetatable(obj)` → Type checking pattern
- `__call` metamethod → Constructor: `ClassName()`
- `__index` metamethod → Method lookup: `obj:method()`

**Code Generation**:
```python
    def visit_Invoke(self, node: Invoke) -> str:
        """Generate method call (obj:method(args))."""
        # obj:method(args) → obj.method(obj, args)
        source = self.generate(node.source, CodeBuilder())
        
        # Access method via __index metamethod
        method_expr = f'l2c_get_table_with_meta(L, {source}, L2C_MAKE_STR("{node.func.id}"))'
        
        # Translate arguments (self is first)
        args = [f'&{source}']
        for arg in node.args:
            arg_var = self.generate(arg, CodeBuilder())
            args.append(f'&{arg_var}')
        
        args_str = ', '.join(args)
        
        return f'l2c_call_value(L, {method_expr}, (lua_value*[]){{{args_str}}}, {len(args)})'
    
    def visit_Call(self, node: Call) -> str:
        """Generate function call - handle setmetatable/getmetatable."""
        # setmetatable(table, metatable)
        if isinstance(node.func, Name) and node.func.id == 'setmetatable':
            table = self.generate(node.args[0], CodeBuilder())
            meta = self.generate(node.args[1], CodeBuilder())
            return f'l2c_setmetatable(L, {table}, {meta})'
        
        # getmetatable(table)
        if isinstance(node.func, Name) and node.func.id == 'getmetatable':
            table = self.generate(node.args[0], CodeBuilder())
            return f'l2c_getmetatable(L, {table})'
        
        # ... rest of existing Call handling (require, etc.)
```

**Example Transpilation**:

```lua
-- Lua code
Game = Object:extend()
function Game:init()
    self.score = 0
end
function Game:update(dt)
    self.score = self.score + dt
end
```

```c
// Generated C
static lua_value _l2c__game_init(lua_State *L, lua_value self) {
    l2c_set_table_with_meta(L, self, L2C_MAKE_STR("score"), L2C_MAKE_INT(0));
    return L2C_MAKE_NIL();
}

static lua_value _l2c__game_update(lua_State *L, lua_value self, lua_value dt) {
    lua_value score = l2c_get_table_with_meta(L, self, L2C_MAKE_STR("score"));
    lua_value new_score = l2c_add_with_meta(L, score, dt);
    l2c_set_table_with_meta(L, self, L2C_MAKE_STR("score"), new_score);
    return L2C_MAKE_NIL();
}
```

**Runtime Functions Required** (add to lua_table.h/c):
```c
/* Metatable operations - OOP support */
lua_value l2c_setmetatable(lua_state *L, lua_value obj, lua_value mt);
lua_value l2c_getmetatable(lua_state *L, lua_value obj);
```

### 2.6 Package Configuration Handling

```python
class PackageConfig(ASTVisitor):
    """Track package.path and package.cpath modifications."""
    
    def __init__(self):
        self.path_variations: List[Tuple[str, int]] = []  # (new_path, source_line)
        self.cpath_variations: List[Tuple[str, int]] = []
    
    def track_assignment(self, node: Assign):
        """Track package.path or package.cpath assignments."""
        for target in node.targets:
            if isinstance(target, Name):
                if target.id == 'package':
                    # This is package.X = ...
                    # Need to walk down to find .path or .cpath
                    pass
```

---

## Phase 3: Runtime Library

### 3.1 Value Type (lua_value.h)

```c
#ifndef LUA_VALUE_H
#define LUA_VALUE_H

#include <stdint.h>
#include <stdbool.h>

/* Lua 5.4 value type representation - tag union */
typedef enum {
    L2C_TNIL,
    L2C_TBOOLEAN,
    L2C_TNUMBER,
    L2C_TSTRING,
    L2C_TTABLE,
    L2C_TFUNCTION,
    L2C_TUSERDATA,
    L2C_TTHREAD,
} l2c_type_t;

typedef struct lua_value lua_value;

struct lua_value {
    l2c_type_t type;
    union {
        bool boolean;
        double number;
        const char *string;
        struct lua_table *table;
        struct closure *closure;
        lua_value (*c_function)(struct lua_state *, lua_value *, int);
        void *userdata;
    } v;
};

/* Type constructors */
static inline lua_value L2C_MAKE_NIL(void) {
    return (lua_value){L2C_TNIL, .v = {0}};
}

static inline lua_value L2C_MAKE_BOOL(bool b) {
    return (lua_value){L2C_TBOOLEAN, .v.boolean = b};
}

static inline lua_value L2C_MAKE_INT(int i) {
    return (lua_value){L2C_TNUMBER, .v.number = (double)i};
}

static inline lua_value L2C_MAKE_FLOAT(double f) {
    return (lua_value){L2C_TNUMBER, .v.number = f};
}

static inline lua_value L2C_MAKE_STR(const char *s) {
    return (lua_value){L2C_TSTRING, .v.string = s};
}

/* Type predicates */
static inline bool l2c_is_nil(lua_value v) { return v.type == L2C_TNIL; }
static inline bool l2c_is_boolean(lua_value v) { return v.type == L2C_TBOOLEAN; }
static inline bool l2c_is_number(lua_value v) { return v.type == L2C_TNUMBER; }
static inline bool l2c_is_string(lua_value v) { return v.type == L2C_TSTRING; }
static inline bool l2c_is_table(lua_value v) { return v.type == L2C_TTABLE; }
static inline bool l2c_is_function(lua_value v) { return v.type == L2C_TFUNCTION; }

/* Truthiness test (like Lua's implicit boolean conversion) */
bool l2c_is_truthy(struct lua_state *L, lua_value v);

/* Value operations with metamethod dispatch */
lua_value l2c_add_with_meta(struct lua_state *L, lua_value a, lua_value b);
lua_value l2c_sub_with_meta(struct lua_state *L, lua_value a, lua_value b);
lua_value l2c_mul_with_meta(struct lua_state *L, lua_value a, lua_value b);
lua_value l2c_div_with_meta(struct lua_state *L, lua_value a, lua_value b);
lua_value l2c_concat(struct lua_state *L, lua_value a, lua_value b);

/* Comparison with metamethod dispatch */
bool l2c_eq(struct lua_state *L, lua_value a, lua_value b);
bool l2c_lt(struct lua_state *L, lua_value a, lua_value b);
bool l2c_le(struct lua_state *L, lua_value a, lua_value b);

/* Length operator with metamethod dispatch */
lua_value l2c_len(struct lua_state *L, lua_value v);

#endif
```

### 3.2 VTable-Based State (lua_state.h)

```c
#ifndef LUA_STATE_H
#define LUA_STATE_H

#include "lua_value.h"
#include <setjmp.h>

/* Forward declarations */
typedef struct lua_state lua_state;
typedef struct lua_table lua_table;

/* VTable for custom luaState implementation */
struct lua_state_vtable {
    /* Table operations */
    lua_table *(*new_table)(lua_state *L);
    void (*free_table)(lua_state *L, lua_table *t);
    lua_value (*get_table)(lua_state *L, lua_value table, lua_value key);
    void (*set_table)(lua_state *L, lua_value table, lua_value key, lua_value value);
    
    /* Global operations */
    lua_value (*get_global)(lua_state *L, const char *name);
    void (*set_global)(lua_state *L, const char *name, lua_value value);
    
    /* Function operations */
    lua_value (*call)(lua_state *L, lua_value func, lua_value *args, int nargs);
    
    /* Memory management */
    void *(*alloc)(lua_state *L, void *ptr, size_t osize, size_t nsize);
    
    /* Error handling */
    void (*error)(lua_state *L, const char *msg);
    
    /* User-provided hooks */
    lua_value (*get_registry)(lua_state *L, const char *key);
    void (*set_registry)(lua_state *L, const char *key, lua_value value);
};

/* Main luaState structure */
struct lua_state {
    const struct lua_state_vtable *vt;
    void *user_data;  /* User-provided context */
    
    /* Built-in globals */
    lua_value globals;
    
    /* Registry for C API extensions */
    lua_table *registry;
    
    /* Error handling */
    jmp_buf error_jump;
    bool in_error;
    const char *error_message;
    
    /* Module cache */
    lua_table *module_cache;
    
    /* GC state */
    int gc_threshold;
    int gc_counter;
    
    /* Package configuration (for debugging) */
    const char *package_path;
    const char *package_cpath;
};

/* State creation/destruction */
lua_state *lua_state_new(const struct lua_state_vtable *vt, void *user_data);
void lua_state_close(lua_state *L);

/* Helper macros using VTable */
#define L2C_NEW_TABLE(L) ((L)->vt->new_table(L))
#define L2C_GET_TABLE(L, t, k) ((L)->vt->get_table(L, t, k))
#define L2C_SET_TABLE(L, t, k, v) ((L)->vt->set_table(L, t, k, v))
#define L2C_GET_GLOBAL(L, n) ((L)->vt->get_global(L, n))
#define L2C_SET_GLOBAL(L, n, v) ((L)->vt->set_global(L, n, v))
#define L2C_CALL(L, f, a, n) ((L)->vt->call(L, f, a, n))

/* Default VTable implementation */
extern const struct lua_state_vtable l2c_default_vtable;

#endif
```

**Note**: External libraries (love, math, string, io, os, debug, etc.) are **NOT** implemented in the runtime. They are provided by the luaState implementer through the VTable hooks. The transpiler generates code that calls these libraries via the VTable interface.

### 3.3 Closure Support (closure.h) - Non-Generated Header

```c
#ifndef CLOSURE_H
#define CLOSURE_H

#include "lua_value.h"

/* Closure structure for capturing upvalues */
struct closure {
    lua_value (*func)(struct lua_state *L, lua_value *args, int nargs, lua_value *upvalues);
    int num_upvalues;
    lua_value *upvalues[];
};

/* Create a new closure */
struct closure *l2c_create_closure(
    lua_value (*func)(struct lua_state *, lua_value *, int, lua_value *),
    int num_upvalues
);

/* Free a closure */
void l2c_free_closure(struct lua_state *L, struct closure *cl);

/* Call a closure */
lua_value l2c_call_closure(
    struct lua_state *L,
    struct closure *cl,
    lua_value *args,
    int nargs
);

/* Upvalue access */
lua_value l2c_get_upvalue(struct lua_state *L, const char *name);
void l2c_set_upvalue(struct lua_state *L, const char *name, lua_value value);

#endif
```

This header is **NOT** dynamically generated - it's part of the runtime library and can be tuned/optimized by the implementer.

### 3.4 Table Implementation (lua_table.h)

```c
#ifndef LUA_TABLE_H
#define LUA_TABLE_H

#include "lua_value.h"
#include <stdint.h>

/* Hash table for Lua tables */
struct lua_table {
    lua_value *array_part;  /* Array part for integer keys 1..n */
    size_t array_size;
    
    struct hash_entry *hash_part;  /* Hash part for other keys */
    size_t hash_size;
    size_t hash_used;
    
    struct lua_table *metatable;  /* Metatable for __index, __newindex, etc. */
    int refcount;
};

struct hash_entry {
    lua_value key;
    lua_value value;
    struct hash_entry *next;  /* Chaining for collisions */
};

/* Table operations */
lua_table *lua_table_new(lua_state *L, size_t array_hint, size_t hash_hint);
void lua_table_free(lua_state *L, lua_table *t);
lua_value lua_table_get(lua_state *L, lua_table *t, lua_value key);
void lua_table_set(lua_state *L, lua_table *t, lua_value key, lua_value value);
int lua_table_len(lua_table *t);

/* Metatable operations - always check for metamethods */
lua_value lua_table_get_with_meta(lua_state *L, lua_table *t, lua_value key);
void lua_table_set_with_meta(lua_state *L, lua_table *t, lua_value key, lua_value value);

/* Metamethod dispatch - flexible for future optimization */
lua_value l2c_get_metamethod(lua_table *t, const char *name);

#endif
```

**Note**: We **DO NOT** optimize metamethod dispatch away based on compile-time knowledge. The code always checks for metamethods at runtime. This makes the code simpler and more flexible. Future optimizations can be added without breaking the architecture.

### 3.5 Error Handling (error.h)

```c
#ifndef ERROR_H
#define ERROR_H

#include <setjmp.h>
#include "lua_state.h"

/* Error handling using longjmp/setjmp (Lua-compatible) */
void l2c_error(lua_state *L, const char *fmt, ...);
void l2c_error_raw(lua_state *L, const char *msg);

/* Protected call mechanism */
typedef int (*l2c_CFunction)(lua_state *L);

lua_value l2c_pcall(lua_state *L, lua_value func, lua_value *args, int nargs);

/* Error handling macros */
#define L2C_TRY(L) if (setjmp((L)->error_jump) == 0)
#define L2C_THROW(L) longjmp((L)->error_jump, 1)
#define L2C_CATCH(L) else

/* Traceback support */
const char *l2c_get_traceback(lua_state *L);

#endif
```

### 3.6 Module Loader (module_loader.h)

```c
#ifndef MODULE_LOADER_H
#define MODULE_LOADER_H

#include "lua_state.h"

/* Module registry - track loaded modules */
/* Note: require() calls are resolved at transpile time to direct function calls */
/* This is for debugging and runtime module registration */

void l2c_register_module(lua_state *L, const char *name, 
                         lua_value (*module_func)(lua_state *));
lua_value l2c_get_module(lua_state *L, const char *name);

/* Package configuration for debugging */
void l2c_set_package_path(lua_state *L, const char *path);
void l2c_set_package_cpath(lua_state *L, const char *path);

#endif
```

**Note**: The module loader does **NOT** implement runtime module resolution. All `require()` calls are resolved during transpilation and converted to direct C function calls (e.g., `_l2c__engine__object_export(L)`). This registry is for debugging and registration purposes only.

### 3.7 Runtime Library Extensions

#### Metatable Operations (lua_table.h/c)

```c
/* Metatable operations - OOP support */
lua_value l2c_setmetatable(lua_state *L, lua_value obj, lua_value mt);
lua_value l2c_getmetatable(lua_state *L, lua_value obj);

/* Implementation in lua_table.c */
lua_value l2c_setmetatable(lua_state *L, lua_value obj, lua_value mt) {
    if (obj.type == L2C_TTABLE && obj.v.table) {
        obj.v.table->metatable = mt.v.table;
    }
    return obj;
}

lua_value l2c_getmetatable(lua_state *L, lua_value obj) {
    if (obj.type == L2C_TTABLE && obj.v.table) {
        return L2C_MAKE_TABLE(obj.v.table->metatable);
    }
    return L2C_MAKE_NIL();
}
```

#### Iterator Functions (lua_value.h/c)

```c
/* Iterator protocol */
lua_value l2c_next(lua_state *L, lua_value table, lua_value prev_key);

/* Implementation - handles pairs/ipairs via next() */
lua_value l2c_next(lua_state *L, lua_value table, lua_value prev_key) {
    /* Use lua_table_next to get next key-value pair */
    lua_value key, value;
    bool has_next = lua_table_next(L, table, prev_key, &key, &value);
    if (!has_next) {
        return L2C_MAKE_NIL();
    }
    /* Return value (key is in prev_key parameter) */
    return value;
}
```

#### Garbage Collection (lua_value.h/c)

```c
/* Garbage collection functions */
lua_value l2c_collectgarbage(lua_state *L, lua_value opt, lua_value arg);

/* Implementation */
lua_value l2c_collectgarbage(lua_state *L, lua_value opt, lua_value arg) {
    const char *option = opt.v.string;
    
    if (strcmp(option, "collect") == 0) {
        l2c_gc_collect(L);
    } else if (strcmp(option, "stop") == 0) {
        l2c_gc_stop(L);
    } else if (strcmp(option, "restart") == 0) {
        l2c_gc_restart(L);
    } else if (strcmp(option, "count") == 0) {
        double kb = l2c_gc_count(L);
        return L2C_MAKE_FLOAT(kb);
    } else if (strcmp(option, "step") == 0) {
        int steps = arg.v.number;
        bool done = l2c_gc_step(L, steps);
        return L2C_MAKE_BOOL(done);
    }
    
    return L2C_MAKE_NIL();
}
```

#### Type Checking (lua_value.h/c)

```c
/* Type checking - returns string type name */
lua_value l2c_type(lua_state *L, lua_value v);

/* Implementation */
lua_value l2c_type(lua_state *L, lua_value v) {
    switch (v.type) {
        case L2C_TNIL: return L2C_MAKE_STR("nil");
        case L2C_TBOOLEAN: return L2C_MAKE_STR("boolean");
        case L2C_TNUMBER: return L2C_MAKE_STR("number");
        case L2C_TSTRING: return L2C_MAKE_STR("string");
        case L2C_TTABLE: return L2C_MAKE_STR("table");
        case L2C_TFUNCTION: return L2C_MAKE_STR("function");
        case L2C_TUSERDATA: return L2C_MAKE_STR("userdata");
        case L2C_TTHREAD: return L2C_MAKE_STR("thread");
        default: return L2C_MAKE_STR("unknown");
    }
}
```

#### Assert (error.h/c)

```c
/* Assert function */
lua_value l2c_assert(lua_state *L, lua_value condition, lua_value message);

/* Implementation */
lua_value l2c_assert(lua_state *L, lua_value condition, lua_value message) {
    if (!l2c_is_truthy(L, condition)) {
        const char *msg = message.type == L2C_TSTRING ? message.v.string : "assertion failed!";
        l2c_error(L, "%s", msg);
    }
    return condition;
}
```

#### Code Loading (lua_value.h/c - Optional)

```c
/* Load function - minimal support */
lua_value l2c_load(lua_state *L, lua_value chunk, lua_value chunkname);

/* Implementation - returns nil or function */
lua_value l2c_load(lua_state *L, lua_value chunk, lua_value chunkname) {
    /* Minimal implementation: parse string, return closure */
    /* Full implementation requires bytecode interpreter or JIT */
    /* For now, return nil (not supported) */
    return L2C_MAKE_NIL();
}
```

#### Coroutine Support (lua_value.h/c - Minimal)

```c
/* Minimal coroutine support */
lua_value l2c_coroutine_wrap(lua_state *L, lua_value func);
lua_value l2c_coroutine_yield(lua_state *L, lua_value *args, int nargs);

/* Implementation */
lua_value l2c_coroutine_wrap(lua_state *L, lua_value func) {
    /* Create wrapper closure that resumes coroutine */
    /* Returns wrapped coroutine */
    struct closure *wrapped = l2c_create_closure(l2c_coroutine_wrapper, 1);
    wrapped->upvalues[0] = func;
    return L2C_MAKE_CLOSURE(wrapped);
}
```

### 3.8 Thread Channel Operations (Optional)

Thread channels are used in nonred for inter-thread communication (game.lua, sound_manager.lua, save_manager.lua, http_manager.lua). These can be implemented via VTable or as standalone runtime functions.

**Channel Operations**:
```c
/* Channel operations */
lua_value l2c_channel_push(lua_state *L, lua_value channel, lua_value value);
lua_value l2c_channel_pop(lua_state *L, lua_value channel);
lua_value l2c_channel_demand(lua_state *L, lua_value channel);

/* Implementation via VTable */
const lua_state_vtable default_vtable = {
    /* ... other methods ... */
    .channel_push = l2c_channel_push,
    .channel_pop = l2c_channel_pop,
    .channel_demand = l2c_channel_demand,
};
```

**Example Usage in nonred**:
```lua
-- Lua code
G.SOUND_MANAGER.channel:push(G.ARGS.play_sound)
local request = CHANNEL:demand()
```

**Note**: Channel operations are optional and can be provided by the luaState implementer via VTable.

---

## Phase 4: Module System

### 4.1 Dependency Graph (dependency_graph.py)

```python
class ModuleDependencyGraph:
    """Build and analyze module dependencies from require() calls."""
    
    def __init__(self):
        self.graph: Dict[str, Set[str]] = {}  # module -> dependencies
        self.reverse_graph: Dict[str, Set[str]] = {}  # module -> dependents
    
    def add_module(self, name: str, dependencies: List[str]):
        """Add module with its dependencies."""
        self.graph[name] = set(dependencies)
        for dep in dependencies:
            if dep not in self.reverse_graph:
                self.reverse_graph[dep] = set()
            self.reverse_graph[dep].add(name)
    
    def get_load_order(self) -> List[str]:
        """Get topological order for loading modules."""
        # Kahn's algorithm for topological sort
        in_degree = {m: len(deps) for m, deps in self.graph.items()}
        queue = [m for m, deg in in_degree.items() if deg == 0]
        result = []
        
        while queue:
            m = queue.pop(0)
            result.append(m)
            
            for dependent in self.reverse_graph.get(m, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(self.graph):
            raise CircularDependencyError("Circular module dependencies detected")
        
        return result
    
    def analyze_return_types(self, parser_results: Dict[str, Chunk]) -> Dict[str, Type]:
        """Analyze what each module returns."""
        return_types = {}
        
        for name, chunk in parser_results.items():
            # Find last statement that's an expression (return value of require)
            last_expr = None
            for stmt in reversed(chunk.body.body):
                if isinstance(stmt, (Call, Name, Number, String)):
                    last_expr = stmt
                    break
            
            if last_expr:
                # Infer type
                inferencer = TypeInferencer(context)
                return_types[name] = inferencer.infer(last_expr)
            else:
                # Module returns implicit nil
                return_types[name] = Type('nil')
        
        return return_types
```

### 4.2 Module Resolver (module_resolver.py)

```python
class ModuleResolver:
    """Resolve module paths and track return types."""
    
    def __init__(self, base_dir: str, package_config: PackageConfig):
        self.base_dir = Path(base_dir)
        self.package_config = package_config
        self.search_paths = ['.']  # Updated by package.path modifications
        self.loaded_modules: Dict[str, ModuleInfo] = {}
    
    def resolve(self, require_path: str, source_line: int) -> Optional[Path]:
        """Resolve a require() path to a file.
        
        Args:
            require_path: The module path from require("...")
            source_line: Line number where require() was called (for debugging)
        """
        # Try different extensions
        for ext in ['.lua', '/init.lua']:
            for search_path in self.search_paths:
                full_path = self.base_dir / search_path / (require_path + ext)
                if full_path.exists():
                    # Record resolution for debugging
                    self.package_config.record_resolution(
                        require_path, 
                        str(full_path), 
                        source_line
                    )
                    return full_path
        
        return None

class ModuleInfo:
    """Information about a loaded module."""
    
    def __init__(self, name: str, path: Path, return_type: Type):
        self.name = name
        self.path = path
        self.return_type = return_type
        self.c_function_name: str = None  # e.g., "_l2c__engine__object_export"
```

### 4.3 Package Configuration (package_config.py)

```python
class PackageConfig:
    """Track package.path and package.cpath modifications for debugging."""
    
    def __init__(self):
        self.path_variations: List[Tuple[str, int]] = []  # (path, line_number)
        self.cpath_variations: List[Tuple[str, int]] = []
        self.resolution_log: List[Tuple[str, str, int]] = []  # (module, file, line)
    
    def update_path(self, new_path: str, line_number: int):
        """Record package.path modification."""
        self.path_variations.append((new_path, line_number))
    
    def update_cpath(self, new_path: str, line_number: int):
        """Record package.cpath modification."""
        self.cpath_variations.append((new_path, line_number))
    
    def record_resolution(self, module: str, file: str, line: int):
        """Record module resolution for debugging."""
        self.resolution_log.append((module, file, line))
    
    def generate_debug_info(self) -> str:
        """Generate C comments with package configuration info."""
        lines = ['/* Package configuration for debugging */']
        lines.append(f'/* package.path variations: */')
        for path, line in self.path_variations:
            lines.append(f'/*   Line {line}: {path} */')
        lines.append(f'/* package.cpath variations: */')
        for path, line in self.cpath_variations:
            lines.append(f'/*   Line {line}: {path} */')
        lines.append(f'/* Module resolutions: */')
        for module, file, line in self.resolution_log:
            lines.append(f'/*   Line {line}: require("{module}") → {file} */')
        return '\n'.join(lines)
```

### 4.4 Cyclic Detection (cyclic_detector.py)

```python
class CycleDetector:
    """Detect circular require() calls."""
    
    def __init__(self):
        self.call_stack: List[str] = []
        self.visited: Set[str] = set()
    
    def check(self, module: str, dependencies: List[str]) -> bool:
        """Check if adding this module creates a cycle."""
        if module in self.call_stack:
            return True  # Cycle detected!
        
        if module in self.visited:
            return False  # Already processed, no cycle
        
        self.call_stack.append(module)
        
        for dep in dependencies:
            if self.check(dep, []):
                return True
        
        self.call_stack.pop()
        self.visited.add(module)
        return False
```

---

## Phase 5: Transpiler CLI

### 5.1 Main Entry Point (cli/main.py)

```python
#!/usr/bin/env python3

import argparse
from pathlib import Path

from luaparser import ast
from core.context import TranslationContext
from core.config import CompilerConfig
from generators.c_emitter import CEmitter
from module_system.dependency_graph import ModuleDependencyGraph
from module_system.module_resolver import ModuleResolver
from module_system.package_config import PackageConfig
from cli.batch_compiler import BatchCompiler

def main():
    parser = argparse.ArgumentParser(description='Lua to C Transpiler')
    parser.add_argument('input', help='Input Lua file or directory')
    parser.add_argument('-o', '--output', default='output', help='Output directory')
    parser.add_argument('--runtime', help='Runtime C files output directory')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--verbose', '-v', action='count', default=0)
    
    args = parser.parse_args()
    
    config = CompilerConfig(
        debug=args.debug,
        verbose=args.verbose,
        generate_line_directives=True,
        static_strings=True,
        one_file_per_module=True
    )
    
    input_path = Path(args.input)
    if input_path.is_file():
        # Single file compilation
        compile_single_file(input_path, args.output, config)
    else:
        # Directory compilation (batch)
        compiler = BatchCompiler(config, input_path, Path(args.output))
        compiler.compile_all()
    
    # Copy runtime files
    if args.runtime:
        copy_runtime_files(Path(args.runtime))

def compile_single_file(input_path: Path, output_dir: Path, config: CompilerConfig):
    """Compile a single Lua file to C."""
    # Parse Lua
    with open(input_path) as f:
        lua_code = f.read()
    
    tree = ast.parse(lua_code)
    
    # Generate C
    package_config = PackageConfig()
    context = TranslationContext(config)
    context.package_config = package_config
    emitter = CEmitter(context)
    
    c_code = emitter.generate_module(tree, input_path.stem)
    
    # Write output
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f'{input_path.stem}.c'
    
    with open(output_file, 'w') as f:
        f.write(c_code)
    
    print(f'Generated: {output_file}')

def copy_runtime_files(output_dir: Path):
    """Copy runtime C files to output directory."""
    runtime_dir = Path(__file__).parent.parent / 'runtime'
    
    for file in runtime_dir.glob('*.c'):
        import shutil
        shutil.copy(file, output_dir / file.name)
    
    for file in runtime_dir.glob('*.h'):
        import shutil
        shutil.copy(file, output_dir / file.name)

if __name__ == '__main__':
    main()
```

### 5.2 Configuration (cli/config.py)

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class CompilerConfig:
    """Compiler configuration."""
    
    # Code generation options
    debug: bool = False
    verbose: int = 0
    generate_line_directives: bool = True
    static_strings: bool = True
    one_file_per_module: bool = True
    
    # Optimization
    optimize_level: int = 0
    inline_threshold: int = 10
    
    # Target platform
    target_c_standard: str = 'C11'
    
    # Output format
    include_runtime: bool = True
    generate_makefile: bool = False
```

### 5.3 Batch Compiler (cli/batch_compiler.py)

```python
from pathlib import Path
from typing import Dict

from luaparser import ast
from core.context import TranslationContext
from core.config import CompilerConfig
from generators.c_emitter import CEmitter
from module_system.dependency_graph import ModuleDependencyGraph
from module_system.module_resolver import ModuleResolver
from module_system.package_config import PackageConfig

class BatchCompiler:
    """Compile all Lua modules in a directory."""
    
    def __init__(self, config: CompilerConfig, base_dir: Path, output_dir: Path):
        self.config = config
        self.base_dir = base_dir
        self.output_dir = output_dir
        self.package_config = PackageConfig()
        self.resolver = ModuleResolver(base_dir, self.package_config)
    
    def compile_all(self):
        """Compile all Lua modules in correct order."""
        # Find all Lua files
        lua_files = list(self.base_dir.rglob('*.lua'))
        
        # Parse all files
        parsed: Dict[str, ast.Chunk] = {}
        for file in lua_files:
            module_name = self._get_module_name(file)
            with open(file) as f:
                parsed[module_name] = ast.parse(f.read())
        
        # Build dependency graph
        dep_graph = ModuleDependencyGraph()
        for name, chunk in parsed.items():
            deps = self._extract_requires(chunk)
            dep_graph.add_module(name, deps)
        
        # Get load order
        load_order = dep_graph.get_load_order()
        
        # Compile in order
        for module_name in load_order:
            context = TranslationContext(self.config)
            context.package_config = self.package_config
            emitter = CEmitter(context)
            
            c_code = emitter.generate_module(parsed[module_name], module_name)
            
            # Write to file
            output_file = self.output_dir / f'{module_name}.c'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                f.write(c_code)
            
            print(f'Compiled: {module_name} → {output_file}')
    
    def _get_module_name(self, file: Path) -> str:
        """Get module name from file path."""
        rel_path = file.relative_to(self.base_dir)
        if rel_path.name == 'init.lua':
            rel_path = rel_path.parent
        return str(rel_path.with_suffix(''))
    
    def _extract_requires(self, chunk: ast.Chunk) -> List[str]:
        """Extract all require() calls from chunk."""
        requires = []
        
        for node in ast.walk(chunk):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'require':
                    if node.args and isinstance(node.args[0], ast.String):
                        requires.append(node.args[0].s.decode())
        
        return requires
```

---

## Generated C Code Structure

### Example Output for simple.lua

```lua
-- simple.lua
local function add(a, b)
    return a + b
end

local result = add(10, 20)
print(result)
```

```c
/* Generated by lua2c from simple.lua */

#include "lua_value.h"
#include "lua_table.h"
#include "lua_state.h"
#include "closure.h"
#include "error.h"
#include "module_loader.h"

/* String pool */
static const char *string_pool[] = {
    NULL
};

/* Module functions */
static lua_value _l2c__simple_add(lua_State *L, lua_value a, lua_value b);

/* Module entry point */
lua_value _l2c__simple_export(lua_State *L) {
#line 1 "simple.lua"
    lua_value _t0 = L2C_MAKE_NIL();
    
#line 3
    lua_value result = l2c_call_value(L, l2c_get_global(L, "add"), 
        (lua_value*[]){&L2C_MAKE_INT(10), &L2C_MAKE_INT(20)}, 2);
    
#line 5
    l2c_call_value(L, l2c_get_global(L, "print"), 
        (lua_value*[]){&result}, 1);
    
    return L2C_MAKE_NIL();
}

/* Local functions */
static lua_value _l2c__simple_add(lua_State *L, lua_value a, lua_value b) {
#line 2
    return l2c_add_with_meta(L, a, b);
}

/* Module registration */
void l2c_register_module_simple(lua_State *L) {
    l2c_register_module(L, "simple", _l2c__simple_export);
}
```

### Example for nonred/main.lua

```c
/* Generated by lua2c from nonred/main.lua */

/* ... includes ... */

/* String pool */
static const char *string_pool[] = {
    "OS X",
    "Windows",
    "OS X",
    "Windows",
    // ... many more strings
    NULL
};

/* External module declarations (from require() calls) */
lua_value _l2c__engine__object_export(lua_State *L);
lua_value _l2c__engine__string_packer_export(lua_State *L);
lua_value _l2c__engine__controller_export(lua_State *L);
lua_value _l2c__back_export(lua_State *L);
lua_value _l2c__tag_export(lua_State *L);
lua_value _l2c__engine__event_export(lua_State *L);
lua_value _l2c__engine__node_export(lua_State *L);
lua_value _l2c__engine__moveable_export(lua_State *L);
lua_value _l2c__engine__sprite_export(lua_State *L);
lua_value _l2c__engine__animatedsprite_export(lua_State *L);
lua_value _l2c__functions__misc_functions_export(lua_State *L);
lua_value _l2c__game_export(lua_State *L);
lua_value _l2c__globals_export(lua_State *L);
lua_value _l2c__engine__ui_export(lua_State *L);
lua_value _l2c__functions__UI_definitions_export(lua_State *L);
lua_value _l2c__functions__state_events_export(lua_State *L);
lua_value _l2c__functions__common_events_export(lua_State *L);
lua_value _l2c__functions__button_callbacks_export(lua_State *L);
lua_value _l2c__functions__test_functions_export(lua_State *L);
lua_value _l2c__card_export(lua_State *L);
lua_value _l2c__cardarea_export(lua_State *L);
lua_value _l2c__blind_export(lua_State *L);
lua_value _l2c__card_character_export(lua_State *L);
lua_value _l2c__engine__particles_export(lua_State *L);
lua_value _l2c__engine__text_export(lua_State *L);
lua_value _l2c__challenges_export(lua_State *L);

/* Package configuration debug info */
/*
   package.path variations:
   Line 94: ...;dir/?.so
   
   Module resolutions:
   Line 1: require("engine/object") → engine/object.lua
   Line 2: require("engine/string_packer") → engine/string_packer.lua
   ...
*/

/* Module entry point */
lua_value _l2c__nonred__main_export(lua_State *L) {
#line 1
    _l2c__engine__object_export(L);
    _l2c__engine__string_packer_export(L);
    _l2c__engine__controller_export(L);
    _l2c__back_export(L);
    _l2c__tag_export(L);
    _l2c__engine__event_export(L);
    _l2c__engine__node_export(L);
    _l2c__engine__moveable_export(L);
    _l2c__engine__sprite_export(L);
    _l2c__engine__animatedsprite_export(L);
    _l2c__functions__misc_functions_export(L);
    _l2c__game_export(L);
    _l2c__globals_export(L);
    _l2c__engine__ui_export(L);
    _l2c__functions__UI_definitions_export(L);
    _l2c__functions__state_events_export(L);
    _l2c__functions__common_events_export(L);
    _l2c__functions__button_callbacks_export(L);
    _l2c__functions__misc_functions_export(L);  # Duplicate require
    _l2c__functions__test_functions_export(L);
    _l2c__card_export(L);
    _l2c__cardarea_export(L);
    _l2c__blind_export(L);
    _l2c__card_character_export(L);
    _l2c__engine__particles_export(L);
    _l2c__engine__text_export(L);
    _l2c__challenges_export(L);
    
#line 29
    l2c_call_value(L, l2c_get_global(L, "math"), 
        (lua_value*[]){&l2c_make_str("randomseed")}, 1);
    
    // ... love.run() function implementation with closure
#line 31
    lua_value _t1 = L2C_MAKE_NIL();
    lua_value _t2 = L2C_MAKE_NIL();
    // ... implementation
    
    return L2C_MAKE_NIL();
}

/* Local functions */
static lua_value _l2c__nonred__main_love_run_anon_0(lua_State *L, lua_value *args, int nargs, lua_value *upvalues) {
    // Anonymous function from line 42
    lua_value dt = upvalues[0];
    lua_value dt_smooth = upvalues[1];
    lua_value run_time = upvalues[2];
    
    // ... loop body
    return L2C_MAKE_NIL();
}

/* ... more functions ... */
```

---

## Key Technical Decisions

### 1. Module System (Static Resolution)

**Approach**: All `require()` calls are resolved at **transpile time**, not runtime.

- `require("engine/object")` → generates direct C function call `_l2c__engine__object_export(L)`
- No runtime module resolution
- Dependency graph built during transpilation
- Topological sort ensures correct compilation order

**Return Value Handling**:
- Modules can return values (via last expression)
- C function returns `lua_value`
- Direct function call (no caching in generated code - caching is in runtime if needed)

**Dependency Management**:
- Build dependency graph from all `require()` calls
- Topological sort for load order
- Detect circular dependencies

### 2. String Handling

**Static String Pool**:
- All string literals stored in `string_pool[]` array
- Generated code uses indices: `string_pool[0]`
- No runtime allocation for literals

**Runtime Strings**:
- Dynamic strings use `const char *` in `lua_value`
- Memory managed by GC

### 3. Error Handling

**Lua-Compatible Errors**:
- Use `setjmp`/`longjmp` for recoverable errors
- `l2c_pcall` wraps function calls with error handling
- Stack unwinding via VTable

**Error Messages**:
- Include source location (line numbers)
- Traceback support via `#line` directives

### 4. VTable Architecture

**Purpose**: Enable custom luaState implementation (drop-in replacement).

**Components**:
- `lua_state_vtable`: Function pointers for all state operations
- User can provide custom VTable
- Runtime uses VTable for all operations

**External Libraries**:
- `love.*`, `math.*`, `string.*`, `io.*`, `os.*`, `debug.*`, `package.*` are **NOT** implemented in runtime
- These are provided by luaState implementer through VTable
- Generated code calls these libraries via VTable hooks

**Example Custom Implementation**:
```c
const lua_state_vtable custom_vtable = {
    .new_table = custom_new_table,
    .get_table = custom_get_table,
    .get_global = custom_get_global,  // Provides love.*, math.*, etc.
    .call = custom_call,
    // ... other methods
};
```

### 5. Type System

**Static Type Inference**:
- Track types where possible
- Number, string, boolean are statically known
- Tables and functions use dynamic types

**Dynamic Fallback**:
- `lua_value` union represents any Lua value
- Type tag checked at runtime
- Coercion functions handle type conversions

### 6. Metamethod Dispatch

**No Compile-Time Optimization**:
- Always check for metamethods at runtime
- `t[key]` → `l2c_get_table_with_meta(L, t, key)`
- `a + b` → `l2c_add_with_meta(L, a, b)`

**Rationale**:
- Simpler code generation
- More flexible for future optimizations
- Can add compile-time analysis later without breaking architecture

**Future Optimization Path**:
- Add type inference to detect when metamethods won't be called
- Generate direct table access for known "safe" cases
- This can be added as an optimization pass

### 7. Package Configuration

**Static Tracking**:
- `package.path` and `package.cpath` modifications are tracked during transpilation
- Recorded for debugging purposes
- Influences module resolution at the point they're seen

**No Runtime Effect**:
- Package paths don't affect runtime (no runtime module resolution)
- All requires are already resolved to direct function calls

**Debug Info**:
- C comments with package path variations
- Module resolution log with source line numbers

### 8. Naming Convention

**Consistent Scheme**:
- `_l2c__` prefix for all generated symbols
- `__` separates path components
- `_export` suffix for module entry points
- Function names: `_l2c__<path>_<funcname>`

**Benefits**:
- Avoids name collisions
- Easy to identify generated code
- Clear module hierarchy

### 9. OOP Pattern Support

**Custom Metatable-Based OOP**:
- The nonred codebase uses a custom OOP system (Object:extend())
- All metatable operations (setmetatable, getmetatable) are handled at runtime
- Colon syntax `obj:method()` translates to `obj.method(obj, ...)`
- No compile-time optimization of OOP patterns - flexible for future

**Rationale**:
- Lua's metatable system is dynamic and powerful
- Compile-time analysis of inheritance chains is complex
- Runtime dispatch ensures correctness with dynamic class hierarchies
- Can add static dispatch optimization in future if needed

---

## Testing Strategy

### Unit Tests

**AST Visitor Tests**:
- Verify each visitor method generates correct code
- Test edge cases (nested scopes, complex expressions)

**Type Inference Tests**:
- Verify type inference for common patterns
- Test polymorphic functions

**Naming Scheme Tests**:
- Verify mangling of various module paths
- Test edge cases (empty paths, deeply nested)

### Integration Tests

**Full Translation Tests**:
- Translate test Lua files to C
- Compile generated C code
- Execute and compare with Lua interpreter

**Module System Tests**:
- Test `require()` with return values
- Test circular dependencies
- Test multiple modules

**VTable Tests**:
- Test with default VTable
- Test with custom VTable implementation

### Test Fixtures

```
tests/
├── unit/
│   ├── test_ast_visitor.py
│   ├── test_type_inference.py
│   ├── test_string_pool.py
│   ├── test_naming.py
│   └── test_codegen.py
├── integration/
│   ├── test_simple.py
│   ├── test_modules.py
│   ├── test_loops.py
│   ├── test_functions.py
│   └── test_nonred_main.py
└── fixtures/
    ├── simple.lua
    ├── modules/
    │   ├── a.lua
    │   ├── b.lua
    │   └── c.lua
    └── complex.lua
```

---

## Implementation Phases

### Phase 1: Core (Week 1-2)
- [ ] AST visitor base class
- [ ] Translation context
- [ ] Scope management
- [ ] Symbol table
- [ ] String pool
- [ ] Naming scheme implementation

### Phase 2: Code Generation (Week 3-4)
- [ ] Expression generator (all types)
- [ ] Statement generator (all types)
- [ ] Main C emitter
- [ ] Declaration generator
- [ ] Package configuration tracking
- [ ] Short-circuit evaluation (and/or)
- [ ] Multiple assignments with _ discard
- [ ] Iterator protocol (pairs/ipairs/next)
- [ ] OOP pattern support (setmetatable/getmetatable, colon syntax)

### Phase 3: Runtime (Week 5-6)
- [ ] lua_value implementation
- [ ] lua_state with VTable
- [ ] lua_table with metamethod dispatch
- [ ] Closure support (non-generated header)
- [ ] Error handling (longjmp/setjmp)
- [ ] Module registry (debug only)
- [ ] Metatable operations (setmetatable/getmetatable)
- [ ] Garbage collection (collectgarbage)
- [ ] Type checking (type, assert)
- [ ] Code loading (load - optional)
- [ ] Iterator functions (next)
- [ ] Thread channel operations (optional)
- [ ] Coroutine support (minimal)

### Phase 4: Module System (Week 7)
- [ ] Dependency graph
- [ ] Module resolver
- [ ] Cycle detection
- [ ] Batch compilation
- [ ] Package configuration

### Phase 5: CLI & Testing (Week 8)
- [ ] Command-line interface
- [ ] Batch compiler
- [ ] Unit tests
- [ ] Integration tests

### Phase 6: Polish & Extensibility (Week 9-10)
- [ ] Debug info (#line directives, package config)
- [ ] Error messages with source location
- [ ] Performance optimization (optional)
- [ ] Documentation

---

## Analysis of nonred/main.lua

### Key Features to Support

1. **Module Loading** (lines 1-27):
   - Multiple `require()` calls
   - Modules may return tables (G, love)
   - Need to track return types
   - Transpiled to direct C function calls

2. **Global Variables**:
   - `_RELEASE_MODE` - global boolean flag
   - `G` - global table (game state)
   - Access pattern: `G.FOO`, `love.bar`
   - Provided by VTable (external libraries)

3. **Love2D Callbacks** (lines 31-386):
   - Functions assigned to `love.*` global table
   - Various signatures (no params, with params, with returns)
   - `love.*` provided by VTable

4. **Anonymous Functions** (line 42):
   - `love.run` returns a function
   - Requires closure support (capturing `run_time`, `dt`, etc.)
   - Closure implemented via `closure.h` (non-generated)

5. **Complex Control Flow**:
   - Nested conditionals
   - Loops (event polling)
   - Early returns
   - `for` loops with multiple variables (line 48)

6. **String Manipulation** (lines 216-229):
   - `string.format`, `string.sub`, `string.find`, `string.match`, `string.gmatch`
   - `string.*` provided by VTable (external library)

7. **Math Operations** (line 29, 69, 78, 190, 372):
   - `math.randomseed`, `math.min`, `math.abs`, `math.floor`
   - `math.*` provided by VTable (external library)

8. **Table Operations**:
   - `next()` (line 183)
   - `ipairs()` usage pattern (line 267)
   - Table indexing and assignment
   - Always use metamethod dispatch

9. **Error Handling** (line 196-320):
   - `love.errhand` function
   - `pcall` (line 253)
   - `debug.traceback()` (line 229)
   - Protected calls
   - `debug.*` provided by VTable

10. **Thread Operations** (lines 201-214):
    - `love.thread.newThread`
    - `love.thread.getChannel`
    - `love.thread.*` provided by VTable

11. **Steam Integration** (lines 86-112):
    - Dynamic library loading (`require 'luasteam'`)
    - Package path manipulation (lines 93-96)
    - Package configuration tracked for debugging

12. **Graphics Operations** (lines 73-84):
    - `love.graphics.isActive()`, `love.draw()`, `love.graphics.present()`
    - Canvas operations (lines 377-385)
    - `love.graphics.*` provided by VTable

### Potential Issues/Considerations

1. **Package Path Manipulation**: Line 94 modifies `package.cpath` - tracked for debugging, affects subsequent require() calls during transpilation.

2. **Nil Checks**: Many `if love.X then` checks - handled by `l2c_is_truthy()`.

3. **Short-Circuit Evaluation**: Lua's `and`/`or` - ensure C code preserves this (requires careful code generation).

4. **Multiple Assignments**: Line 48 `for name, a,b,c,d,e,f in ...` - varargs support needed.

5. **String Escaping**: The error handling code uses complex string manipulation.

6. **Float vs Int**: Lua 5.4 uses integer optimization - `l2c_make_int()` and `l2c_make_float()`.

7. **Closure Semantics**: Anonymous function needs to capture outer variables - implemented via `closure.h`.

8. **Metatables**: Not explicitly shown but likely in `G` and `love` tables - always use metamethod dispatch.

9. **Upvalues**: Functions accessing outer scope variables - marked as `is_upvalue` in symbol table.

10. **Coroutines**: Not in this file but common in Lua - may need support.

19. **OOP Pattern** (engine/object.lua, game.lua, card.lua):
    - `Object:extend()` creates new classes
    - `setmetatable(cls, self)` for inheritance
    - `__call` metamethod for `ClassName()` constructor
    - `__index` for method lookup
    - Colon syntax `obj:method()` → method(obj, ...)

20. **Coroutines** (functions/misc_functions.lua:1688):
    - `coroutine.wrap()` - creates wrapped coroutine
    - `coroutine.yield()` - yields value
    - Minimal but present in codebase

21. **Garbage Collection** (functions/misc_functions.lua:87,97,657,661,662,666):
    - `collectgarbage("count")` - get memory usage
    - `collectgarbage("step", n)` - incremental GC
    - `collectgarbage("collect")` - full GC
    - `collectgarbage("stop")` - stop GC

22. **Special Functions**:
    - `assert(condition, message)` - throw if false (UI_definitions, string_packer, profile)
    - `type(value)` - return type name (used 50+ times across codebase)
    - `load(string, chunkname)` - load code (UI_definitions:208, string_packer:50, game.lua:993)
    - `loadstring()` - load from string (globals.lua)

23. **Table Iterators** (100+ occurrences):
    - `pairs(table)` - iterate all key-value pairs
    - `ipairs(table)` - iterate array-style tables
    - `next(table, prev_key)` - manual iteration, check for empty

24. **Short-Circuit Evaluation**:
    - `and`/`or` must preserve short-circuit semantics
    - Example: `condition and params or {}` - params not evaluated if condition false

25. **Multiple Return Values**:
    - Pattern: `local _, _, r, g, b, a = hex:find('(%x%x)(%x%x)(%x%x)(%x%x)')`
    - `_` underscore used for discarding values

26. **Thread Channels** (game.lua, sound_manager.lua, save_manager.lua, http_manager.lua):
    - `channel:push(value)` - send to channel
    - `channel:pop()` - receive from channel
    - `channel:demand()` - blocking receive

27. **HEK Color Helper** (functions/misc_functions.lua:357, used extensively in globals.lua):
    - `HEX('b95b08')` converts hex string to color table
    - Returns `{r, g, b, a}` table

28. **Love2D Configuration** (conf.lua):
    - `love.conf(t)` called before `love.load()`
    - Configures window, console, etc.
    - Must be transpiled as function definition

---

## Extensibility Design

### Adding New AST Node Types

```python
# 1. Add visitor method to generators/expr_generator.py
def visit_NewNodeType(self, node: NewNodeType) -> str:
    """Generate C code for new node type."""
    # Your implementation
    pass

# 2. Add to type inference
def visit_NewNodeType(self, node: NewNodeType) -> Type:
    """Infer type for new node type."""
    pass
```

### Adding New Runtime Functions

```c
// 1. Add to lua_value.h
lua_value l2c_custom_op(lua_state *L, lua_value a, lua_value b);

// 2. Implement in lua_value.c

// 3. User can override via VTable
const lua_state_vtable custom_vtable = {
    .custom_op = my_custom_implementation,
    // ... other methods
};
```

### Adding Metamethod Optimization (Future)

```python
# Can be added as an optimization pass without breaking existing code
class MetamethodOptimizer(ASTVisitor):
    """Optimize table operations by eliminating unnecessary metamethod checks."""
    
    def visit_Index(self, node: Index) -> str:
        # Check if table is known to have no metatable
        if self._is_meta_safe(node.value):
            return f'l2c_get_table(L, {table}, {key})'  # Direct access
        else:
            return f'l2c_get_table_with_meta(L, {table}, {key})'
```

### Tuning Closure Implementation

The `closure.h` header is **NOT** generated - it's a static part of the runtime. This allows:
- Performance tuning without changing the transpiler
- Custom allocation strategies
- Alternative upvalue handling
- Platform-specific optimizations

---

## Build System Integration

### Generated C Compilation

```makefile
# Generated files
C_SOURCES = $(wildcard output/*.c)
RUNTIME_SOURCES = runtime/*.c

OBJECTS = $(C_SOURCES:.c=.o) $(RUNTIME_SOURCES:.c=.o)

# Compile transpiled code
output/%.o: output/%.c
    gcc -c -std=c11 -Iruntime -O2 $< -o $@

# Compile runtime
runtime/%.o: runtime/%.c
    gcc -c -std=c11 -O2 $< -o $@

# Link
game: $(OBJECTS)
    gcc -o game $(OBJECTS) -lm

# Transpile
transpile:
    python3 -m lua2c nonred -o output

.PHONY: transpile
```

---

## Future Enhancements

1. **Optimization Passes**:
   - Metamethod elimination where safe
   - Constant folding
   - Dead code elimination
   - Loop unrolling
   - Inline small functions

2. **Advanced Type Inference**:
   - Flow-sensitive analysis
   - Union types
   - Generic types

3. **More Runtime Features**:
   - Coroutine support
   - Full pattern matching
   - UTF-8 string operations

4. **Tooling**:
   - Language server protocol support
   - IDE integration
   - Interactive REPL

5. **Platform-Specific Optimizations**:
   - SIMD for numeric operations
   - Platform-specific intrinsics
   - Memory pool allocation

---

## Conclusion

This plan provides a comprehensive roadmap for building a maintainable, extensible Lua to C transpiler with:

- **Modular architecture** using visitor pattern
- **Static module resolution** - all requires resolved at transpile time
- **VTable-based runtime** for custom luaState implementation
- **External libraries via VTable** - love, math, string, etc. not implemented in runtime
- **Static type inference** where possible, dynamic fallback
- **Lua-compatible error handling** with setjmp/longjmp
- **Full debug information** via #line directives and package config tracking
- **One C file per module** organization
- **Static string pooling** for literals
- **Closure support** via non-generated `closure.h` header
- **Always metamethod dispatch** - no compile-time optimization (flexible for future)
- **Naming scheme**: `_l2c__dir__dir__file_export` and `_l2c__dir__dir__file_method`

The design prioritizes maintainability and extensibility, making it easy to add new features, optimize existing code, or integrate with custom runtime implementations. External libraries are cleanly separated via the VTable interface, and the code is flexible enough to add optimizations (like metamethod elimination) in the future without breaking the architecture.
