#include "fixpoint_fact_state.hpp"
#include "fixpoint_fact_module.hpp"
#include <iostream>

int main(int argc, char* argv[]) {
    fixpoint_fact_lua_State state;
    state.arg = luaArray<luaValue>{{}};
    for (int i = 1; i < argc; ++i) {
        state.arg.set(i - 1, luaValue(argv[i]));
    }

    state.print = &l2c::print;
    state.tonumber = &l2c::tonumber;

    luaValue result = _l2c__fixpoint_fact_export(&state);

    return 0;
}
