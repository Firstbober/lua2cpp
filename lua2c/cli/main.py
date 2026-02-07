"""Main CLI entry point for Lua2C++ transpiler"""

import sys
import argparse
import traceback
from pathlib import Path
from typing import List, Set, Optional, Dict

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
    """Transpile a single Lua file to C++ (legacy mode, DEPRECATED)

    Args:
        input_file: Path to Lua source file

    Returns:
        Generated C++ code

    Note: This is deprecated. Use transpile_single_file() instead.
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


def _collect_globals_from_tree(tree) -> Set[str]:
    """Collect global variable names from AST

    Args:
        tree: Parsed Lua AST

    Returns:
        Set of global variable names
    """
    from luaparser import astnodes

    globals = set()

    def visit(node):
        if isinstance(node, astnodes.Name):
            globals.add(node.id)
        elif hasattr(node, 'body'):
            for child in (node.body if isinstance(node.body, list) else [node.body]):
                visit(child)
        elif hasattr(node, 'left'):
            visit(node.left)
        elif hasattr(node, 'right'):
            visit(node.right)
        elif hasattr(node, 'expr'):
            visit(node.expr)
        elif hasattr(node, 'init'):
            visit(node.init)
        elif hasattr(node, 'value'):
            visit(node.value)
        elif hasattr(node, 'args'):
            for arg in node.args:
                visit(arg)
        elif hasattr(node, 'idx'):
            visit(node.idx)
            visit(node.value)
        elif hasattr(node, 'operand'):
            visit(node.operand)
        elif hasattr(node, 'test'):
            visit(node.test)
        elif hasattr(node, 'orelse'):
            orelse = node.orelse
            if orelse:
                for child in (orelse if isinstance(orelse, list) else [orelse]):
                    visit(child)

    visit(tree)
    return globals


def _collect_used_libraries(tree) -> Set[str]:
    """Collect used standard libraries from AST

    Args:
        tree: Parsed Lua AST

    Returns:
        Set of library module names (io, math, string, table, os)
    """
    from luaparser import astnodes

    libraries = set()
    known_libs = {'io', 'math', 'string', 'table', 'os'}
    standalone_funcs = {'print', 'tonumber'}

    def check_node(node):
        if isinstance(node, astnodes.Index):
            if isinstance(node.value, astnodes.Name):
                if node.value.id in known_libs:
                    libraries.add(node.value.id)
        elif isinstance(node, astnodes.Call):
            # Check for library.function() calls
            if isinstance(node.func, astnodes.Index):
                if isinstance(node.func.value, astnodes.Name):
                    if node.func.value.id in known_libs:
                        libraries.add(node.func.value.id)
            # Check for standalone functions (print, tonumber)
            elif isinstance(node.func, astnodes.Name):
                if node.func.id in standalone_funcs:
                    libraries.add('print') if node.func.id == 'print' else None
                    # tonumber is handled separately as a standalone function

    # Simple BFS traversal to avoid recursion issues
    nodes_to_visit = [tree]
    while nodes_to_visit:
        node = nodes_to_visit.pop(0)
        check_node(node)

        # Add children to visit
        for attr in ['left', 'right', 'value', 'expr', 'init', 'body']:
            child = getattr(node, attr, None)
            if child is not None:
                if isinstance(child, list):
                    nodes_to_visit.extend(child)
                else:
                    nodes_to_visit.append(child)

        # Handle Call args
        if hasattr(node, 'args'):
            nodes_to_visit.extend(node.args)

        # Handle if/while/etc. bodies
        if hasattr(node, 'elsebody'):
            nodes_to_visit.append(node.elsebody)

    return libraries


def transpile_single_file(
    input_file: Path,
    output_name: Optional[str] = None,
    as_library: bool = False,
    output_dir: Optional[Path] = None
) -> Dict[str, Optional[str]]:
    """Transpile single Lua file with custom state

    Args:
        input_file: Input Lua file path
        output_name: Custom name for output files (default: input filename)
        as_library: If True, generate as library (no main.cpp, no arg member)
        output_dir: Output directory (default: current directory)

    Returns:
        Dict with keys: 'state_hpp', 'module_hpp', 'module_cpp', 'main_cpp'
        main_cpp is None if as_library=True

    Raises:
        FileNotFoundError: If input_file doesn't exist
        Exception: If transpilation fails (with full stack trace)
    """
    import traceback

    # Validate input
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Parse source
    with open(input_file, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except Exception as e:
        print(f"Error parsing {input_file}:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    # Determine module name
    if output_name:
        module_name = output_name
    else:
        module_name = input_file.stem

    # Setup context
    context = TranslationContext(input_file.parent, str(input_file.parent))
    context.set_single_file_mode(module_name, as_library=as_library)

    # Generate module cpp and header
    emitter = CppEmitter(context)
    try:
        result = emitter.generate_file(tree, input_file, generate_header=True)
        if isinstance(result, tuple):
            module_cpp, module_hpp = result
        else:
            # Backward compatibility: if only module_cpp returned
            module_cpp = result
            # Generate header separately
            state_type = f"{module_name}_lua_State"
            from lua2c.generators.header_generator import HeaderGenerator
            header_gen = HeaderGenerator()
            module_hpp = header_gen.generate_module_header(module_name, state_type)
    except Exception as e:
        print(f"Error generating C++ from {input_file}:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    # Collect globals and used libraries
    globals = _collect_globals_from_tree(tree)
    used_libs = _collect_used_libraries(tree)
    
    # Manual check: if source contains 'arg', add to globals
    if 'arg' in source:
        globals.add('arg')

    # Generate state header
    state_gen = ProjectStateGenerator(module_name)
    state_hpp = state_gen.generate_state_class(
        globals=globals,
        modules=set(),
        library_modules=used_libs,
        include_module_registry=False,
        include_arg=not as_library,
    )

    # Generate main (if not library mode)
    main_cpp = None
    if not as_library:
        main_gen = MainGenerator()
        main_cpp = main_gen.generate_standalone_main(
            module_name=module_name,
            used_libraries=used_libs,
            globals=globals,
        )

    return {
        'state_hpp': state_hpp,
        'module_hpp': module_hpp,
        'module_cpp': module_cpp,
        'main_cpp': main_cpp,
    }


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
        description='Lua2C Transpiler - Convert Lua to C++',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standalone executable mode (default)
  lua2c input.lua
  lua2c input.lua -o myapp
  lua2c input.lua --output-dir build/

  # Library mode (embeddable)
  lua2c input.lua --lib
  lua2c input.lua --lib -o mymodule

  # Project mode (multi-file)
  lua2c --main path/to/main.lua
  lua2c --main path/to/main.lua --output-dir build/
        """
    )

    parser.add_argument('input', type=Path, help='Input Lua file')
    parser.add_argument(
        '--lib', action='store_true',
        help='Generate as library (no main.cpp, no arg member)'
    )
    parser.add_argument(
        '-o', '--output', type=str,
        help='Custom output name (default: input filename)'
    )
    parser.add_argument(
        '--output-dir', type=Path, default=Path.cwd(),
        help='Output directory (default: current directory)'
    )
    parser.add_argument(
        '--main', action='store_true',
        help='Treat input as project main file (transpile all modules)'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Validate input file
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    # Create output directory if needed
    output_dir = args.output_dir
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error: Cannot create output directory {output_dir}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.main:
            # Project mode
            output_path = Path(args.output) if args.output else None
            transpile_project(input_file, output_path, args.verbose)
        else:
            # Single-file mode
            output_name = args.output if args.output else input_file.stem
            results = transpile_single_file(
                input_file=input_file,
                output_name=output_name,
                as_library=args.lib,
                output_dir=output_dir,
            )

            # Determine base filename for output files
            base_name = output_dir / output_name

            # Write state header
            state_file = base_name.with_name(f"{output_name}_state.hpp")
            state_file.write_text(results['state_hpp'])
            print(f"Generated: {state_file}")

            # Write module header
            module_hpp_file = base_name.with_name(f"{output_name}_module.hpp")
            module_hpp_file.write_text(results['module_hpp'])
            print(f"Generated: {module_hpp_file}")

            # Write module cpp
            module_cpp_file = base_name.with_name(f"{output_name}_module.cpp")
            module_cpp_file.write_text(results['module_cpp'])
            print(f"Generated: {module_cpp_file}")

            # Write main (if not library mode)
            if results['main_cpp']:
                main_file = base_name.with_name(f"{output_name}_main.cpp")
                main_file.write_text(results['main_cpp'])
                print(f"Generated: {main_file}")

                # Print compilation instructions
                print(f"\nTo compile, use:")
                print(f"  g++ -std=c++17 -I runtime {output_name}_main.cpp {output_name}_module.cpp runtime/lua_value.cpp runtime/lua_array.cpp runtime/lua_table.cpp -o {output_name}")
            else:
                # Library mode usage instructions
                print(f"\nTo use as library, include:")
                print(f"  #include \"{output_name}_state.hpp\"")
                print(f"  #include \"{output_name}_module.hpp\"")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"Error transpiling {input_file}:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
