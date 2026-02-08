#include "../runtime/l2c_runtime.hpp"
#include <iostream>
#include <string>

using namespace l2c;

int main() {
    std::cout << "=== to_string tests ===" << std::endl;
    std::cout << "to_string(42): " << to_string(42) << std::endl;
    std::cout << "to_string(3.14): " << to_string(3.14) << std::endl;
    std::cout << "to_string(true): " << to_string(true) << std::endl;
    std::cout << "to_string('x'): " << to_string('x') << std::endl;

    std::cout << "\n=== to_number tests ===" << std::endl;
    std::cout << "to_number(42): " << to_number(42) << std::endl;
    std::cout << "to_number(3.14): " << to_number(3.14) << std::endl;

    std::cout << "\n=== print() tests ===" << std::endl;
    std::cout << "Testing single argument:" << std::endl;
    print(42);

    std::cout << "Testing multiple arguments:" << std::endl;
    print(42, 3.14, true, 'x');

    std::cout << "Testing string arguments:" << std::endl;
    print("Hello", "World");

    std::cout << "Testing mixed arguments:" << std::endl;
    print("Value:", 42, "Pi:", 3.14);

    std::cout << "\n=== All tests completed successfully ===" << std::endl;

    return 0;
}
