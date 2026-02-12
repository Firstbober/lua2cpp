// Auto-generated from tests/cpp/lua/qt.lua
// Lua2C Transpiler with Type Optimization

#include "qt_test_state.hpp"
#include "qt_test_module.hpp"

auto output(qt_test_lua_State* state, auto&& a1, auto&& a2, auto&& a3, auto&& a4, auto&& a5, auto&& a6) {
    state->write({luaValue((a1).is_truthy() ? (a1) : (luaValue(""))), luaValue(" "), luaValue((a2).is_truthy() ? (a2) : (luaValue(""))), luaValue(" "), luaValue((a3).is_truthy() ? (a3) : (luaValue(""))), luaValue(" "), luaValue((a4).is_truthy() ? (a4) : (luaValue(""))), luaValue(" "), luaValue((a5).is_truthy() ? (a5) : (luaValue(""))), luaValue(" "), luaValue((a6).is_truthy() ? (a6) : (luaValue(""))), luaValue(" \n")});
return luaValue();
}

auto imul(qt_test_lua_State* state, auto&& xmin, auto&& xmax, auto&& ymin, auto&& ymax) {
    double mm = xmin * ymin;
double mM = xmin * ymax;
double Mm = xmax * ymin;
double MM = xmax * ymax;
luaValue m = mm;
luaValue M = mm;
if (luaValue(m > mM).is_truthy()) {
    m = mM;
}
if (luaValue(m > Mm).is_truthy()) {
    m = Mm;
}
if (luaValue(m > MM).is_truthy()) {
    m = MM;
}
return std::vector<luaValue>({m, M});
}

auto isqr(qt_test_lua_State* state, auto&& xmin, auto&& xmax) {
    double u = xmin * xmin;
double v = xmax * xmax;
if (luaValue((luaValue(xmin <= luaValue(0.0))).is_truthy() ? (luaValue(luaValue(0.0) <= xmax)) : (luaValue(xmin <= luaValue(0.0)))).is_truthy()) {
    if (luaValue(u < v).is_truthy()) {
    return std::vector<luaValue>({luaValue(0.0), v});
}
else {
    return std::vector<luaValue>({luaValue(0.0), u});
}
}
else {
    if (luaValue(u < v).is_truthy()) {
    return std::vector<luaValue>({u, v});
}
else {
    return std::vector<luaValue>({v, u});
}
}
return luaValue();
}

auto f(qt_test_lua_State* state, auto&& xmin, auto&& xmax, auto&& ymin, auto&& ymax) {
    luaValue x2min = luaValue(isqr(state, xmin, xmax));
luaValue y2min = luaValue(isqr(state, ymin, ymax));
luaValue xymin = luaValue(imul(state, xmin, xmax, ymin, ymax));
return std::vector<luaValue>({x2min - y2max + state->cx, x2max - y2min + state->cx, 2.0 * xymin + state->cy, 2.0 * xymax + state->cy});
}

auto outside(qt_test_lua_State* state, auto&& xmin, auto&& xmax, auto&& ymin, auto&& ymax) {
    luaValue x = luaValue();
luaValue y = luaValue();
if (luaValue(luaValue(0.0) < xmin).is_truthy()) {
    x = xmin;
}
if (luaValue(luaValue(0.0) < ymin).is_truthy()) {
    y = ymin;
}
return luaValue(l2c_pow(x, luaValue(2)) + l2c_pow(y, luaValue(2)) > luaValue(4.0));
}

