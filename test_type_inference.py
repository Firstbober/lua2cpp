from luaparser import ast
from pathlib import Path
from lua2c.core.context import TranslationContext
from lua2c.analyzers.type_inference import TypeInference

lua_code = """
local x = 5
local y = x + 3
"""

tree = ast.parse(lua_code)
context = TranslationContext(Path("."), "test")

# Run type inference
type_inferencer = TypeInference(context)
type_inferencer.infer_chunk(tree)

# Print inferred types
print("Inferred types:")
for symbol_name, type_info in type_inferencer.inferred_types.items():
    print(f"  {symbol_name}: {type_info}")
