#include "l2c_runtime.hpp"
#include "test_array_state.hpp"
#include "test_array_module.hpp"
#include <iostream>

int main() {
    std::cout << "Testing transpiled test_array.lua..." << std::endl;

    // Create custom state
    test_array_lua_State state;

    // Initialize library function pointers
    state.print = &l2c::print;
    state.tonumber = &l2c::tonumber;

    // Call the transpiled test_array.lua module
    std::cout << "\nRunning test_array.lua..." << std::endl;
    luaValue result = _l2c__test_array_export(&state);

    std::cout << "\nTest completed successfully!" << std::endl;
    return 0;
}
