"""Dependency resolution system for Lua2C multi-file projects

Analyzes require() calls and builds dependency graph with topological sort.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from pathlib import Path
from collections import deque

try:
    from luaparser import astnodes, ast
except ImportError:
    raise ImportError("luaparser is required. Install with: pip install luaparser")


@dataclass
class ModuleDependency:
    """Represents a single require() dependency"""

    module_name: str  # The module being required (e.g., "utils", "subdir_helper")
    line_number: int
    is_string_literal: bool = True  # True if require("utils"), False if require(var)

    def __str__(self) -> str:
        return f"{self.module_name}:{self.line_number}"


@dataclass
class ModuleInfo:
    """Information about a Lua module file"""

    module_name: str  # e.g., "utils", "subdir_helper"
    file_path: Path  # Full path to .lua file
    relative_path: Path  # Relative to project root
    dependencies: List[ModuleDependency] = field(default_factory=list)

    def add_dependency(self, dep: ModuleDependency) -> None:
        """Add a dependency"""
        self.dependencies.append(dep)


class DependencyGraph:
    """Dependency graph with topological sort using Kahn's algorithm"""

    def __init__(self):
        self.dependencies: Dict[str, Set[str]] = {}  # module -> set of modules it depends on
        self.reverse_dependencies: Dict[str, Set[str]] = (
            {}
        )  # module -> set of modules that depend on it
        self.all_modules: Set[str] = set()

    def add_module(self, module_name: str) -> None:
        """Add a module to graph"""
        if module_name not in self.dependencies:
            self.dependencies[module_name] = set()
        if module_name not in self.reverse_dependencies:
            self.reverse_dependencies[module_name] = set()
        self.all_modules.add(module_name)

    def add_dependency(self, from_module: str, to_module: str) -> None:
        """Add a dependency edge: from_module -> to_module

        Args:
            from_module: Module that requires other
            to_module: Module being required (prerequisite)
        """
        self.add_module(from_module)
        self.add_module(to_module)
        # from_module depends on to_module
        self.dependencies[from_module].add(to_module)
        # For topological sort: edge is to_module -> from_module (prerequisite -> dependent)
        self.reverse_dependencies[to_module].add(from_module)

    def topological_sort(self) -> List[str]:
        """Perform topological sort using Kahn's algorithm

        Returns:
            List of module names in dependency order (dependencies before dependents)

        Raises:
            ValueError: If circular dependency detected
        """
        # Calculate in-degrees (number of incoming edges in reverse_dependencies)
        in_degree: Dict[str, int] = {module: 0 for module in self.all_modules}
        for module in self.all_modules:
            for dependent in self.reverse_dependencies[module]:
                in_degree[dependent] += 1

        # Start with modules having no dependencies (in-degree = 0)
        queue = deque([module for module in self.all_modules if in_degree[module] == 0])
        result: List[str] = []

        while queue:
            module = queue.popleft()
            result.append(module)

            # Reduce in-degree for modules that depend on this one
            for dependent in self.reverse_dependencies[module]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Check for cycles
        if len(result) != len(self.all_modules):
            # Find cycle for better error message
            cycle = self._find_cycle()
            raise ValueError(f"Circular dependency detected: {' -> '.join(cycle)}")

        return result

    def _find_cycle(self) -> List[str]:
        """Find a cycle in dependency graph for error reporting

        Returns:
            List of module names forming a cycle
        """
        visited = set()
        rec_stack = set()
        cycle_path: List[str] = []
        found_cycle: List[str] = []

        def dfs(module: str) -> bool:
            visited.add(module)
            rec_stack.add(module)
            cycle_path.append(module)

            for dep in self.dependencies[module]:
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    # Found a cycle - store it
                    nonlocal found_cycle
                    cycle_start = cycle_path.index(dep)
                    found_cycle = cycle_path[cycle_start:]
                    return True

            rec_stack.remove(module)
            cycle_path.pop()
            return False

        for module in self.all_modules:
            if module not in visited:
                if dfs(module):
                    return found_cycle

        return []

    def get_dependents(self, module_name: str) -> Set[str]:
        """Get all modules that depend on given module"""
        return self.reverse_dependencies.get(module_name, set()).copy()

    def get_dependencies(self, module_name: str) -> Set[str]:
        """Get all modules that given module depends on"""
        return self.dependencies.get(module_name, set()).copy()