auto inside(qt_test_lua_State* state, auto&& xmin, auto&& xmax, auto&& ymin, auto&& ymax) {
    return luaValue((luaValue((luaValue((luaValue(l2c_pow(xmin, luaValue(2)) + l2c_pow(ymin, luaValue(2)) <= luaValue(4.0))).is_truthy() ? (luaValue(l2c_pow(xmin, luaValue(2)) + l2c_pow(ymax, luaValue(2)) <= luaValue(4.0))) : (luaValue(l2c_pow(xmin, luaValue(2)) + l2c_pow(ymin, luaValue(2)) <= luaValue(4.0))))).is_truthy() ? (luaValue(l2c_pow(xmax, luaValue(2)) + l2c_pow(ymin, luaValue(2)) <= luaValue(4.0))) : (luaValue((luaValue(l2c_pow(xmin, luaValue(2)) + l2c_pow(ymin, luaValue(2)) <= luaValue(4.0))).is_truthy() ? (luaValue(l2c_pow(xmin, luaValue(2)) + l2c_pow(ymax, luaValue(2)) <= luaValue(4.0))) : (luaValue(l2c_pow(xmin, luaValue(2)) + l2c_pow(ymin, luaValue(2)) <= luaValue(4.0))))))).is_truthy() ? (luaValue(l2c_pow(xmax, luaValue(2)) + l2c_pow(ymax, luaValue(2)) <= luaValue(4.0))) : (luaValue((luaValue((luaValue(l2c_pow(xmin, luaValue(2)) + l2c_pow(ymin, luaValue(2)) <= luaValue(4.0))).is_truthy() ? (luaValue(l2c_pow(xmin, luaValue(2)) + l2c_pow(ymax, luaValue(2)) <= luaValue(4.0))) : (luaValue(l2c_pow(xmin, luaValue(2)) + l2c_pow(ymin, luaValue(2)) <= luaValue(4.0))))).is_truthy() ? (luaValue(l2c_pow(xmax, luaValue(2)) + l2c_pow(ymin, luaValue(2)) <= luaValue(4.0))) : (luaValue((luaValue(l2c_pow(xmin, luaValue(2)) + l2c_pow(ymin, luaValue(2)) <= luaValue(4.0))).is_truthy() ? (luaValue(l2c_pow(xmin, luaValue(2)) + l2c_pow(ymax, luaValue(2)) <= luaValue(4.0))) : (luaValue(l2c_pow(xmin, luaValue(2)) + l2c_pow(ymin, luaValue(2)) <= luaValue(4.0))))))));
}

auto newcell(qt_test_lua_State* state) {
    return luaValue::new_table();
}

auto addedge(qt_test_lua_State* state, auto&& a, auto&& b) {
    state->nE = state->nE + 1;
(state->E).set(state->nE - 1, b);
return luaValue();
}

auto refine(qt_test_lua_State* state, auto&& q) {
    if (luaValue(((q).get(color.as_number() - 1) == state->gray)).is_truthy()) {
    if (luaValue(((q).get(1 - 1) == luaValue())).is_truthy()) {
    (q).set(1 - 1, newcell(state));
    (q).set(2 - 1, newcell(state));
    (q).set(3 - 1, newcell(state));
    (q).set(4 - 1, newcell(state));
}
else {
    refine(state, (q).get(1 - 1));
    refine(state, (q).get(2 - 1));
    refine(state, (q).get(3 - 1));
    refine(state, (q).get(4 - 1));
}
}
return luaValue();
}

auto clip(qt_test_lua_State* state, auto&& q, auto&& xmin, auto&& xmax, auto&& ymin, auto&& ymax, auto&& o, auto&& oxmin, auto&& oxmax, auto&& oymin, auto&& oymax) {
    luaValue ixmin = luaValue();
luaValue ixmax = luaValue();
luaValue iymin = luaValue();
luaValue iymax = luaValue();
if (luaValue(xmin > oxmin).is_truthy()) {
    ixmin = xmin;
}
else {
    ixmin = oxmin;
}
if (luaValue(xmax < oxmax).is_truthy()) {
    ixmax = xmax;
}
else {
    ixmax = oxmax;
}
if (luaValue(ixmin >= ixmax).is_truthy()) {
    return luaValue()
}
if (luaValue(ymin > oymin).is_truthy()) {
    iymin = ymin;
}
else {
    iymin = oymin;
}
if (luaValue(ymax < oymax).is_truthy()) {
    iymax = ymax;
}
else {
    iymax = oymax;
}
if (luaValue(iymin < iymax).is_truthy()) {
    if (luaValue(((q).get(1 - 1) == luaValue())).is_truthy()) {
    addedge(state, o, q);
}
else {
    double xmid = xmin + xmax / 2.0;
    double ymid = ymin + ymax / 2.0;
    clip(state, (q).get(1 - 1), xmin, xmid, ymid, ymax, o, oxmin, oxmax, oymin, oymax);
    clip(state, (q).get(2 - 1), xmid, xmax, ymid, ymax, o, oxmin, oxmax, oymin, oymax);
    clip(state, (q).get(3 - 1), xmin, xmid, ymin, ymid, o, oxmin, oxmax, oymin, oymax);
    clip(state, (q).get(4 - 1), xmid, xmax, ymin, ymid, o, oxmin, oxmax, oymin, oymax);
}
}
return luaValue();
}

