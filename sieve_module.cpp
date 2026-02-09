// Auto-generated from tests/cpp/lua/sieve.lua
// Lua2C Transpiler with Type Optimization

#include "sieve_state.hpp"
#include "sieve_module.hpp"

// Module export: _l2c__sieve_export
luaValue _l2c__sieve_export(sieve_lua_State* state) {
    double count = 0;
    auto main_lua(sieve_lua_State* state, luaValue num, luaValue lim) -> luaValue {
    luaValue flags = luaValue::new_table();
for (luaValue num = num; num <= luaValue(1); num = num + -(luaValue(1))) {
    count = 0;
    for (luaValue i = luaValue(1); i <= lim; i++) {
    (flags)[i] = luaValue(1);
}
    for (luaValue i = luaValue(2); i <= lim; i++) {
    if (luaValue((flags)[i] == luaValue(1)).is_truthy()) {
    state->k = luaValue(0);
    for (luaValue k = i + i; k <= lim; k = k + i) {
    (flags)[k] = luaValue(0);
}
    count = count + luaValue(1);
}
}
}
return luaValue();
}
    state->NUM = [&]() { auto _l2c_tmp_left = state->tonumber([&]() { return (state->arg).get(1 - 1); }()); auto _l2c_tmp_right = luaValue(100); auto _l2c_result = luaValue(_l2c_tmp_left.is_truthy() ? _l2c_tmp_left : _l2c_tmp_right); return _l2c_result.as_number(); }();
    state->lim = luaValue(([&]() { return (state->arg).get(2 - 1); }()).is_truthy() ? ([&]() { return (state->arg).get(2 - 1); }()) : (luaValue(8192))).as_number();
    state->print(std::vector<luaValue>{luaValue(state->NUM), luaValue(state->lim)});
    count = 0;
    state->main({luaValue(state->NUM), luaValue(state->lim)});
    state->print(std::vector<luaValue>{luaValue("Count: "), luaValue(count)});
    return luaValue();
}