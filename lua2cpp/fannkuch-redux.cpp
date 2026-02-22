// Auto-generated from ../tests/cpp/lua/fannkuch-redux.lua
// Lua2Cpp Transpiler
#include "../runtime/l2c_runtime_lua_table.hpp"
// Module state
TABLE fannkuch_redux_flips;
NUMBER fannkuch_redux_n;
TABLE fannkuch_redux_sum;

// Forward declarations
// Local function: fannkuch

template<typename n_t>
auto fannkuch(n_t n) {
    auto p = NEW_TABLE;
auto q = NEW_TABLE;
auto s = NEW_TABLE;
auto sign = NUMBER(1);
auto maxflips = NUMBER(0);
auto sum = NUMBER(0);
    for (double i = NUMBER(1); i <= fannkuch_redux_n; i += 1) {
    p[i] = i;
    
    q[i] = i;
    
    s[i] = i;
}
    do {
    auto q1 = p[NUMBER(1)];
    if (l2c::is_truthy((q1 != NUMBER(1)))) {
    for (double i = NUMBER(2); i <= fannkuch_redux_n; i += 1) {
    q[i] = p[i];
}
    auto flips = NUMBER(1);
    do {
    auto qq = q[q1];
    if (l2c::is_truthy((qq == NUMBER(1)))) {
    fannkuch_redux_sum = (fannkuch_redux_sum + (sign * fannkuch_redux_flips));
    if (l2c::is_truthy((fannkuch_redux_flips > maxflips))) {
    maxflips = fannkuch_redux_flips;
}
    break;
}
    q[q1] = q1;
    if (l2c::is_truthy((q1 >= NUMBER(4)))) {
    auto i = NUMBER(2);
auto j = (q1 - NUMBER(1));
    do {
    auto _l2c_tmp_0 = q[j];
auto _l2c_tmp_1 = q[i];
q[i] = _l2c_tmp_0;
q[j] = _l2c_tmp_1;
    
    i = (i + NUMBER(1));
    
    j = (j - NUMBER(1));
    
} while (!l2c::is_truthy((i >= j)));
}
    q1 = qq;
    
    fannkuch_redux_flips = (fannkuch_redux_flips + NUMBER(1));
} while (!l2c::is_truthy(false));
}
    if (l2c::is_truthy((sign == NUMBER(1)))) {
    auto _l2c_tmp_0 = p[NUMBER(1)];
auto _l2c_tmp_1 = p[NUMBER(2)];
p[NUMBER(2)] = _l2c_tmp_0;
p[NUMBER(1)] = _l2c_tmp_1;
    
    sign = -(NUMBER(1));
}
else {
    auto _l2c_tmp_0 = p[NUMBER(3)];
auto _l2c_tmp_1 = p[NUMBER(2)];
p[NUMBER(2)] = _l2c_tmp_0;
p[NUMBER(3)] = _l2c_tmp_1;
    
    sign = NUMBER(1);
    for (double i = NUMBER(3); i <= fannkuch_redux_n; i += 1) {
    auto sx = s[i];
    if (l2c::is_truthy((sx != NUMBER(1)))) {
    s[i] = (sx - NUMBER(1));
    
    break;
}
    if (l2c::is_truthy((i == fannkuch_redux_n))) {
    return multi_return(fannkuch_redux_sum, maxflips);
}
    s[i] = i;
    auto t = p[NUMBER(1)];
    
    for (double j = NUMBER(1); j <= i; j += 1) {
    p[j] = p[(j + NUMBER(1))];
}
    
    p[(i + NUMBER(1))] = t;
}
}
} while (!l2c::is_truthy(false));
}

// Module body
void fannkuch_redux_module_init(TABLE arg) {
    // fannkuch_redux_module_init - Module initialization
    // This function contains all module-level statements
    fannkuch_redux_n = ((l2c::tonumber(((arg) ? (arg[NUMBER(1)]) : (arg)))) ? (l2c::tonumber(((arg) ? (arg[NUMBER(1)]) : (arg)))) : (TABLE(NUMBER(7))));
    auto _mr_sum = fannkuch(fannkuch_redux_n);
auto sum = _mr_sum;
auto flips = _mr_sum[2];
    l2c::io_write(fannkuch_redux_sum, "\nPfannkuchen(", fannkuch_redux_n, ") = ", fannkuch_redux_flips, "\n");
}