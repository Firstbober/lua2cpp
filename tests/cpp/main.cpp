#include "lua_state.hpp"
#include "lua_value.hpp"
#include <iostream>

// Forward declarations for generated modules
luaValue _l2c__simple_export(luaState* state);

int main() {
    std::cout << "Testing transpiled Lua code..." << std::endl;

    // Create Lua state
    luaState state;

    // Call the transpiled simple.lua module
    std::cout << "\nRunning simple.lua..." << std::endl;
    luaValue result = _l2c__simple_export(&state);

    std::cout << "\nTest completed successfully!" << std::endl;
    return 0;
}