auto map(qt_test_lua_State* state, auto&& q, auto&& xmin, auto&& xmax, auto&& ymin, auto&& ymax) {
    xmin = f(state, xmin, xmax, ymin, ymax);
if (outside(state, xmin, xmax, ymin, ymax).is_truthy()) {
    (q).set(state->color - 1, state->white);
}
else {
    if (!(inside(state, xmin, xmax, ymin, ymax)).is_truthy().is_truthy()) {
    addedge(state, q, state->exterior);
}
    clip(state, state->root, state->Rxmin, state->Rxmax, state->Rymin, state->Rymax, q, xmin, xmax, ymin, ymax);
}
return luaValue();
}

auto update(qt_test_lua_State* state, auto&& q, auto&& xmin, auto&& xmax, auto&& ymin, auto&& ymax) {
    if (luaValue(((q).get(color.as_number() - 1) == state->gray)).is_truthy()) {
    if (luaValue(((q).get(1 - 1) == luaValue())).is_truthy()) {
    luaValue b = state->nE;
    (q).set(2 - 1, state->nE + 1);
    map(state, q, xmin, xmax, ymin, ymax);
    (q).set(3 - 1, state->nE);
}
else {
    double xmid = xmin + xmax / 2.0;
    double ymid = ymin + ymax / 2.0;
    update(state, (q).get(1 - 1), xmin, xmid, ymid, ymax);
    update(state, (q).get(2 - 1), xmid, xmax, ymid, ymax);
    update(state, (q).get(3 - 1), xmin, xmid, ymin, ymid);
    update(state, (q).get(4 - 1), xmid, xmax, ymin, ymid);
}
}
return luaValue();
}

auto color(qt_test_lua_State* state, auto&& q) {
    if (luaValue(((q).get(color.as_number() - 1) == state->gray)).is_truthy()) {
    if (luaValue(((q).get(1 - 1) == luaValue())).is_truthy()) {
    for (double i = (q).get(2 - 1); i <= (q).get(3 - 1); i++) {
    if (luaValue((((state->E).get(i - 1))["color"] != state->white)).is_truthy()) {
    return luaValue()
}
}
    (q).set(color - 1, state->white);
    state->N = state->N + 1;
}
else {
    color(state, (q).get(1 - 1));
    color(state, (q).get(2 - 1));
    color(state, (q).get(3 - 1));
    color(state, (q).get(4 - 1));
}
}
return luaValue();
}

auto prewhite(qt_test_lua_State* state, auto&& q) {
    if (luaValue(((q).get(color.as_number() - 1) == state->gray)).is_truthy()) {
    if (luaValue(((q).get(1 - 1) == luaValue())).is_truthy()) {
    for (double i = (q).get(2 - 1); i <= (q).get(3 - 1); i++) {
    luaValue c = ((state->E).get(i - 1))["color"];
    if (luaValue((luaValue((c == state->white))).is_truthy() ? (luaValue((c == state->white))) : (luaValue((c == -(state->gray))))).is_truthy()) {
    (q).set(color - 1, -(state->gray));
    state->N = state->N + 1;
    return luaValue()
}
}
}
else {
    prewhite(state, (q).get(1 - 1));
    prewhite(state, (q).get(2 - 1));
    prewhite(state, (q).get(3 - 1));
    prewhite(state, (q).get(4 - 1));
}
}
return luaValue();
}

