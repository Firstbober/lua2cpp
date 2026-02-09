#include "sieve_state.hpp"
#include "sieve_module.hpp"
#include <iostream>

int main(int argc, char* argv[]) {
    sieve_lua_State state;
    // Set command-line arguments
    state.arg = luaArray<luaValue>{{}};
    for (int i = 1; i < argc; ++i) {
        state.arg.set(i - 1, luaValue(argv[i]));
    }

    // Initialize library function pointers
    state.print = &l2c::print;
            state.tonumber = &l2c::tonumber;

    // Call module entry point
    luaValue result = _l2c__sieve_export(&state);

    return 0;
}
