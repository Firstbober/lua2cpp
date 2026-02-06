"""Function signature registry for inter-procedural type analysis

Tracks function signatures, parameter types, and call sites to enable
type propagation between function boundaries.

Architecture:
- Collects all function definitions with their parameter signatures
- Records all call sites with argument-to-parameter mappings
- Provides query interface for type propagation
- Maintains call graph for dependency analysis
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

if __name__.startswith('lua2c.analyzers'):
    # When imported from within lua2c package
    from lua2c.core.type_system import Type, TableTypeInfo
else:
    # For TYPE_CHECKING and external imports
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from lua2c.core.type_system import Type, TableTypeInfo


@dataclass
class CallSiteInfo:
    """Information about a specific function call site

    Stores details about where a function is called and what arguments
    are passed, enabling type propagation from arguments to parameters
    and vice versa.

    Attributes:
        caller_name: Name of the function making this call
        arg_symbols: Symbol names for each argument (None if not a simple name)
        line_number: Source line number where call occurs
    """
    caller_name: str
    arg_symbols: List[Optional[str]]
    line_number: Optional[int] = None

    def get_arg_symbol(self, param_index: int) -> Optional[str]:
        """Get the symbol name for an argument at a specific parameter index

        Args:
            param_index: Parameter index (0-based)

        Returns:
            Symbol name or None if argument is not a simple name
        """
        if 0 <= param_index < len(self.arg_symbols):
            return self.arg_symbols[param_index]
        return None


@dataclass
class FunctionSignature:
    """Signature and type information for a function

    Tracks a function's parameters, their types (when known),
    and all call sites where the function is invoked.

    Attributes:
        name: Function name
        param_names: Ordered list of parameter names
        param_table_info: Mapping from parameter index to table type info
        return_type: Inferred return type (None if unknown)
        is_local: True if this is a local function
        call_sites: List of all call sites for this function
    """
    name: str
    param_names: List[str]
    param_table_info: Dict[int, 'TableTypeInfo'] = field(default_factory=dict)
    return_type: Optional['Type'] = None
    is_local: bool = False
    call_sites: List[CallSiteInfo] = field(default_factory=list)

    def get_param_index(self, param_name: str) -> Optional[int]:
        """Get the index of a parameter by name

        Args:
            param_name: Parameter name to look up

        Returns:
            Parameter index or None if not found
        """
        try:
            return self.param_names.index(param_name)
        except ValueError:
            return None

    def get_num_params(self) -> int:
        """Get number of parameters in this function

        Returns:
            Number of parameters
        """
        return len(self.param_names)

    def has_param_info(self, param_index: int) -> bool:
        """Check if parameter has type information

        Args:
            param_index: Parameter index

        Returns:
            True if parameter has table type info
        """
        return param_index in self.param_table_info

    def get_all_call_sites(self) -> List[CallSiteInfo]:
        """Get all call sites for this function

        Returns:
            List of call site information
        """
        return self.call_sites.copy()


class FunctionSignatureRegistry:
    """Registry for tracking function signatures and call sites

    Maintains a comprehensive mapping of all functions in the codebase,
    their parameter signatures, type information, and call graph.
    Serves as the central data structure for inter-procedural type analysis.

    Usage Example:
        registry = FunctionSignatureRegistry()

        # Register a function
        registry.register_function("foo", ["x", "y"], is_local=True)

        # Update parameter type info
        from lua2c.core.type_system import TableTypeInfo, Type, TypeKind
        table_info = TableTypeInfo(is_array=True, value_type=Type(TypeKind.NUMBER))
        registry.update_param_table_info("foo", 0, table_info)

        # Record a call site
        registry.record_call_site("main", "foo", ["arg1", "arg2"], line=42)

        # Query parameter type info
        param_info = registry.get_param_table_info("foo", 0)
    """

    def __init__(self) -> None:
        """Initialize empty function registry"""
        self.signatures: Dict[str, FunctionSignature] = {}
        self.call_graph: Dict[str, List[str]] = {}  # func → list of callers

    def register_function(
        self,
        name: str,
        param_names: List[str],
        is_local: bool = True
    ) -> FunctionSignature:
        """Register a function signature

        Creates a new function signature entry in the registry.
        If a function with this name already exists, it will be overwritten.

        Args:
            name: Function name
            param_names: Ordered list of parameter names
            is_local: True if this is a local function

        Returns:
            Created FunctionSignature object

        Raises:
            ValueError: If param_names contains duplicates
        """
        if len(param_names) != len(set(param_names)):
            raise ValueError(f"Function '{name}' has duplicate parameter names")

        signature = FunctionSignature(
            name=name,
            param_names=param_names,
            is_local=is_local
        )

        self.signatures[name] = signature

        # Initialize call graph entry
        if name not in self.call_graph:
            self.call_graph[name] = []

        return signature

    def has_function(self, name: str) -> bool:
        """Check if a function is registered

        Args:
            name: Function name

        Returns:
            True if function exists in registry
        """
        return name in self.signatures

    def get_signature(self, name: str) -> Optional[FunctionSignature]:
        """Get function signature by name

        Args:
            name: Function name

        Returns:
            FunctionSignature or None if not found
        """
        return self.signatures.get(name)

    def update_param_table_info(
        self,
        func_name: str,
        param_index: int,
        table_info: 'TableTypeInfo'
    ) -> bool:
        """Update table type information for a function parameter

        Sets or updates the table type info for a specific parameter.
        This is called during type inference when parameter usage
        patterns are discovered.

        Args:
            func_name: Function name
            param_index: Parameter index (0-based)
            table_info: Table type information to set

        Returns:
            True if update succeeded, False if function/param not found
        """
        signature = self.signatures.get(func_name)
        if not signature:
            return False

        if param_index < 0 or param_index >= len(signature.param_names):
            return False

        signature.param_table_info[param_index] = table_info
        return True

    def get_param_table_info(
        self,
        func_name: str,
        param_index: int
    ) -> Optional['TableTypeInfo']:
        """Get table type information for a function parameter

        Args:
            func_name: Function name
            param_index: Parameter index (0-based)

        Returns:
            TableTypeInfo or None if not available
        """
        signature = self.signatures.get(func_name)
        if not signature:
            return None

        return signature.param_table_info.get(param_index)

    def get_param_name(self, func_name: str, param_index: int) -> Optional[str]:
        """Get the name of a parameter by index

        Args:
            func_name: Function name
            param_index: Parameter index (0-based)

        Returns:
            Parameter name or None if not found
        """
        signature = self.signatures.get(func_name)
        if not signature:
            return None

        if 0 <= param_index < len(signature.param_names):
            return signature.param_names[param_index]
        return None

    def record_call_site(
        self,
        caller: str,
        callee: str,
        arg_symbols: List[Optional[str]],
        line: Optional[int] = None
    ) -> None:
        """Record a function call site

        Records that `caller` invoked `callee` with the given arguments.
        This information is used for type propagation between arguments
        and parameters.

        Args:
            caller: Name of function making the call
            callee: Name of function being called
            arg_symbols: Symbol names for each argument (None if not a name)
            line: Source line number
        """
        # Get or create callee signature
        callee_sig = self.signatures.get(callee)
        if not callee_sig:
            # Function not yet registered - this can happen if call comes
            # before definition in the AST
            callee_sig = self.register_function(callee, [], is_local=False)

        # Record call site
        call_site = CallSiteInfo(
            caller_name=caller,
            arg_symbols=arg_symbols,
            line_number=line
        )
        callee_sig.call_sites.append(call_site)

        # Update call graph
        if callee not in self.call_graph:
            self.call_graph[callee] = []
        if caller not in self.call_graph[callee]:
            self.call_graph[callee].append(caller)

    def get_call_sites_for_function(self, func_name: str) -> List[CallSiteInfo]:
        """Get all call sites for a specific function

        Args:
            func_name: Function name

        Returns:
            List of CallSiteInfo objects (empty if no calls)
        """
        signature = self.signatures.get(func_name)
        if not signature:
            return []

        return signature.get_all_call_sites()

    def get_callers_of_function(self, func_name: str) -> List[str]:
        """Get list of functions that call a specific function

        Args:
            func_name: Function name

        Returns:
            List of caller function names (empty if none)
        """
        return self.call_graph.get(func_name, []).copy()

    def get_all_functions(self) -> List[str]:
        """Get list of all registered functions

        Returns:
            List of function names
        """
        return list(self.signatures.keys())

    def get_functions_with_param_info(self) -> List[str]:
        """Get list of functions that have parameter type information

        Returns:
            List of function names with typed parameters
        """
        result = []
        for name, sig in self.signatures.items():
            if sig.param_table_info:
                result.append(name)
        return result

    def get_statistics(self) -> Dict:
        """Get registry statistics

        Returns:
            Dictionary with statistics about registered functions
        """
        total_params = sum(len(sig.param_names) for sig in self.signatures.values())
        typed_params = sum(
            len(sig.param_table_info) for sig in self.signatures.values()
        )
        total_calls = sum(len(sig.call_sites) for sig in self.signatures.values())

        return {
            "total_functions": len(self.signatures),
            "total_parameters": total_params,
            "typed_parameters": typed_params,
            "untyped_parameters": total_params - typed_params,
            "total_call_sites": total_calls
        }

    def print_statistics(self) -> str:
        """Generate formatted statistics string

        Returns:
            Formatted statistics as string
        """
        stats = self.get_statistics()
        lines = ["=== Function Signature Registry Statistics ==="]
        lines.append(f"Total functions: {stats['total_functions']}")
        lines.append(f"Total parameters: {stats['total_parameters']}")
        lines.append(f"  Typed parameters: {stats['typed_parameters']}")
        lines.append(f"  Untyped parameters: {stats['untyped_parameters']}")
        lines.append(f"Total call sites: {stats['total_call_sites']}")

        # List functions with typed parameters
        typed_funcs = self.get_functions_with_param_info()
        if typed_funcs:
            lines.append(f"\nFunctions with typed parameters ({len(typed_funcs)}):")
            for func_name in typed_funcs:
                sig = self.signatures[func_name]
                typed_indices = list(sig.param_table_info.keys())
                lines.append(f"  {func_name}: params {typed_indices}")

        return "\n".join(lines)
