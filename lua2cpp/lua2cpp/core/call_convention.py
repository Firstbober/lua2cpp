"""Call convention system for optimized code generation.

Provides configurable conventions for how module/function access should be
transpiled to C++ - either as direct function calls (fast) or table indexing (flexible).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from pathlib import Path


class CallConvention(Enum):
    """Convention for how to generate C++ code for module access."""
    
    NAMESPACE = "namespace"        # X::Y() - C++ namespace syntax
    FLAT = "flat"                  # X_Y() - flat function names
    FLAT_NESTED = "flat_nested"    # X_Y_Z() - flattened nested paths
    TABLE = "table"                # X["Y"] - table indexing (default, slowest)


@dataclass
class ModuleConventionConfig:
    """Configuration for a specific module's call convention.
    
    Attributes:
        convention: The call convention to use
        cpp_prefix: Prefix for flat function names (e.g., "love_")
        cpp_namespace: C++ namespace name (e.g., "math_lib")
        flatten_depth: How many levels to flatten (-1 = unlimited)
    """
    convention: CallConvention
    cpp_prefix: str = ""
    cpp_namespace: str = ""
    flatten_depth: int = -1


class CallConventionRegistry:
    """Registry for module call conventions.
    
    Provides lookup methods to determine how a module's functions and fields
    should be transpiled to C++.
    """
    
    def __init__(self):
        self._modules: Dict[str, ModuleConventionConfig] = {}
        self._default = CallConvention.TABLE
        self._initialize_defaults()
    
    def _initialize_defaults(self) -> None:
        """Initialize default conventions for standard Lua libraries."""
        # Standard Lua libraries - namespace style (existing behavior)
        self.register('math', CallConvention.NAMESPACE, cpp_namespace='math_lib')
        self.register('io', CallConvention.NAMESPACE, cpp_namespace='io')
        self.register('string', CallConvention.NAMESPACE, cpp_namespace='string_lib')
        self.register('table', CallConvention.NAMESPACE, cpp_namespace='table_lib')
        self.register('os', CallConvention.NAMESPACE, cpp_namespace='os_lib')
        
        # l2c runtime
        self.register('l2c', CallConvention.NAMESPACE, cpp_namespace='l2c')
    
    def register(self, module: str, convention: CallConvention, 
                 cpp_prefix: str = "", cpp_namespace: str = "", 
                 flatten_depth: int = -1) -> None:
        """Register a convention for a module.
        
        Args:
            module: Module name (e.g., "love", "G")
            convention: Call convention to use
            cpp_prefix: For FLAT conventions, prefix for function names
            cpp_namespace: For NAMESPACE convention, C++ namespace name
            flatten_depth: How many levels to flatten (-1 = unlimited)
        """
        self._modules[module] = ModuleConventionConfig(
            convention=convention,
            cpp_prefix=cpp_prefix,
            cpp_namespace=cpp_namespace,
            flatten_depth=flatten_depth
        )
    
    def get_config(self, module: str) -> ModuleConventionConfig:
        """Get convention config for a module.
        
        Args:
            module: Module name
            
        Returns:
            ModuleConventionConfig (defaults to TABLE if not registered)
        """
        return self._modules.get(module, ModuleConventionConfig(self._default))
    
    def get_convention(self, module: str) -> CallConvention:
        """Get call convention for a module."""
        return self.get_config(module).convention
    
    def has_convention(self, module: str) -> bool:
        """Check if a module has a registered convention."""
        return module in self._modules
    
    def load_from_cli(self, specs: List[str]) -> None:
        """Load conventions from CLI argument specs.
        
        Parses specs like: ["love=flat_nested", "G=flat"]
        
        Args:
            specs: List of "module=convention" strings
        """
        for spec in specs:
            if '=' not in spec:
                continue
            module, conv_str = spec.split('=', 1)
            module = module.strip()
            conv_str = conv_str.strip()
            
            # Parse convention
            convention_map = {
                'namespace': CallConvention.NAMESPACE,
                'flat': CallConvention.FLAT,
                'flat_nested': CallConvention.FLAT_NESTED,
                'table': CallConvention.TABLE,
            }
            
            if conv_str in convention_map:
                convention = convention_map[conv_str]
                # Derive prefix from module name for flat conventions
                prefix = f"{module}_" if convention in (CallConvention.FLAT, CallConvention.FLAT_NESTED) else ""
                self.register(module, convention, cpp_prefix=prefix)
    
    def load_from_yaml(self, path: Path) -> None:
        """Load conventions from YAML config file.
        
        Args:
            path: Path to YAML config file
        """
        try:
            import yaml
        except ImportError:
            return  # YAML not available, skip
        
        if not path.exists():
            return
        
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        
        if not config or 'conventions' not in config:
            return
        
        for module, settings in config.get('conventions', {}).items():
            style = settings.get('style', 'table')
            convention_map = {
                'namespace': CallConvention.NAMESPACE,
                'flat': CallConvention.FLAT,
                'flat_nested': CallConvention.FLAT_NESTED,
                'table': CallConvention.TABLE,
            }
            
            if style in convention_map:
                convention = convention_map[style]
                prefix = settings.get('prefix', f"{module}_")
                namespace = settings.get('namespace', module)
                depth = settings.get('flatten_depth', -1)
                
                self.register(module, convention, 
                             cpp_prefix=prefix, 
                             cpp_namespace=namespace,
                             flatten_depth=depth)
    
    def __repr__(self) -> str:
        return f"CallConventionRegistry(modules={list(self._modules.keys())})"


def flatten_index_chain_parts(node) -> List[str]:
    """Extract module path parts from an Index chain.
    
    Examples:
        love.timer.step → ["love", "timer", "step"]
        G.SETTINGS.graphics → ["G", "SETTINGS", "graphics"]
        math.sqrt → ["math", "sqrt"]
    
    Args:
        node: AST node (Name, Index, or String)
        
    Returns:
        List of path components
    """
    from luaparser import astnodes
    
    parts = []
    
    def extract(n):
        if isinstance(n, astnodes.Name):
            parts.append(n.id)
        elif isinstance(n, astnodes.Index):
            # Add the index part
            if isinstance(n.idx, astnodes.Name):
                parts.append(n.idx.id)
            elif isinstance(n.idx, astnodes.String):
                s = n.idx.s
                parts.append(s.decode() if isinstance(s, bytes) else s)
            # Recurse into value
            extract(n.value)
        elif isinstance(n, astnodes.String):
            s = n.s
            parts.append(s.decode() if isinstance(s, bytes) else s)
    
    extract(node)
    parts.reverse()
    return parts


def get_root_module(node) -> str:
    """Get the root module name from an Index chain or Name node.
    
    Args:
        node: AST node (Name or Index)
        
    Returns:
        Root module name, or empty string if not determinable
    """
    from luaparser import astnodes
    
    if isinstance(node, astnodes.Name):
        return node.id
    elif isinstance(node, astnodes.Index):
        return get_root_module(node.value)
    return ""
