import sys
sys.path.insert(0, 'lua2cpp')

from lua2cpp.generators.class_generator import ClassDetector, _generate_class_implementation
from luaparser import ast
from pathlib import Path

chunk = ast.parse(Path('nonred/card.lua').read_text())
detector = ClassDetector()
classes = detector.detect(chunk)

if 'Card' in classes:
    impl = _generate_class_implementation(classes['Card'], classes, "test")
    print("SUCCESS: Card.cpp generated")
    print(f"Lines: {len(impl.split(chr(10)))}")
    print("\n--- Generated Card.cpp ---")
    print(impl)
else:
    print("ERROR: Card class not detected")
    print(f"Detected classes: {list(classes.keys())}")
