#include "spectral_norm_state.hpp"
#include "spectral_norm_module.hpp"
#include <iostream>

int main(int argc, char* argv[]) {
    spectral_norm_lua_State state;
    // Set command-line arguments
    state.arg = luaArray<luaValue>{{}};
    for (int i = 1; i < argc; ++i) {
        state.arg.set(i - 1, luaValue(argv[i]));
    }

    // Initialize library function pointers
    state.print = &l2c::print;
            state.tonumber = &l2c::tonumber;
            state.io.flush = &l2c::io_flush;
            state.io.read = &l2c::io_read;
            state.io.write = &l2c::io_write;
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
            state.string.format = &l2c::string_format;
            state.string.len = &l2c::string_len;
            state.string.lower = &l2c::string_lower;
            state.string.sub = &l2c::string_sub;
            state.string.upper = &l2c::string_upper;

    // Call module entry point
    luaValue result = _l2c__spectral_norm_export(&state);

    return 0;
}
