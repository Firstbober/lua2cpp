#pragma once

#include "l2c_runtime.hpp"
#include <unordered_map>

struct spectralnorm_lua_State {
    // Special globals
    // arg
    luaArray<luaValue> arg;
    // x (user-defined)
    luaValue x;
    // y (user-defined)
    luaValue y;

    // Standalone functions
    void(*print)(const std::vector<luaValue>&);
    double(*tonumber)(const luaValue&);

    // Io library
    struct {
        void(*flush)();
        std::string(*read)(const std::string&);
        void(*write)(const std::vector<luaValue>&);
    } io;

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

    // String library
    struct {
        std::string(*format)(const std::string&, const std::vector<luaValue>&);
        double(*len)(const std::string&);
        std::string(*lower)(const std::string&);
        std::string(*sub)(const std::string&, double, double);
        std::string(*upper)(const std::string&);
    } string;

};
