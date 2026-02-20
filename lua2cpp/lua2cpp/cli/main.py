"""Main CLI entry point for Lua2C++ transpiler"""

import sys
import argparse
import re
import traceback
from pathlib import Path
from typing import List, Set, Optional, Dict, Tuple, Any

try:
    from luaparser import ast
    from luaparser.ast import SyntaxException
except ImportError:
    print("Error: luaparser is required. Install with: pip install luaparser", file=sys.stderr)
    sys.exit(1)

from lua2cpp.generators import CppEmitter
from lua2cpp.generators.header_generator import HeaderGenerator
from .core.library_call_collector import LibraryCallCollector, LibraryCallCollector as Collector
from .analyzers.y_combinator_detector import YCombinatorDetector
from .core.call_convention import CallConventionRegistry


def transpile_file(input_file: Path, collect_library_calls: bool = False, output_dir: Optional[Path] = None, verbose: bool = False, convention_registry: Optional[CallConventionRegistry] = None) -> Tuple[str, List, Optional[Collector], Any]:
    """Transpile a single Lua file to C++

    Args:
        input_file: Path to Lua source file
        collect_library_calls: If True, also collect library calls for header generation
        output_dir: Optional output directory for generated files
        verbose: If True, print verbose file generation details
        convention_registry: Optional registry for call conventions

    Returns:
        Tuple of (generated C++ code, list of LibraryCall objects if collect_library_calls=True else [], emitter)

    Raises:
        FileNotFoundError: If input_file doesn't exist
        PermissionError: If input_file cannot be read
        SyntaxException: If Lua source has invalid syntax
        Exception: If code generation fails
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            source = f.read()
    except PermissionError as e:
        raise PermissionError(f"Cannot read input file {input_file}: {e}")

    try:
        tree = ast.parse(source)
    except SyntaxException as e:
        raise SyntaxException(f"Invalid Lua syntax in {input_file}: {e}")

    source_lines = source.split('\n')

    y_detector = YCombinatorDetector(source_lines)
    y_detector.visit(tree)
    y_warnings = y_detector.get_warnings()

    for w in y_warnings:
        print(f"Warning: {w.message}", file=sys.stderr)
        print(f"  at {input_file}:{w.line_start}", file=sys.stderr)
        if w.source_snippet:
            print(f"  source: {w.source_snippet.strip()}", file=sys.stderr)

    collector = None
    library_calls = []
    if collect_library_calls:
        collector = LibraryCallCollector()
        collector.visit(tree)
        library_calls = collector.get_library_calls()

    emitter = CppEmitter(convention_registry=convention_registry)
    cpp_code = emitter.generate_file(tree, input_file)

    if y_warnings:
        warning_block = "// WARNING: Y-combinator patterns detected that may not compile in C++17:\n"
        for w in y_warnings:
            warning_block += f"//   Line {w.line_start}: {w.source_snippet.strip() if w.source_snippet else '(unknown)'}\n"
        warning_block += "// These patterns use self-application (f(f)) which creates circular type dependencies.\n"
        "// Consider rewriting using explicit recursion or std::function wrappers.\n"
        cpp_code = warning_block + cpp_code

    return cpp_code, library_calls, collector, emitter


def extract_function_signatures(cpp_code: str) -> List[str]:
    """Extract function signatures from generated C++ code using regex.

    Simple approach: extract function definitions and convert to forward declarations.
    Pattern: return_type function_name(params) { ... }

    Args:
        cpp_code: Generated C++ source code

    Returns:
        List of function signatures (return_type function_name(params))
    """
    signatures = []

    # Pattern to match function definitions
    # Matches: return_type function_name(params) {
    # Excludes: static functions (not exported), comments, preprocessor directives
    pattern = r'^([a-zA-Z_][a-zA-Z0-9_<>:*&\s]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*\{'

    for line in cpp_code.split('\n'):
        line = line.strip()

        # Skip empty lines, comments, and preprocessor directives
        if not line or line.startswith('//') or line.startswith('/*') or line.startswith('#'):
            continue

        # Skip static functions (not exported)
        if 'static' in line:
            continue

        match = re.match(pattern, line)
        if match:
            return_type = match.group(1).strip()
            func_name = match.group(2).strip()
            params = match.group(3).strip()

            # Detect template parameters (T1, T2, etc.) in the function signature
            # This handles: auto func(T1&& x) -> template<typename T1> auto func(T1&& x)
            template_params = []
            if params:
                # Match template type parameters like T1, T2, T3, etc.
                template_param_pattern = r'\b([A-Z]\d+)\b'
                template_param_matches = re.findall(template_param_pattern, params)
                if template_param_matches:
                    # Extract unique template parameters
                    template_params = list(set(template_param_matches))
                    # Sort them to ensure consistent ordering
                    template_params.sort()

            # Build the signature with or without template prefix
            if template_params:
                # Add template declaration: template<typename T1, typename T2, ...>
                template_prefix = f"template<{', '.join([f'typename {tp}' for tp in template_params])}>"
                signature = f"{template_prefix} {return_type} {func_name}({params})"
            else:
                signature = f"{return_type} {func_name}({params})"

            signatures.append(signature)

    return signatures


def generate_lib_header(cpp_code: str, module_name: str, has_g_table: bool = False) -> str:
    """Generate .hpp header file with forward declarations.

    Args:
        cpp_code: Generated C++ source code
        module_name: Name of the module (input filename stem)
        has_g_table: Whether this module uses the G table

    Returns:
        Header file content with forward declarations
    """
    signatures = extract_function_signatures(cpp_code)

    header_lines = [
        f'// Auto-generated header for {module_name}',
        f'// Generated by lua2cpp',
        '',
        '#pragma once',
        '',
        '#include "../runtime/globals.hpp"',
        '',
    ]

    for sig in signatures:
        header_lines.append(f'{sig};')

    # Add extern TABLE G; declaration if G is used
    if has_g_table:
        header_lines.append('')
        header_lines.append('extern TABLE G;')

    header_lines.append('')

    return '\n'.join(header_lines)


def main():
    """Main entry point for the CLI."""
    emitter = None
    parser = argparse.ArgumentParser(
        description="Transpile Lua 5.4 source code to C++"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input Lua file to transpile"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output C++ file"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Output directory for generated files"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print verbose file generation details"
    )
    parser.add_argument(
        "--header",
        action="store_true",
        help="Generate state.h header file with library API declarations"
    )
    parser.add_argument(
        "--lib",
        action="store_true",
        help="Generate as library (output {input_name}.hpp with forward declarations)"
    )
    parser.add_argument(
        "--convention",
        action="append",
        default=[],
        metavar="MODULE=STYLE",
        help="Set call convention for a module (e.g., love=flat_nested,G=flat). Styles: namespace, flat, flat_nested, table"
    )
    parser.add_argument(
        "--convention-file",
        type=Path,
        help="Load call conventions from YAML config file"
    )

    args = parser.parse_args()

    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        print(f"Error: Permission denied when creating output directory {args.output_dir}: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error: Cannot create output directory {args.output_dir}: {e}", file=sys.stderr)
        sys.exit(1)

    # Create and configure call convention registry
    convention_registry = CallConventionRegistry()
    
    # Load from YAML file if specified
    if args.convention_file:
        convention_registry.load_from_yaml(args.convention_file)
    
    # Load from CLI arguments
    if args.convention:
        convention_registry.load_from_cli(args.convention)

    try:
        cpp_code, library_calls, collector, emitter = transpile_file(
            args.input,
            collect_library_calls=args.header,
            output_dir=args.output_dir,
            verbose=args.verbose,
            convention_registry=convention_registry
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except SyntaxException as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error transpiling {args.input}:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    if args.output:
        output_file = args.output_dir / args.output
    else:
        output_file = args.output_dir / f"{args.input.stem}.cpp"

    if args.verbose:
        print(f"Transpiling: {args.input} → {output_file}")

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cpp_code)
    except PermissionError as e:
        print(f"Error: Permission denied when writing to {output_file}: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error writing output file {output_file}: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    print(f"Generated: {output_file}")

    if args.lib:
        try:
            hpp_content = generate_lib_header(cpp_code, args.input.stem, emitter._has_g_table)
            hpp_file = output_file.parent / f"{args.input.stem}.hpp"
            with open(hpp_file, 'w', encoding='utf-8') as f:
                f.write(hpp_content)
            print(f"Generated: {hpp_file}")
        except Exception as e:
            print(f"Error generating library header file: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)

    # Restore original return value for back-compatibility
    return cpp_code, library_calls, collector

    if args.header:
        try:
            header_gen = HeaderGenerator()
            global_functions = set()
            if collector:
                for call in collector.get_global_calls():
                    global_functions.add(call.func)
            # Add get_length manually - it's used by # operator but not tracked as a function call
            global_functions.add("get_length")
            state_h_content = header_gen.generate_header(library_calls, global_functions)

            state_h_path = output_file.parent / "state.h"
            with open(state_h_path, 'w', encoding='utf-8') as f:
                f.write(state_h_content)

            print(f"Generated: {state_h_path}")
        except Exception as e:
            print(f"Error generating header file: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
