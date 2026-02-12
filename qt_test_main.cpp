#include "qt_test_state.hpp"
#include "qt_test_module.hpp"
#include <iostream>

int main(int argc, char* argv[]) {
    qt_test_lua_State state;

    // Initialize library function pointers
    state.print = &l2c::print;
            state.tonumber = &l2c::tonumber;
            state.math.abs = &l2c::math_abs;
            state.math.ceil = &l2c::math_ceil;
            state.math.cos = &l2c::math_cos;
            state.math.exp = &l2c::math_exp;
            state.math.floor = &l2c::math_floor;
            state.math.log = &l2c::math_log;
            state.math.max = &l2c::math_max;
            state.math.min = &l2c::math_min;
            state.math.random = &l2c::math_random;
            state.math.randomseed = &l2c::math_randomseed;
            state.math.sin = &l2c::math_sin;
            state.math.sqrt = &l2c::math_sqrt;
            state.math.tan = &l2c::math_tan;

    // Call module entry point
    luaValue result = _l2c__qt_test_export(&state);

    return 0;
}
