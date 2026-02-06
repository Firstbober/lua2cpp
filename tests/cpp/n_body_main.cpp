#include "lua_state.hpp"
#include "lua_value.hpp"
#include <iostream>

// Forward declarations for generated modules
luaValue _l2c__n_body_export(luaState* state);

int main(int argc, char* argv[]) {
    std::cout << "Testing transpiled n-body.lua..." << std::endl;

    // Create Lua state
    luaState state;

    // Set command line arguments (Lua's arg table)
    // Note: We skip argv[0] (program name) as Lua's arg[1] is the first script argument
    std::vector<luaValue> args;
    for (int i = 1; i < argc; ++i) {
        args.push_back(luaValue(argv[i]));
    }
    state.set_arg(args);

    // Set default for arg[1]
    if (argc <= 1) {
        args.push_back(luaValue(1000));
        state.set_arg(args);
    }

    // Call the transpiled n-body.lua module
    luaValue result = _l2c__n_body_export(&state);

    std::cout << "Test completed!" << std::endl;
    return 0;
}
