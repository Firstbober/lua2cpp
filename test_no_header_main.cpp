#include "test_no_header_state.hpp"
#include "test_no_header_module.hpp"
#include <iostream>

int main(int argc, char* argv[]) {
    test_no_header_lua_State state;

    // Initialize library function pointers
    state.print = &l2c::print;
            state.tonumber = &l2c::tonumber;
            state.io.flush = &l2c::io_flush;
            state.io.read = &l2c::io_read;
            state.io.write = &l2c::io_write;

    // Call module entry point
    luaValue result = _l2c__test_no_header_export(&state);

    return 0;
}
