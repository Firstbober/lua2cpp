#include "l2c_runtime.hpp"
#include "comparisons_state.hpp"
#include "comparisons_module.hpp"
#include <iostream>

int main() {
    std::cout << "Testing transpiled comparisons.lua..." << std::endl;

    // Create custom state
    comparisons_lua_State state;

    // Initialize library function pointers
    state.print = &l2c::print;
    state.tonumber = &l2c::tonumber;

    // Call the transpiled comparisons.lua module
    std::cout << "\nRunning comparisons.lua..." << std::endl;
    luaValue result = _l2c__comparisons_export(&state);

    std::cout << "\nTest completed successfully!" << std::endl;
    return 0;
}
