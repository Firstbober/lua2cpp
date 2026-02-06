"""Main CLI entry point for Lua2C transpiler"""

import sys
from pathlib import Path

try:
    from luaparser import ast
except ImportError:
    print("Error: luaparser is required. Install with: pip install luaparser")
    sys.exit(1)

from lua2c.core.context import TranslationContext
from lua2c.generators.expr_generator import ExprGenerator
from lua2c.generators.stmt_generator import StmtGenerator


def transpile_file(input_file: Path) -> str:
    """Transpile a single Lua file to C

    Args:
        input_file: Path to Lua source file

    Returns:
        Generated C code
    """
    # Read Lua source
    with open(input_file, 'r', encoding='utf-8') as f:
        source = f.read()

    # Parse AST
    tree = ast.parse(source)

    # Create translation context
    try:
        rel_path = input_file.relative_to(Path.cwd())
    except ValueError:
        rel_path = input_file
    module_path = str(rel_path.parent) if hasattr(rel_path, 'parent') else str(rel_path)
    context = TranslationContext(Path.cwd(), module_path)

    # Generate code
    stmt_gen = StmtGenerator(context)

    code_lines = [
        f"// Auto-generated from {input_file}",
        f"// Lua2C Transpiler",
        "",
        "#include \"lua_value.h\"",
        "#include \"lua_state.h\"",
        "",
    ]

    # Generate all statements
    for stmt in tree.body.body:
        stmt_code = stmt_gen.generate(stmt)
        code_lines.append(stmt_code)

    return "\n".join(code_lines)


def main() -> None:
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m lua2c.cli.main <input_file.lua>")
        sys.exit(1)

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    try:
        c_code = transpile_file(input_file)
        print(c_code)
    except Exception as e:
        print(f"Error transpiling {input_file}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
