import sys
sys.path.insert(0, 'lua2cpp')

from luaparser import ast

# Check If node structure
code = "if x > 0 then print(x) else print(y) end"
chunk = ast.parse(code)
for stmt in chunk.body.body:
    print(f"Type: {type(stmt).__name__}")
    print(f"  test: {type(stmt.test)}")
    print(f"  body: {type(stmt.body)}")
    print(f"  body.body: {type(stmt.body.body)}")
    print(f"  orelse: {type(stmt.orelse)}")
    print(f"  orelse.body: {type(stmt.orelse.body)}")
    if hasattr(stmt.body.body, '__iter__'):
        print(f"  body.body is iterable: {hasattr(stmt.body.body, '__iter__')}")
    if hasattr(stmt.orelse.body, '__iter__'):
        print(f"  orelse.body is iterable: {hasattr(stmt.orelse.body, '__iter__')}")
