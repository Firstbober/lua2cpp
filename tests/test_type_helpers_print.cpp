#include "../runtime/lua_value.hpp"
#include "../runtime/l2c_runtime.hpp"
#include <iostream>
#include <vector>

void test_variadic_print_single() {
    std::cout << "Test 1: Single argument\n";
    l2c::print("Hello");
    std::cout << "Expected: Hello\\n\n\n";
}

void test_variadic_print_multiple() {
    std::cout << "Test 2: Multiple arguments\n";
    l2c::print("Hello", "World", 42, 3.14);
    std::cout << "Expected: Hello\\tWorld\\t42\\t3.14\\n\n";
}

void test_variadic_print_numbers() {
    std::cout << "Test 3: Numbers\n";
    l2c::print(1, 2, 3, 4, 5);
    std::cout << "Expected: 1\\t2\\t3\\t4\\t5\\n\n";
}

void test_variadic_print_mixed() {
    std::cout << "Test 4: Mixed types\n";
    l2c::print("Text", 123, "More", 4.56);
    std::cout << "Expected: Text\\t123\\tMore\\t4.56\\n\n";
}

int main() {
    std::cout << "=== Testing l2c::print() function ===\n\n";

    test_variadic_print_single();
    test_variadic_print_multiple();
    test_variadic_print_numbers();
    test_variadic_print_mixed();

    std::cout << "=== All tests completed ===\n";
    return 0;
}