auto recolor(qt_test_lua_State* state, auto&& q) {
    if (luaValue(((q).get(color.as_number() - 1) == -(state->gray))).is_truthy()) {
    (q).set(color - 1, state->gray);
}
return luaValue();
}

auto area(qt_test_lua_State* state, auto&& q) {
    if (luaValue(((q).get(1 - 1) == luaValue())).is_truthy()) {
    if (luaValue(((q).get(color.as_number() - 1) == state->white)).is_truthy()) {
    return std::vector<luaValue>({luaValue(0.0), luaValue(0.0)});
}
}
else {
    luaValue g1 = luaValue(area(state, (q).get(1 - 1)));
    luaValue g2 = luaValue(area(state, (q).get(2 - 1)));
    luaValue g3 = luaValue(area(state, (q).get(3 - 1)));
    luaValue g4 = luaValue(area(state, (q).get(4 - 1)));
    return std::vector<luaValue>({(g1 + g2 + g3 + g4) / 4.0, (b1 + b2 + b3 + b4) / 4.0});
}
return luaValue();
}

auto colorup(qt_test_lua_State* state, auto&& q) {
    if (luaValue((luaValue(((q).get(1 - 1) != luaValue()))).is_truthy() ? (luaValue(((q).get(color.as_number() - 1) == state->gray))) : (luaValue(((q).get(1 - 1) != luaValue())))).is_truthy()) {
    luaValue c1 = luaValue(colorup(state, (q).get(1 - 1)));
    luaValue c2 = luaValue(colorup(state, (q).get(2 - 1)));
    luaValue c3 = luaValue(colorup(state, (q).get(3 - 1)));
    luaValue c4 = luaValue(colorup(state, (q).get(4 - 1)));
    if (luaValue((luaValue((luaValue((c1 == c2))).is_truthy() ? (luaValue((c1 == c3))) : (luaValue((c1 == c2))))).is_truthy() ? (luaValue((c1 == c4))) : (luaValue((luaValue((c1 == c2))).is_truthy() ? (luaValue((c1 == c3))) : (luaValue((c1 == c2)))))).is_truthy()) {
    if (luaValue((c1 != state->gray)).is_truthy()) {
    (q).set(1 - 1, luaValue());
    
    state->N = state->N + 1;
}
    (q).set(color - 1, c1);
}
}
return (q).get(color.as_number() - 1);
}

auto save(qt_test_lua_State* state, auto&& q, auto&& xmin, auto&& ymin, auto&& N) {
    if (luaValue((luaValue(((q).get(1 - 1) == luaValue()))).is_truthy() ? (luaValue(((q).get(1 - 1) == luaValue()))) : (luaValue((N == 1)))).is_truthy()) {
    output(state, xmin, ymin, N, (q).get(color.as_number() - 1));
}
else {
    N = N / 2;
    double xmid = xmin + N;
    double ymid = ymin + N;
    save(state, (q).get(1 - 1), xmin, ymin, N);
    save(state, (q).get(2 - 1), xmid, ymin, N);
    save(state, (q).get(3 - 1), xmin, ymid, N);
    save(state, (q).get(4 - 1), xmid, ymid, N);
}
return luaValue();
}

auto show(qt_test_lua_State* state, auto&& p) {
    double N = l2c_pow(luaValue(2), luaValue(10));
output(state, state->N);
{
    luaValue _l2c_tmp_arg_0 = luaValue(0);
    luaValue _l2c_tmp_arg_1 = luaValue(0);
    save(state, state->root, _l2c_tmp_arg_0, _l2c_tmp_arg_1, state->N);
}
return luaValue();
}

auto memory(qt_test_lua_State* state, auto&& s) {
    luaValue t = state->os.clock({});
double dt = t - state->t0;
((state->io)["stdout"])[state->write]({(state->io)["stdout"], s, luaValue("	"), dt, luaValue(" sec	"), t, luaValue(" sec	"), state->math.floor(state->collectgarbage({luaValue("count")}) / 1024), luaValue("M\n")});
state->t0 = t;
return luaValue();
}

