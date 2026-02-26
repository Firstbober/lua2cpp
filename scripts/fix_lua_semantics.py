#!/usr/bin/env python3
"""
Post-process generated C++ to fix Lua semantics inspired patterns:
- Add variadic overloads for template functions called with extra args
- Wrap template-function arguments with lambdas when passed as args
- Mark fixed blocks to avoid double-processing

Usage:
  python scripts/fix_lua_semantics.py path/to/file.cpp
"""

import re
import sys
from pathlib import Path


def parse_param_names(param_list: str):
    """Return (param_decls, param_names) from a comma-separated list.
    param_decls: list of declarations as written in the function signature
    param_names: corresponding parameter names to be used when calling
    """
    decls = []
    names = []
    s = param_list.strip()
    if not s:
        return decls, names
    parts = [p.strip() for p in s.split(',') if p.strip()]
    for part in parts:
        # last token is assumed to be the parameter name
        toks = part.split()
        if not toks:
            continue
        name = toks[-1]
        names.append(name)
        # keep full declaration as-is
        decls.append(part)
    return decls, names


def find_template_functions(code: str):
    """Yield tuples for template function definitions:
    (start_idx, end_idx, name, ret_type, template_params, param_decls, param_names)
    """
    # Multiline template function header, e.g.:
    # template<typename q_t>
    # TABLE color(q_t q) { ...
    pattern = re.compile(
        r"template\s*<(?P<params>[^>]+)>\s*"  # template params
        r"(?P<ret>[A-Za-z_][\w:\<\>\s&*]*?)\s+"  # return type
        r"(?P<name>\w+)\s*"  # function name
        r"\((?P<args>[^\)]*)\)\s*\{",  # parameter list and opening brace
        re.MULTILINE | re.DOTALL,
    )
    for m in pattern.finditer(code):
        name = m.group('name')
        ret_type = m.group('ret').strip()
        template_params = m.group('params').strip()
        args = m.group('args').strip()
        decls, names = parse_param_names(args)
        # Determine the start (position of 'template...') and end of function body
        # We locate the opening brace position and then balance braces to find end.
        # Find the position of the opening brace following the match
        brace_pos = code.find('{', m.end() - 1)
        if brace_pos == -1:
            continue
        depth = 0
        end_pos = brace_pos
        i = brace_pos
        while i < len(code):
            ch = code[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end_pos = i
                    break
            i += 1
        else:
            continue
        yield (m.start(), end_pos + 1, name, ret_type, template_params, decls, names,)


def build_variadic_overload(code: str, func_start: int, func_end: int, name: str,
                          ret_type: str, template_params: str, param_decls: list, param_names: list):
    if not param_decls:
        # no parameters to overload; skip
        return None
    # Check for existing override marker after the function end to avoid duplicates
    marker = f"fix_lua_semantics: variadic overload added for {name}"
    post = code[func_end:func_end+500]
    if marker in post:
        return None
    template_decl = f"template<{template_params}, typename... Unused>"
    overload = (
        "\n\n" + template_decl + "\n" + f"{ret_type} {name}({', '.join(param_decls)}, Unused&&...) {{\n"
        f"    return {name}({', '.join(param_names)});\n"
        "}\n"
    )
    # append marker as a comment to avoid re-processing in future runs
    overload = overload + f"// fix_lua_semantics: variadic overload added for {name}"
    return overload


def wrap_template_as_lambda(code: str, do_match_start: int, do_match_end: int, func_name: str):
    # Return the replacement snippet for the detected do_(<name>, "<name>") pattern
    # and mark to avoid double-wrapping by the caller.
    # In this simplified approach we just construct the lambda-wrapped call.
    replacement = f'do_([&](auto&&... args) {{ return {func_name}(args...); }}, "{func_name}")'
    marker = f"fix_lua_semantics: lambda-wrapped {func_name}"
    if marker in code[do_match_start:do_match_end]:
        return None
    return replacement


def fix(code: str) -> str:
    # First pass: handle variadic overloads after template function definitions
    inserts = []  # tuples of (position, text)
    fixed_names = set()
    for item in find_template_functions(code):
        start, end, name, ret_type, template_params, decls, names = item
        if name in fixed_names:
            continue
        # Build overload
        overload = build_variadic_overload(code, start, end, name, ret_type, template_params, decls, names)
        if overload:
            inserts.append((end, overload))
            fixed_names.add(name)

    # Apply variadic overload inserts in reverse order to not corrupt indices
    if inserts:
        inserts.sort(key=lambda x: x[0], reverse=True)
        for pos, snippet in inserts:
            code = code[:pos] + snippet + code[pos:]

    # Second pass: wrap template functions used as arguments (pattern: do_(NAME, "NAME"))
    # We replace occurrences with a lambda wrapper, and add a trailing marker comment.
    # Avoid multiple wrappings by simple in-place marker check.
    lambda_pattern = re.compile(r"do_\(\s*(?P<name>\w+)\s*,\s*\"(?P<quoted>[^\"]+)\"\s*\)")
    def repl_lam(m):
        name = m.group('name')
        # if already wrapped, skip
        after = code[m.end():m.end()+1]
        # crude check: if the preceding text contains '[' then assume already wrapped; keep simple
        if code[m.start():m.end()].find('[') != -1:
            return m.group(0)
        new = f'do_([&](auto&&... args) {{ return {name}(args...); }}, "{name}")'
        return new
    code = lambda_pattern.sub(repl_lam, code)

    return code


def main():
    if len(sys.argv) != 2:
        print("Usage: fix_lua_semantics.py <path-to-cpp-file>")
        sys.exit(2)
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"File not found: {p}")
        sys.exit(2)
    code = p.read_text(encoding='utf-8')
    fixed = fix(code)
    print(fixed, end='')


if __name__ == "__main__":
    main()
