from lua2c.cli.main import transpile_file
from pathlib import Path

test_file = Path("test_simple.lua")
result = transpile_file(test_file)
print(result)
