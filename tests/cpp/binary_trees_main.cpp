#include "binary_trees_state.hpp"
#include "binary_trees_module.hpp"
#include <iostream>

int main(int argc, char* argv[]) {
    binary_trees_lua_State state;
    state.arg = luaArray<luaValue>{{}};
    for (int i = 1; i < argc; ++i) {
        state.arg.set(i - 1, luaValue(argv[i]));
    }

    state.print = &l2c::print;
    state.tonumber = &l2c::tonumber;
    state.string.format = &l2c::string_format;

    luaValue result = _l2c__binary_trees_export(&state);

    return 0;
}
