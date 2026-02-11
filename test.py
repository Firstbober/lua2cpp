from luaparser import ast
from lua2cpp.generators.cpp_emitter import CppEmitter
from pathlib import Path
# Read Lua file
with open('tests/cpp/lua/spectral-norm.lua', 'r') as f:
    lua_code = f.read()
# Parse and transpile
chunk = ast.parse(lua_code)
emitter = CppEmitter()
cpp_code = emitter.generate_file(chunk, input_file=Path('spectral-norm.lua'))
# Write C++ output
print(cpp_code)