auto do_(qt_test_lua_State* state, auto&& f, auto&& s) {
    luaValue a = luaValue(f(state, state->root, state->Rxmin, state->Rxmax, state->Rymin, state->Rymax));
memory(state, s);
return std::vector<luaValue>({a, b});
}

auto julia(qt_test_lua_State* state, auto&& l, auto&& a, auto&& b) {
    {
    luaValue _l2c_tmp_arg_0 = luaValue("begin");
    memory(state, _l2c_tmp_arg_0);
}
state->cx = a;
state->cy = b;
state->root = newcell(state);
state->exterior = newcell(state);
(state->exterior)["color"] = state->white;
{
    luaValue _l2c_tmp_arg_0 = luaValue(0);
    show(state, _l2c_tmp_arg_0);
}
for (double i = 1; i <= l; i++) {
    state->print(std::vector<luaValue>{luaValue("\nstep"), luaValue(i)});
    state->nE = 0;
    {
    luaValue _l2c_tmp_arg_0 = luaValue("refine");
    do_(state, refine, _l2c_tmp_arg_0);
}
    {
    luaValue _l2c_tmp_arg_0 = luaValue("update");
    do_(state, update, _l2c_tmp_arg_0);
}
    do {
    state->N = 0;
    color(state, state->root, state->Rxmin, state->Rxmax, state->Rymin, state->Rymax);
    state->print(std::vector<luaValue>{luaValue("color"), luaValue(state->N)});
} while (!luaValue((state->N == 0)).is_truthy());
    {
    luaValue _l2c_tmp_arg_0 = luaValue("color");
    memory(state, _l2c_tmp_arg_0);
}
    do {
    state->N = 0;
    prewhite(state, state->root, state->Rxmin, state->Rxmax, state->Rymin, state->Rymax);
    state->print(std::vector<luaValue>{luaValue("prewhite"), luaValue(state->N)});
} while (!luaValue((state->N == 0)).is_truthy());
    {
    luaValue _l2c_tmp_arg_0 = luaValue("prewhite");
    memory(state, _l2c_tmp_arg_0);
}
    {
    luaValue _l2c_tmp_arg_0 = luaValue("recolor");
    do_(state, recolor, _l2c_tmp_arg_0);
}
    {
    luaValue _l2c_tmp_arg_0 = luaValue("colorup");
    do_(state, colorup, _l2c_tmp_arg_0);
}
    state->print(std::vector<luaValue>{luaValue("colorup"), luaValue(state->N)});
    luaValue g = luaValue(do_(state, area, std::string("area")));
    state->print(std::vector<luaValue>{luaValue("area"), luaValue(g), luaValue(b), luaValue(g + b)});
    show(state, i);
    {
    luaValue _l2c_tmp_arg_0 = luaValue("output");
    memory(state, _l2c_tmp_arg_0);
}
    state->print(std::vector<luaValue>{luaValue("edges"), luaValue(state->nE)});
}
return luaValue();
}

// Module export: _l2c__qt_export
luaValue _l2c__qt_export(qt_test_lua_State* state) {
    luaValue io = io;
    luaValue root = luaValue();
luaValue exterior = luaValue();
    luaValue cx = luaValue();
luaValue cy = luaValue();
    double Rxmin = -(luaValue(2.0));
double Rxmax = 2.0;
double Rymin = -(luaValue(2.0));
double Rymax = 2.0;
    double white = 1.0;
    double black = 0.0;
    double gray = 0.5;
    double N = 0;
    double nE = 0;
    luaArray<auto> E = luaValue::new_table();
    luaValue write = state->io.write;
    double t0 = 0;
    {
    luaValue _l2c_tmp_arg_0 = luaValue(10);
    luaValue _l2c_tmp_arg_1 = luaValue(0.74);
    julia(state, _l2c_tmp_arg_0, -(luaValue(0.25)), _l2c_tmp_arg_1);
}
    return luaValue();
}