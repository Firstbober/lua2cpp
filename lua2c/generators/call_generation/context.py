"""Context for function call generation
Provides unified access to type information, function signatures,
and generation utilities.
"""
from dataclasses import dataclass
from typing import Optional, Dict, List
from luaparser import astnodes
from lua2c.core.type_system import Type, TypeKind, TableTypeInfo
from lua2c.core.context import TranslationContext
from lua2c.core.global_type_registry import GlobalTypeRegistry, FunctionSignature


@dataclass
class CallGenerationContext:
    """Context object for generating function calls
    
    Centralizes all information needed for call generation:
    - Function signatures
    - Type information
    - Conversion utilities
    """
    
    expr: astnodes.Call
    func_path: Optional[str]  # e.g., "string.format", "print"
    signature: Optional[FunctionSignature]
    arg_types: List[Type]
    arg_table_infos: Dict[int, TableTypeInfo]
    return_type: Optional[Type]
    is_local: bool
    line_number: Optional[int]
    
    def __post_init__(self):
        """Compute derived information"""
        self.num_args = len(self.expr.args)
        self.num_params = len(self.signature.param_types) if self.signature else 0
    
    def needs_variadic(self, library_tracker=None) -> bool:
        """Check if function should use variadic template
        
        Args:
            library_tracker: LibraryCallTracker for checking usage patterns
            
        Returns:
            True if variadic template should be used
        """
        if not self.signature:
            return False
        
        # Hardcoded always-variadic functions
        if getattr(self.signature, 'always_variadic', False):
            return True
        
        # Check library tracker for usage patterns
        if library_tracker and hasattr(library_tracker, 'is_variadic'):
            if library_tracker.is_variadic(self.func_path):
                return True
        
        # Check signature is_variadic flag
        return getattr(self.signature, 'is_variadic', False)
    
    def needs_vector(self) -> bool:
        """Check if function needs vector parameter
        
        Returns:
            True if function uses std::vector<luaValue> parameter
        """
        if not self.signature:
            return False
        return any("vector<luaValue>" in pt for pt in self.signature.param_types)
    
    def has_fixed_params(self) -> bool:
        """Check if function has fixed (non-variadic) parameters
        
        Returns:
            True if function has at least one fixed parameter
        """
        return self.num_params > 0
    
    def get_fixed_param_count(self) -> int:
        """Get number of fixed parameters
        
        Returns:
            Number of parameters before variadic ones
        """
        if not self.signature:
            return 0
        return len(self.signature.param_types)


class CallContextBuilder:
    """Builder for creating CallGenerationContext objects"""
    
    @staticmethod
    def build(expr: astnodes.Call, context: TranslationContext, type_inferencer=None) -> CallGenerationContext:
        """Build a CallGenerationContext from a Call node
        
        Args:
            expr: Call AST node
            context: TranslationContext
            type_inferencer: Optional TypeInference instance
            
        Returns:
            CallGenerationContext with all information populated
        """
        # Get function path
        func_path = CallContextBuilder._get_function_path(expr)
        
        # Get signature
        signature = None
        if func_path:
            signature = GlobalTypeRegistry.get_function_signature(func_path)
        
        # Check if local
        is_local = CallContextBuilder._is_local_call(expr, context)
        
        # Infer argument types
        arg_types = CallContextBuilder._infer_arg_types(expr, context, type_inferencer)
        
        # Get table info for arguments
        arg_table_infos = CallContextBuilder._get_arg_table_infos(expr, context)
        
        # Get return type
        return_type = CallContextBuilder._get_return_type(expr, context, signature)
        
        return CallGenerationContext(
            expr=expr,
            func_path=func_path,
            signature=signature,
            arg_types=arg_types,
            arg_table_infos=arg_table_infos,
            return_type=return_type,
            is_local=is_local,
            line_number=getattr(expr, 'lineno', None),
        )
    
    @staticmethod
    def _get_function_path(expr: astnodes.Call) -> Optional[str]:
        """Extract function path from call expression
        
        Args:
            expr: Call AST node
            
        Returns:
            Function path (e.g., "string.format", "print") or None
        """
        if isinstance(expr.func, astnodes.Index):
            if isinstance(expr.func.value, astnodes.Name) and isinstance(expr.func.idx, astnodes.Name):
                module_name = expr.func.value.id
                func_name = expr.func.idx.id
                return f"{module_name}.{func_name}"
        elif isinstance(expr.func, astnodes.Name):
            return expr.func.id
        
        return None
    
    @staticmethod
    def _is_local_call(expr: astnodes.Call, context: TranslationContext) -> bool:
        """Check if this is a local function call
        
        Args:
            expr: Call AST node
            context: Translation context
            
        Returns:
            True if local function call
        """
        if not isinstance(expr.func, astnodes.Name):
            return False
        
        func_name = expr.func.id
        symbol = context.resolve_symbol(func_name)
        return bool(symbol and not symbol.is_global)
    
    @staticmethod
    def _infer_arg_types(expr: astnodes.Call, context: TranslationContext, type_inferencer) -> List[Type]:
        """Infer types for all arguments
        
        Args:
            expr: Call AST node
            context: Translation context
            type_inferencer: Optional type inference engine
            
        Returns:
            List of Type objects for each argument
        """
        from lua2c.generators.call_generation.type_queries import TypeQueryService
        
        type_service = TypeQueryService(context, type_inferencer)
        arg_types = []
        
        for arg in expr.args:
            arg_type = type_service.get_expression_type(arg)
            if arg_type is None:
                arg_type = Type(TypeKind.UNKNOWN)
            arg_types.append(arg_type)
        
        return arg_types
    
    @staticmethod
    def _get_arg_table_infos(expr: astnodes.Call, context: TranslationContext) -> Dict[int, TableTypeInfo]:
        """Get table type information for arguments
        
        Args:
            expr: Call AST node
            context: Translation context
            
        Returns:
            Dict mapping argument index to TableTypeInfo
        """
        from lua2c.generators.call_generation.type_queries import TypeQueryService
        
        type_service = TypeQueryService(context)
        table_infos = {}
        
        for i, arg in enumerate(expr.args):
            if isinstance(arg, astnodes.Name):
                table_info = type_service.get_table_info(arg.id)
                if table_info:
                    table_infos[i] = table_info
        
        return table_infos
    
    @staticmethod
    def _get_return_type(expr: astnodes.Call, context: TranslationContext, signature: Optional[FunctionSignature]) -> Optional[Type]:
        """Get return type for function call
        
        Args:
            expr: Call AST node
            context: Translation context
            signature: Function signature if available
            
        Returns:
            Return type or None
        """
        if signature and signature.return_type:
            # Map C++ types to TypeKind
            if signature.return_type == "void":
                return Type(TypeKind.NIL)
            elif signature.return_type == "double":
                return Type(TypeKind.NUMBER)
            elif signature.return_type == "std::string":
                return Type(TypeKind.STRING)
            elif signature.return_type == "bool":
                return Type(TypeKind.BOOLEAN)
            else:
                return Type(TypeKind.UNKNOWN)
        
        # Local functions or unknown functions return luaValue
        return Type(TypeKind.UNKNOWN)
