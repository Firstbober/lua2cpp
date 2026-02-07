"""Main CLI entry point for Lua2C++ transpiler"""

import sys
import argparse
from pathlib import Path
from typing import List, Set, Optional

try:
    from luaparser import ast
except ImportError:
    print("Error: luaparser is required. Install with: pip install luaparser", file=sys.stderr)
    sys.exit(1)

from lua2c.core.context import TranslationContext
from lua2c.core.scope import ScopeManager
from lua2c.core.symbol_table import SymbolTable
from lua2c.generators.cpp_emitter import CppEmitter
from lua2c.generators.header_generator import HeaderGenerator
from lua2c.generators.project_state_generator import ProjectStateGenerator
from lua2c.generators.main_generator import MainGenerator
from lua2c.module_system.dependency_resolver import DependencyResolver


def transpile_file(input_file: Path) -> str:
    """Transpile a single Lua file to C++

    Args:
        input_file: Path to Lua source file

    Returns:
        Generated C++ code
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        source = f.read()

    tree = ast.parse(source)

    try:
        rel_path = input_file.relative_to(Path.cwd())
    except ValueError:
        rel_path = input_file
    module_path = str(rel_path.parent) if hasattr(rel_path, 'parent') else str(rel_path)
    context = TranslationContext(Path.cwd(), module_path)
    emitter = CppEmitter(context)
    return emitter.generate_file(tree, input_file)


def _determine_project_name(project_root: Path, main_file: Path) -> str:
    """Determine project name from directory structure or main file.

    Args:
        project_root: Root directory of project
        main_file: Path to main.lua

    Returns:
        Sanitized project name (C identifier safe)
    """
    if project_root.name:
        name = project_root.name.replace('-', '_')
        return name
    return main_file.stem.replace('-', '_')


def _find_lua_files(project_root: Path) -> List[Path]:
    """Find all .lua files in project (recursive).

    Args:
        project_root: Root directory to search

    Returns:
        List of .lua file paths (relative to project_root)
    """
    lua_files = []
    skip_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'build', 'dist'}

    for lua_file in project_root.rglob("*.lua"):
        if any(skip in lua_file.parts for skip in skip_dirs):
            continue
        rel_path = lua_file.relative_to(project_root)
        lua_files.append(rel_path)

    return sorted(lua_files)


def _collect_globals(project_root: Path, lua_files: List[Path]) -> Set[str]:
    """Collect all global variables used across all modules.

    Args:
        project_root: Project root directory
        lua_files: List of .lua file paths

    Returns:
        Set of global variable names
    """
    from luaparser import astnodes

    all_globals = set()

    for lua_file_rel in lua_files:
        lua_file_abs = project_root / lua_file_rel
        if not lua_file_abs.exists():
            continue

        with open(lua_file_abs, 'r', encoding='utf-8') as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except Exception:
            continue

        scope_mgr = ScopeManager()
        symbol_table = SymbolTable(scope_mgr)

        def visit_node(node: astnodes.Node) -> None:
            """Recursively visit AST nodes to collect globals."""
            if isinstance(node, astnodes.LocalAssign):
                for target in node.targets:
                    if hasattr(target, 'id'):
                        var_name = target.id
                        if not symbol_table.is_local(var_name):
                            symbol_table.add_local(var_name)
            elif isinstance(node, astnodes.Assign):
                for target in node.targets:
                    if hasattr(target, 'id'):
                        var_name = target.id
                        if not symbol_table.is_local(var_name):
                            symbol_table.add_global(var_name)
                            all_globals.add(var_name)
            elif isinstance(node, astnodes.LocalFunction):
                if hasattr(node.name, 'id'):
                    func_name = node.name.id
                    symbol_table.add_local(func_name)
                if hasattr(node, 'args'):
                    for param in node.args:
                        if hasattr(param, 'id'):
                            param_name = param.id
                            if not symbol_table.is_local(param_name):
                                symbol_table.add_local(param_name)
            elif isinstance(node, astnodes.Function):
                if hasattr(node.name, 'id'):
                    func_name = node.name.id
                    if not symbol_table.is_local(func_name):
                        symbol_table.add_global(func_name)
                        all_globals.add(func_name)
                if hasattr(node, 'args'):
                    for param in node.args:
                        if hasattr(param, 'id'):
                            param_name = param.id
                            if not symbol_table.is_local(param_name):
                                symbol_table.add_local(param_name)
            elif isinstance(node, astnodes.Name):
                name = node.id
                is_local = symbol_table.is_local(name)
                if not is_local:
                    all_globals.add(name)

            for attr in ['body', 'left', 'right', 'operand', 'func', 'test', 'orelse', 'args', 'targets', 'values', 'idx', 'value', 'params', 'init']:
                if hasattr(node, attr):
                    child = getattr(node, attr)
                    if child is None:
                        continue
                    if isinstance(child, list):
                        for item in child:
                            if hasattr(item, '__class__'):
                                visit_node(item)
                    elif hasattr(child, '__class__'):
                        visit_node(child)

        visit_node(tree)

    return all_globals


def _transpile_module(lua_file: Path, project_name: str) -> str:
    """Transpile a single Lua module to C++.

    Args:
        lua_file: Path to .lua file
        project_name: Name of project

    Returns:
        C++ code as string
    """
    with open(lua_file, 'r', encoding='utf-8') as f:
        source = f.read()

    tree = ast.parse(source)

    context = TranslationContext(lua_file.parent, str(lua_file))
    context.set_project_mode(project_name)

    emitter = CppEmitter(context)
    return emitter.generate_file(tree, lua_file)


def transpile_project(
    main_file: Path, output_dir: Optional[Path] = None, verbose: bool = False
) -> None:
    """Transpile entire project.

    Args:
        main_file: Path to main.lua file
        output_dir: Output directory (default: build/)
        verbose: Enable verbose output

    Raises:
        FileNotFoundError: If main_file doesn't exist
        ValueError: If no .lua files found in project
    """
    # Validate inputs
    if not main_file.exists():
        raise FileNotFoundError(f"Main file not found: {main_file}")

    project_root = main_file.parent
    if not project_root.name:
        raise ValueError(f"Invalid project root: {project_root}")

    project_name = _determine_project_name(project_root, main_file)

    lua_files = _find_lua_files(project_root)

    if not lua_files:
        raise ValueError(f"No .lua files found in {project_root}")

    if main_file.name not in [str(f) for f in lua_files]:
        raise FileNotFoundError(f"Main file '{main_file.name}' not found in discovered files: {lua_files}")

    if verbose:
        print(f"Project root: {project_root}")
        print(f"Project name: {project_name}")
        print(f"Found {len(lua_files)} Lua files:")
        for f in lua_files:
            print(f"  {f}")

    resolver = DependencyResolver(project_root)
    dep_graph = resolver.build_dependency_graph(resolver.resolve_project(lua_files))
    dependency_order = dep_graph.topological_sort()

    if verbose:
        print(f"\nDependency order: {' → '.join(dependency_order)}")

    if output_dir is None:
        output_dir = project_root / "build"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state_gen = ProjectStateGenerator(project_name)
    used_libraries = state_gen.detect_used_libraries(lua_files, project_root)

    all_globals = _collect_globals(project_root, lua_files)

    state_header = state_gen.generate_state_class(all_globals, set(dependency_order), used_libraries)
    state_file = output_dir / f"{project_name}_state.hpp"
    state_file.write_text(state_header)
    if verbose:
        print(f"\nGenerated: {state_file}")

    header_gen = HeaderGenerator()

    for lua_file_rel in lua_files:
        lua_file_abs = project_root / lua_file_rel
        if lua_file_rel == main_file.name:
            continue

        if verbose:
            print(f"\nTranspiling module: {lua_file_rel}")

        module_name = lua_file_abs.stem
        module_header = header_gen.generate_module_header(module_name, project_name)
        header_file = output_dir / f"{module_name}_module.hpp"
        header_file.write_text(module_header)

        module_code = _transpile_module(lua_file_abs, project_name)
        cpp_file = output_dir / f"{module_name}_module.cpp"
        cpp_file.write_text(module_code)

        if verbose:
            print(f"  Generated header: {header_file.name}")
            print(f"  Generated impl: {cpp_file.name}")

    if verbose:
        print(f"\nTranspiling main module: {main_file.name}")

    main_module_code = _transpile_module(main_file, project_name)
    main_cpp_file = output_dir / f"{main_file.stem}_module.cpp"
    main_cpp_file.write_text(main_module_code)

    main_header = header_gen.generate_module_header(main_file.stem, project_name)
    main_header_file = output_dir / f"{main_file.stem}_module.hpp"
    main_header_file.write_text(main_header)

    if verbose:
        print(f"  Generated header: {main_header_file.name}")
        print(f"  Generated impl: {main_cpp_file.name}")

    main_gen = MainGenerator()
    main_code = main_gen.generate_main_file(
        project_name, main_file, all_globals, dependency_order, used_libraries
    )
    main_file_out = output_dir / f"{project_name}_main.cpp"
    main_file_out.write_text(main_code)

    if verbose:
        print(f"\nGenerated: {main_file_out}")

    print(f"\n✓ Project transpilation complete!")
    print(f"  Output directory: {output_dir}")
    print(f"  Modules transpiled: {len(lua_files)}")
    print(f"\nTo compile:")
    runtime_path = Path(__file__).parent.parent.parent / "runtime"
    print(f"  cd {output_dir}")
    print(f"  g++ -std=c++17 -I{runtime_path} -o {project_name} {project_name}_main.cpp *_module.cpp {runtime_path}/*.cpp")


def main() -> None:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Lua to C++ transpiler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Examples:
    Single-file mode:
    python -m lua2c.cli.main file.lua -o output.cpp
    python -m lua2c.cli.main file.lua --output output.cpp

    Project mode:
    python -m lua2c.cli.main --main path/to/main.lua
    python -m lua2c.cli.main --main path/to/main.lua -o output_dir/
        """
    )
    parser.add_argument('input', help='Input Lua file (or main file with --main flag)')
    parser.add_argument(
        '--main', action='store_true',
        help='Treat input as project main file (transpile all modules)'
    )
    parser.add_argument(
        '-o', '--output', dest='output',
        help='Output file (single-file) or directory (project mode)'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    input_file = Path(args.input)

    if not input_file.exists():
        print(f"Error: File not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    if args.main and input_file.suffix != '.lua':
        print(f"Error: Main file must be a .lua file", file=sys.stderr)
        sys.exit(1)

    try:
        if args.main:
            output_path = Path(args.output) if args.output else None
            transpile_project(input_file, output_path, args.verbose)
        else:
            cpp_code = transpile_file(input_file)
            output_file = Path(args.output) if args.output else None
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(cpp_code)
            else:
                print(cpp_code)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error transpiling: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