class DependencyResolver:
    """Parses Lua AST and extracts require() dependencies"""

    def __init__(self, project_root: Path) -> None:
        """Initialize dependency resolver

        Args:
            project_root: Root directory of project
        """
        self.project_root = project_root

    def resolve_project(self, lua_files: List[Path]) -> Dict[str, ModuleInfo]:
        """Resolve dependencies for entire project

        Args:
            lua_files: List of .lua file paths (relative to project_root)

        Returns:
            Dict mapping module_name -> ModuleInfo
        """
        module_infos: Dict[str, ModuleInfo] = {}

        # First pass: collect all modules
        for lua_file_rel in lua_files:
            lua_file_abs = self.project_root / lua_file_rel
            module_name = self._path_to_module_name(lua_file_rel)
            module_infos[module_name] = ModuleInfo(
                module_name=module_name, file_path=lua_file_abs, relative_path=lua_file_rel
            )

        # Second pass: extract dependencies
        for module_name, module_info in module_infos.items():
            dependencies = self._resolve_file_dependencies(module_info.file_path)
            module_info.dependencies = dependencies

        # Validate all required modules exist
        for module_name, module_info in module_infos.items():
            for dep in module_info.dependencies:
                if dep.module_name not in module_infos:
                    raise ValueError(
                        f"Module '{module_name}' requires '{dep.module_name}' "
                        f"(line {dep.line_number}) but it doesn't exist in project"
                    )

        return module_infos

    def _path_to_module_name(self, path: Path) -> str:
        """Convert file path to module name

        Examples:
            utils.lua -> utils
            subdir/helper.lua -> subdir__helper

        Args:
            path: File path (relative to project_root)

        Returns:
            Module name
        """
        # Remove .lua extension
        stem = path.with_suffix("").name

        # If file is in subdirectory, include directory name
        if len(path.parts) > 1:
            parent = path.parent
            return f"{parent.name}__{stem}"

        return stem

    def _module_name_to_path(self, module_name: str) -> Optional[Path]:
        """Convert module name to file path (reverse of _path_to_module_name)

        Examples:
            utils -> utils.lua
            subdir__helper -> subdir/helper.lua

        Args:
            module_name: Module name

        Returns:
            Path to .lua file or None if not found
        """
        # Try direct match: utils.lua
        direct_path = Path(f"{module_name}.lua")
        if (self.project_root / direct_path).exists():
            return direct_path

        # Try subdirectory match: subdir/helper.lua (using __ separator)
        if "__" in module_name:
            parts = module_name.split("__", 1)
            subdir_path = Path(parts[0]) / f"{parts[1]}.lua"
            if (self.project_root / subdir_path).exists():
                return subdir_path

        return None

    def _resolve_file_dependencies(self, lua_file: Path) -> List[ModuleDependency]:
        """Parse Lua file and extract require() calls

        Args:
            lua_file: Path to .lua file

        Returns:
            List of ModuleDependency objects
        """
        with open(lua_file, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        dependencies: List[ModuleDependency] = []

        def visit_node(node: astnodes.Node) -> None:
            """Recursively visit AST nodes to find require() calls"""
            if isinstance(node, astnodes.Call):
                func_name = self._get_call_function_name(node)
                if func_name == "require":
                    dep = self._parse_require_call(node)
                    if dep:
                        dependencies.append(dep)

            # Recursively visit child nodes - only known AST attributes
            # Check for body attribute (blocks, functions, etc.)
            if hasattr(node, "body"):
                if isinstance(node.body, astnodes.Block):
                    for stmt in node.body.body:
                        if isinstance(stmt, astnodes.Node):
                            visit_node(stmt)
                elif isinstance(node.body, list):
                    for stmt in node.body:
                        if isinstance(stmt, astnodes.Node):
                            visit_node(stmt)
                elif isinstance(node.body, astnodes.Node):
                    visit_node(node.body)

            # Check for expression-related attributes
            for attr in ["left", "right", "operand", "func", "test", "orelse"]:
                if hasattr(node, attr):
                    child = getattr(node, attr)
                    if child and isinstance(child, astnodes.Node):
                        visit_node(child)

            # Check for list attributes
            for attr in ["args", "targets", "values"]:
                if hasattr(node, attr):
                    children = getattr(node, attr)
                    if isinstance(children, (list, tuple)):
                        for child in children:
                            if isinstance(child, astnodes.Node):
                                visit_node(child)

        visit_node(tree)
        return dependencies

    def _get_call_function_name(self, call_node: astnodes.Call) -> Optional[str]:
        """Extract function name from Call node

        Args:
            call_node: Call AST node

        Returns:
            Function name or None
        """
        if isinstance(call_node.func, astnodes.Name):
            return call_node.func.id
        return None

    def _parse_require_call(self, call_node: astnodes.Call) -> Optional[ModuleDependency]:
        """Parse a require() call to extract module name

        Args:
            call_node: Call AST node for require()

        Returns:
            ModuleDependency or None if parsing fails
        """
        if not call_node.args:
            return None

        arg = call_node.args[0]

        # Only support string literal require()
        if isinstance(arg, astnodes.String):
            require_path = arg.s.decode() if isinstance(arg.s, bytes) else arg.s
            module_name = self._require_to_module_name(require_path)

            # Try to get line number, but handle AttributeError gracefully
            try:
                line_number = arg.line if arg.line is not None else 0
            except AttributeError:
                line_number = 0

            return ModuleDependency(
                module_name=module_name, line_number=line_number, is_string_literal=True
            )

        # Variable require() - not supported yet
        return None

    def _require_to_module_name(self, require_path: str) -> str:
        """Convert require() path to module name

        Examples:
            "utils" -> utils
            "subdir.helper" -> subdir__helper

        Args:
            require_path: Path from require() call

        Returns:
            Module name
        """
        # Replace dots with double underscores (matches __ separator in _path_to_module_name)
        return require_path.replace(".", "__")

    def build_dependency_graph(self, module_infos: Dict[str, ModuleInfo]) -> DependencyGraph:
        """Build dependency graph from module information

        Args:
            module_infos: Dict mapping module_name -> ModuleInfo

        Returns:
            DependencyGraph with all dependencies
        """
        graph = DependencyGraph()

        # Add all modules
        for module_name in module_infos:
            graph.add_module(module_name)

        # Add dependencies
        for module_name, module_info in module_infos.items():
            for dep in module_info.dependencies:
                graph.add_dependency(module_name, dep.module_name)

        return graph
