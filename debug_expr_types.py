from luaparser import ast
from pathlib import Path
from lua2c.core.context import TranslationContext
from lua2c.analyzers.type_inference import TypeInference
from lua2c.core.type_system import TypeKind

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

# Check expression types
print("\nChecking expression types in second assignment:")
assign2 = tree.body.body[1]
print(f"  Assignment: {assign2}")
print(f"  Value type: {type(assign2.values[0])}")
if hasattr(assign2.values[0], 'left'):
    print(f"  Left: {assign2.values[0].left}")
    print(f"  Right: {assign2.values[0].right}")
    left_type = type_inferencer._get_expression_type(assign2.values[0].left)
    right_type = type_inferencer._get_expression_type(assign2.values[0].right)
    result_type = type_inferencer._get_expression_type(assign2.values[0])
    print(f"  Left type: {left_type}")
    print(f"  Right type: {right_type}")
    print(f"  Result type: {result_type}")
