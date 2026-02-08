#include "ack_state.hpp"
#include "ack_module.hpp"
#include <iostream>

int main(int argc, char* argv[]) {
    ack_lua_State state;
    state.arg = luaArray<luaValue>{{}};
    for (int i = 1; i < argc; ++i) {
        state.arg.set(i - 1, luaValue(argv[i]));
    }

    state.print = &l2c::print;
    state.tonumber = &l2c::tonumber;
    state.string.format = &l2c::string_format;

    luaValue result = _l2c__ack_export(&state);

    return 0;
}
