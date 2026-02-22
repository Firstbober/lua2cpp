// Auto-generated from ../tests/cpp/lua/mandel.lua
// Lua2Cpp Transpiler
#include "../runtime/l2c_runtime_lua_table.hpp"
// Module state
TABLE mandel_Complex;
NUMBER mandel_N;
NUMBER mandel_S;
NUMBER mandel_dx;
NUMBER mandel_dy;
NUMBER mandel_xmax;
NUMBER mandel_xmin;
NUMBER mandel_ymax;
NUMBER mandel_ymin;

// Forward declarations
// Local function: complex
// Local function: abs

template<typename x_t, typename y_t>
TABLE complex(x_t x, y_t y) {
    return l2c::setmetatable([=]() {
    TABLE t = NEW_TABLE;
    t[STRING("re")] = x;
    t[STRING("im")] = y;
    return t;
}(), mandel_Complex["metatable"]);
}

template<typename T1, typename T2>
auto Complex_conj(T1 x, T2 y) {
    return complex(x["re"], -(x["im"]));
}
// Register conj in mandel_Complex
mandel_Complex[STRING("conj")] = l2c::make_function([](TValue a, TValue b) -> TValue {
    return Complex_conj(a, b);
});

template<typename T1>
auto Complex_norm2(T1 x) {
    auto n = mandel_Complex["mul"](x, mandel_Complex["conj"](x));
    return n["re"];
}
// Register norm2 in mandel_Complex
mandel_Complex[STRING("norm2")] = l2c::make_function([](TValue a, TValue b) -> TValue {
    return Complex_norm2(a, b);
});

template<typename T1>
auto Complex_abs(T1 x) {
    return sqrt(mandel_Complex["norm2"](x));
}
// Register abs in mandel_Complex
mandel_Complex[STRING("abs")] = l2c::make_function([](TValue a, TValue b) -> TValue {
    return Complex_abs(a, b);
});

template<typename T1, typename T2>
auto Complex_add(T1 x, T2 y) {
    return complex((x["re"] + y["re"]), (x["im"] + y["im"]));
}
// Register add in mandel_Complex
mandel_Complex[STRING("add")] = l2c::make_function([](TValue a, TValue b) -> TValue {
    return Complex_add(a, b);
});

template<typename T1, typename T2>
auto Complex_mul(T1 x, T2 y) {
    return complex(((x["re"] * y["re"]) - (x["im"] * y["im"])), ((x["re"] * y["im"]) + (x["im"] * y["re"])));
}
// Register mul in mandel_Complex
mandel_Complex[STRING("mul")] = l2c::make_function([](TValue a, TValue b) -> TValue {
    return Complex_mul(a, b);
});

template<typename x_t>
double abs(x_t x) {
    return l2c::math_sqrt(mandel_Complex["norm2"](x));
}

template<typename T1, typename T2>
auto level(T1 x, T2 y) {
    auto c = complex(x, y);
    auto l = NUMBER(0);
    auto z = c;
    do {
    z = ((z * z) + c);
    l = (l + NUMBER(1));
} while (!l2c::is_truthy((((abs(z) > NUMBER(2.0))) ? ((abs(z) > NUMBER(2.0))) : ((l > NUMBER(255))))));
    return (l - NUMBER(1));
}

// Module body
void mandel_module_init(TABLE arg) {
    // mandel_module_init - Module initialization
    // This function contains all module-level statements
    TABLE xmin;
    TABLE xmax;
    TABLE ymin;
    TABLE ymax;
    TABLE N;
    TABLE dx;
    TABLE dy;
    mandel_Complex = [=]() {
    TABLE t = NEW_TABLE;
    t[STRING("type")] = "package";
    return t;
}();
    mandel_Complex["metatable"] = [=]() {
    TABLE t = NEW_TABLE;
    t[STRING("__add")] = mandel_Complex["add"];
    t[STRING("__mul")] = mandel_Complex["mul"];
    return t;
}();
    mandel_xmin = -(NUMBER(2.0));
    mandel_xmax = NUMBER(2.0);
    mandel_ymin = -(NUMBER(2.0));
    mandel_ymax = NUMBER(2.0);
    mandel_N = ((arg[NUMBER(1)]) ? (arg[NUMBER(1)]) : (TABLE(NUMBER(256))));
    mandel_dx = ((mandel_xmax - mandel_xmin) / mandel_N);
    mandel_dy = ((mandel_ymax - mandel_ymin) / mandel_N);
    l2c::print("P2");
    l2c::print("# mandelbrot set", mandel_xmin, mandel_xmax, mandel_ymin, mandel_ymax, mandel_N);
    l2c::print(mandel_N, mandel_N, NUMBER(255));
    mandel_S = NUMBER(0);
    for (double i = NUMBER(1); i <= mandel_N; i += 1) {
    auto x = (mandel_xmin + ((i - NUMBER(1)) * mandel_dx));
    for (double j = NUMBER(1); j <= mandel_N; j += 1) {
    auto y = (mandel_ymin + ((j - NUMBER(1)) * mandel_dy));
    mandel_S = (mandel_S + level(x, y));
}
}
    l2c::print(mandel_S);
}