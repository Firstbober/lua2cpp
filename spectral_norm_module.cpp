// Auto-generated from tests/cpp/lua/spectral-norm.lua
// Lua2C Transpiler with Type Optimization

#include "spectral_norm_state.hpp"
#include "spectral_norm_module.hpp"

auto A(spectral_norm_lua_State* state, auto&& i, auto&& j) {
    double ij = i + j - 1;
return 1.0 / (ij * (ij - 1) * 0.5 + i);
}

auto Av(spectral_norm_lua_State* state, auto&& x, auto&& y, auto&& N) {
    for (double i = 1; i <= N; i++) {
    double a = 0;
    for (double j = 1; j <= N; j++) {
    a = a + (x).get(j - 1) * A(state, i, j);
}
    (y).set(i - 1, a);
}
return luaValue();
}

auto Atv(spectral_norm_lua_State* state, auto&& x, auto&& y, auto&& N) {
    for (double i = 1; i <= N; i++) {
    double a = 0;
    for (double j = 1; j <= N; j++) {
    a = a + (x).get(j - 1) * A(state, j, i);
}
    (y).set(i - 1, a);
}
return luaValue();
}

auto AtAv(spectral_norm_lua_State* state, auto&& x, auto&& y, auto&& t, auto&& N) {
    Av(state, x, t, N);
Atv(state, t, y, N);
return luaValue();
}

// Module export: _l2c__spectral_norm_export
luaValue _l2c__spectral_norm_export(spectral_norm_lua_State* state) {
    double N = [&]() { auto _l2c_tmp_left = state->tonumber([&]() { return (state->arg).get(1 - 1); }()); auto _l2c_tmp_right = luaValue(100); auto _l2c_result = luaValue(_l2c_tmp_left.is_truthy() ? _l2c_tmp_left : _l2c_tmp_right); return _l2c_result.as_number(); }();
    luaArray<double> u = luaArray<double>{{}};
luaArray<double> v = luaArray<double>{{}};
luaArray<double> t = luaArray<double>{{}};
    for (double i = 1; i <= N; i++) {
    (u).set(i - 1, 1);
}
    for (double i = 1; i <= 10; i++) {
    AtAv(state, u, v, t, N);
    AtAv(state, v, u, t, N);
}
    double vBv = 0;
double vv = 0;
    for (double i = 1; i <= N; i++) {
    double ui = (u).get(i - 1);
double vi = (v).get(i - 1);
    vBv = vBv + ui * vi;
    vv = vv + vi * vi;
}
    state->io.write(std::vector<luaValue>{luaValue(state->string.format(std::string("%0.9f\n"), std::vector<luaValue>{luaValue(state->math.sqrt(vBv / vv))}))});
    return luaValue();
}