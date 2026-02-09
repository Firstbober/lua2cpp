#include "heapsort_state.hpp"
#include "heapsort_module.hpp"
#include <iostream>

int main(int argc, char* argv[]) {
    heapsort_lua_State state;
    state.arg = luaArray<luaValue>{{}};
    for (int i = 1; i < argc; ++i) {
        state.arg.set(i - 1, luaValue(argv[i]));
    }

    state.print = &l2c::print;
    state.tonumber = &l2c::tonumber;

    luaValue result = _l2c__heapsort_export(&state);

    return 0;
}
