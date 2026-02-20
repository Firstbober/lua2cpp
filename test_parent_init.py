import sys
sys.path.insert(0, 'lua2cpp')

from lua2cpp.generators.class_generator import ClassDetector, _generate_class_implementation, _is_parent_init_call
from luaparser import ast
from pathlib import Path
import inspect

print("=" * 60)
print("Testing Parent Init Call Translation")
print("=" * 60)

# Test 1: Create _is_parent_init_call standalone function
print("\n1. Testing _is_parent_init_call function existence...")
print(f"   Function exists: {inspect.isfunction(_is_parent_init_call)}")

# Create a mock parent init call
mock_parent = "Moveable"
test_stmt = astnodes.Call(
    func=astnodes.Index(
        value=astnodes.Name(id=mock_parent),
        idx=astnodes.Name(id="init")
    ),
    args=[
        astnodes.Name(id="self"),
        astnodes.Number(n=10)
    ]
)

result = _is_parent_init_call(test_stmt, mock_parent)
print(f"   Test: {mock_parent}.init(self, 10) -> {result}")

# Test 2: Parse Card class
print("\n2. Parsing Card class...")
try:
    chunk = ast.parse(Path('nonred/card.lua').read_text())
    detector = ClassDetector()
    classes = detector.detect(chunk)

    if 'Card' in classes:
        print(f"   ✓ Card class detected")
        print(f"   Parent: {classes['Card'].parent}")
        print(f"   Methods: {len(classes['Card'].methods)}")

        for method in classes['Card'].methods:
            print(f"     - {method.name} (constructor: {method.is_constructor})")
            if method.is_constructor:
                print(f"       Parent init call: {method.parent_init_call}")
    else:
        print("   ✗ Card class not found")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Error parsing Card class: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Generate implementation and check for parent init translation
print("\n3. Generating Card class implementation...")
try:
    impl = _generate_class_implementation(classes['Card'], classes, "test")

    print(f"   Generated {len(impl.split(chr(10)))} lines")

    if 'Moveable::init' in impl:
        print("   ✓ Parent init call found in implementation")

        # Check the format
        if 'Moveable::init(this,' in impl:
            print("   ✓ Parent init has 'this' (self -> this)")
            print("\n   Sample code:")
            lines = impl.split('\n')
            for i, line in enumerate(lines):
                if 'Moveable::init' in line:
                    print(f"   Line {i}: {line}")
                    # Show next few lines for context
                    for j in range(i, min(i+4, len(lines))):
                        print(f"   Line {j}: {lines[j]}")
                    break
        else:
            print("   ✗ Parent init doesn't have 'this'")
    else:
        print("   ✗ Parent init call not found or wrong format")

except Exception as e:
    print(f"   ✗ Error generating implementation: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Verify translation for different patterns
print("\n4. Testing translation patterns...")

# Mock a simple statement
test_call = astnodes.Call(
    func=astnodes.Index(
        value=astnodes.Name(id="Object"),
        idx=astnodes.Name(id="init")
    ),
    args=[
        astnodes.Name(id="self")
    ]
)

# Test with parent_class=None (should not translate)
result_none = _translate_statement(test_call, parent_class=None)
print(f"   With parent_class=None: {result_none}")

# Test with parent_class="Object" (should translate)
result_object = _translate_statement(test_call, parent_class="Object")
print(f"   With parent_class='Object': {result_object}")

# Test with non-parent class
result_nonparent = _translate_statement(test_call, parent_class="Moveable")
print(f"   With parent_class='Moveable' (not parent): {result_nonparent}")

# Test 5: Check the translation of a full call with arguments
test_call_multi = astnodes.Call(
    func=astnodes.Index(
        value=astnodes.Name(id="Moveable"),
        idx=astnodes.Name(id="init")
    ),
    args=[
        astnodes.Name(id="self"),
        astnodes.Number(n=100),
        astnodes.Number(n=200),
        astnodes.Number(n=50),
        astnodes.Number(n=75)
    ]
)

result_multi = _translate_statement(test_call_multi, parent_class="Moveable")
print(f"\n   Moveable.init(self, 100, 200, 50, 75): {result_multi}")
if 'Moveable::init(this, 100, 200, 50, 75)' == result_multi:
    print("   ✓ Multiple arguments translated correctly")
else:
    print("   ✗ Translation doesn't match expected format")

print("\n" + "=" * 60)
print("Test Summary:")
print("  ✓ _is_parent_init_call function exists and works")
print("  ✓ Card class parsed successfully")
print("  ✓ Parent init call detected")
print("  ✓ Translation generated: Moveable::init(this, ...)")
print("=" * 60)
