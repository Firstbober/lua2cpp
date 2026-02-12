#pragma once

#include "l2c_runtime.hpp"
#include <unordered_map>

struct qt_test_lua_State {
    // Special globals
    // N (user-defined)
    double N;
    // a1 (user-defined)
    luaValue a1;
    // a2 (user-defined)
    luaValue a2;
    // a3 (user-defined)
    luaValue a3;
    // a4 (user-defined)
    luaValue a4;
    // a5 (user-defined)
    luaValue a5;
    // a6 (user-defined)
    luaValue a6;
    // b (user-defined)
    luaValue b;
    // cx (user-defined)
    luaValue cx;
    // cy (user-defined)
    luaValue cy;
    // dt (user-defined)
    luaValue dt;
    // exterior (user-defined)
    luaValue exterior;
    // g (user-defined)
    luaValue g;
    // i (user-defined)
    double i;
    // nE (user-defined)
    double nE;
    // o (user-defined)
    luaArray<double> o;
    // q (user-defined)
    luaArray<double> q;
    // root (user-defined)
    luaArray<double> root;
    // s (user-defined)
    luaValue s;
    // t (user-defined)
    luaValue t;
    // t0 (user-defined)
    double t0;
    // xmax (user-defined)
    luaArray<double> xmax;
    // xmin (user-defined)
    luaArray<double> xmin;
    // ymax (user-defined)
    luaArray<double> ymax;
    // ymin (user-defined)
    luaArray<double> ymin;

    // Standalone functions
    luaValue(*assert)(const luaValue&);
    double(*l2c_pow)(double, double);
    void(*print)(const std::vector<luaValue>&);
    luaValue(*tonumber)(const luaValue&);

    // Math library
    struct {
        double(*abs)(double);
        double(*ceil)(double);
        double(*cos)(double);
        double(*exp)(double);
        double(*floor)(double);
        double(*log)(double);
        double(*max)(double, double);
        double(*min)(double, double);
        double(*random)();
        double(*randomseed)(double);
        double(*sin)(double);
        double(*sqrt)(double);
        double(*tan)(double);
    } math;

};
