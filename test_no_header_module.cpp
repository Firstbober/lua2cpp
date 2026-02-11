// Auto-generated from test_no_header.lua
// Lua2C Transpiler with Type Optimization

#include "test_no_header_state.hpp"
#include "test_no_header_module.hpp"

// Module export: _l2c__test_no_header_export
luaValue _l2c__test_no_header_export(test_no_header_lua_State* state) {
    state->io.write(std::vector<luaValue>{luaValue("test")});
    return luaValue();
}