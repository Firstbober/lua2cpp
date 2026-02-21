#include <iostream>
#include <string>

using namespace l2c::detail;

int main() {
    std::cout << "Test 1: Basic multi-arg formatting" << std::endl;
    auto result1 = string_format("a=%d b=%d c=%d\n", 1, 2, 3);
    std::cout << "Result: " << result1.toString() << std::endl;
    std::cout << "Expected: a=1 b=2 c=3\n" << std::endl;

    std::cout << "Test 2: binary-trees.lua test case" << std::endl;
    auto result2 = string_format("%d\t trees of depth %d\t check: %d\n", 2048, 4, -2048);
    std::cout << "Result: " << result2.toString() << std::endl;
    std::cout << "Expected: 2048\t trees of depth 4\t check: -2048\n" << std::endl;

    std::cout << "Test 3: Single format specifier (should still work)" << std::endl;
    auto result3 = string_format("%d trees of depth %d\n", 100, 5);
    std::cout << "Result: " << result3.toString() << std::endl;
    std::cout << "Expected: 100 trees of depth 5\n" << std::endl;

    std::cout << "Test 4: Floats (should be converted to int via tonumber)" << std::endl;
    auto result4 = string_format("%d trees of depth %d\n", 2048.0, 4.0);
    std::cout << "Result: " << result4.toString() << std::endl;
    std::cout << "Expected: 2048 trees of depth 4\n" << std::endl;

    return 0;
}
