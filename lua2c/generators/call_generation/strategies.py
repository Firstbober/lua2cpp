"""Strategy pattern for function call generation
Different call types (local, library, variadic, vector) use different
strategies, making code more modular and testable.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from luaparser import astnodes
from lua2c.core.type_system import Type, TypeKind
from lua2c.core.context import TranslationContext
from lua2c.generators.call_generation.context import CallGenerationContext


class CallGenerationStrategy(ABC):
    """Base class for call generation strategies"""
    
    @abstractmethod
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        """Check if this strategy can handle call
        
        Args:
            expr: Call AST node
            context: Translation context
            **kwargs: Additional context (signature, etc.)
            
        Returns:
            True if this strategy can handle the call
        """
        pass
    
    @abstractmethod
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:
        """Generate C++ code for call
        
        Args:
            expr: Call AST node
            context: Translation context
            expr_generator: ExprGenerator instance
            call_ctx: Call generation context
            
        Returns:
            Generated C++ code
        """
        pass


class LocalFunctionStrategy(CallGenerationStrategy):
    """Strategy for local function calls: func(state, args...)"""
    
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        if not isinstance(expr.func, astnodes.Name):
            return False
        symbol = context.resolve_symbol(expr.func.id)
        return symbol and not symbol.is_global
    
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:
        from lua2c.generators.call_generation.type_queries import TypeQueryService

        func = expr_generator.generate(expr.func)

        # Generate arguments with minimal luaValue wrapping
        # Functions with auto&& parameters can bind to both native types and luaValue
        # Numeric literals need wrapping to ensure consistent type (double)
        # The compiler will implicitly convert native types to luaValue if needed
        arg_codes = []
        for arg in expr.args:
            is_literal = isinstance(arg, (astnodes.Number, astnodes.String,
                                        astnodes.TrueExpr, astnodes.FalseExpr, astnodes.Nil))
            is_call = isinstance(arg, astnodes.Call)

            if is_literal:
                expr_generator._set_expected_type(arg, Type(TypeKind.NUMBER) if isinstance(arg, astnodes.Number) else Type(TypeKind.STRING))

            arg_code = expr_generator.generate(arg)
            expr_generator._clear_expected_type(arg)

            # Wrap numeric literals in luaValue() to ensure double type
            # This prevents auto return type inconsistency (e.g., mixing int and double)
            if is_literal and isinstance(arg, astnodes.Number):
                arg_codes.append(f"luaValue({arg_code})")
            elif is_call or arg_code.startswith("luaValue("):
                arg_codes.append(arg_code)
            else:
                arg_codes.append(arg_code)

        args_str = ", ".join(arg_codes)
        if args_str:
            return f"{func}(state, {args_str})"
        else:
            return f"{func}(state)"


class LibraryFunctionStrategy(CallGenerationStrategy):
    """Strategy for library function calls"""
    
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        # Library functions are those with a signature in the registry
        # This is a base strategy that delegates to sub-strategies
        if not isinstance(expr.func, (astnodes.Name, astnodes.Index)):
            return False
        
        # Check if this is a local function - if so, LocalFunctionStrategy handles it
        if isinstance(expr.func, astnodes.Name):
            symbol = context.resolve_symbol(expr.func.id)
            if symbol and not symbol.is_global:
                return False
        
        # Otherwise, it's a library or global function
        return True
    
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:
        # LibraryFunctionStrategy delegates to sub-strategies
        # This is handled by the strategy selection logic in ExprGenerator
        raise NotImplementedError("LibraryFunctionStrategy delegates to sub-strategies")


class StaticLibraryStrategy(CallGenerationStrategy):
    """Strategy for static typed library functions (math.sqrt, etc.)"""
    
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        call_ctx = kwargs.get('call_ctx')
        if not call_ctx or not call_ctx.signature:
            return False

        # Don't handle always_variadic or is_variadic functions
        if getattr(call_ctx.signature, 'always_variadic', False):
            return False
        if getattr(call_ctx.signature, 'is_variadic', False):
            return False

        # Check for fixed parameter types (no vector<luaValue>)
        has_fixed_params = any("vector<luaValue>" not in pt for pt in call_ctx.signature.param_types)
        return has_fixed_params and len(call_ctx.signature.param_types) > 0
    
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:

        # Generate function path
        func_path = expr_generator.generate(expr.func)

        # Generate arguments with type hints
        args = []
        for i, arg in enumerate(expr.args):
            # Set expected type for std::string parameters
            if call_ctx.signature and call_ctx.signature.param_types:
                param_type = call_ctx.signature.param_types[i] if i < len(call_ctx.signature.param_types) else None
                if param_type and "std::string" in param_type and "vector" not in param_type:
                    # Parameter is std::string, set expected type for string literals
                    expr_generator._set_expected_type(arg, Type(TypeKind.STRING))

            # Generate argument (type hints will be used if set)
            args.append(expr_generator.generate(arg))

            # Clear expected type after generating
            expr_generator._clear_expected_type(arg)

        # Build call
        return f"{func_path}({', '.join(args)})"


class DefaultCallStrategy(CallGenerationStrategy):
    """Fallback strategy for unknown functions"""
    
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        # Always can handle (fallback)
        return True
    
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:
        # Generate function name
        func = expr_generator.generate(expr.func)
        
        # Generate luaValue-wrapped arguments
        args = []
        for arg in expr.args:
            arg_code = expr_generator.generate(arg)
            # Wrap in luaValue if not already
            if not arg_code.startswith("luaValue("):
                args.append(f"luaValue({arg_code})")
            else:
                args.append(arg_code)
        
        # Build call with vector
        if args:
            return f"{func}({{{', '.join(args)}}})"
        else:
            return f"{func}({{}})"


class VariadicLibraryStrategy(CallGenerationStrategy):
    """Strategy for variadic library functions (print, io.write, string.format)"""
    
    def can_handle(self, expr: astnodes.Call, context: TranslationContext, **kwargs) -> bool:
        call_ctx = kwargs.get('call_ctx')
        if not call_ctx or not call_ctx.signature:
            return False
        
        # Check for always_variadic flag
        if getattr(call_ctx.signature, 'always_variadic', False):
            return True
        
        # Check for is_variadic flag
        if getattr(call_ctx.signature, 'is_variadic', False):
            return True
        
        return False
    
    def generate(self, expr: astnodes.Call, context: TranslationContext, expr_generator, call_ctx: CallGenerationContext) -> str:

        # Generate function path
        func_path = expr_generator.generate(expr.func)

        # Check if this is string.format (has std::string first param)
        is_string_format = (call_ctx.func_path == "string.format" if hasattr(call_ctx, 'func_path') else False)
        has_string_first_param = (call_ctx.signature and call_ctx.signature.param_types and
                              "std::string" in call_ctx.signature.param_types[0])

        # Generate arguments based on function signature
        if is_string_format and has_string_first_param:
            # string.format: first arg as std::string, rest as vector<luaValue>
            if len(expr.args) > 0:
                # Set expected type for format string
                expr_generator._set_expected_type(expr.args[0], Type(TypeKind.STRING))
                fmt_arg = expr_generator.generate(expr.args[0])
                expr_generator._clear_expected_type(expr.args[0])

                # Wrap remaining args in vector
                var_args = []
                for arg in expr.args[1:]:
                    arg_code = expr_generator.generate(arg)
                    if not arg_code.startswith("luaValue("):
                        var_args.append(f"luaValue({arg_code})")
                    else:
                        var_args.append(arg_code)

                if var_args:
                    return f"{func_path}({fmt_arg}, std::vector<luaValue>{{{', '.join(var_args)}}})"
                else:
                    return f"{func_path}({fmt_arg}, {{}})"
        else:
            # print/io.write: wrap all args in vector
            args = []
            for arg in expr.args:
                arg_code = expr_generator.generate(arg)
                if not arg_code.startswith("luaValue("):
                    args.append(f"luaValue({arg_code})")
                else:
                    args.append(arg_code)

            if args:
                return f"{func_path}(std::vector<luaValue>{{{', '.join(args)}}})"
            else:
                return f"{func_path}({{}})"
