#include "l2c_runtime.hpp"
#include "test_func_state.hpp"
#include "test_func_module.hpp"
#include <iostream>

int main() {
    std::cout << "Testing transpiled test_func.lua..." << std::endl;

    // Create custom state
    test_func_lua_State state;

    // Initialize library function pointers
    state.print = &l2c::print;
    state.tonumber = &l2c::tonumber;

    // Call the transpiled test_func.lua module
    std::cout << "\nRunning test_func.lua..." << std::endl;
    luaValue result = _l2c__test_func_export(&state);

    std::cout << "\nTest completed successfully!" << std::endl;
    return 0;
}
