#include "lua_state.hpp"
#include "lua_value.hpp"
#include <iostream>

// Forward declarations for generated modules
luaValue _l2c__scimark_export(luaState* state);

int main(int argc, char* argv[]) {
    std::cout << "Testing transpiled scimark.lua..." << std::endl;

    // Create Lua state
    luaState state;

    // Set command line arguments (Lua's arg table)
    // Note: We skip argv[0] (program name) as Lua's arg[1] is the first script argument
    std::vector<luaValue> args;
    for (int i = 1; i < argc; ++i) {
        args.push_back(luaValue(argv[i]));
    }
    state.set_arg(args);

    // No default arguments needed

    // Call the transpiled scimark.lua module
    luaValue result = _l2c__scimark_export(&state);

    std::cout << "Test completed!" << std::endl;
    return 0;
}
