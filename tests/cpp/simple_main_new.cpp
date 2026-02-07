#include "l2c_runtime.hpp"
#include "simple_state.hpp"
#include "simple_module.hpp"
#include <iostream>

int main() {
    std::cout << "Testing transpiled simple.lua..." << std::endl;

    // Create custom state
    simple_lua_State state;

    // Initialize library function pointers
    state.print = &l2c::print;
    state.tonumber = &l2c::tonumber;

    // Call the transpiled simple.lua module
    std::cout << "\nRunning simple.lua..." << std::endl;
    luaValue result = _l2c__simple_export(&state);

    std::cout << "\nTest completed successfully!" << std::endl;
    return 0;
}
