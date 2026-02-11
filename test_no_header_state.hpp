#pragma once

#include "l2c_runtime.hpp"
#include <unordered_map>

struct test_no_header_lua_State {
    // Standalone functions
    luaValue(*assert)(const luaValue&);
    double(*l2c_pow)(double, double);
    void(*print)(const std::vector<luaValue>&);
    luaValue(*tonumber)(const luaValue&);

    // Io library
    struct {
        void(*flush)();
        std::string(*read)(const std::string&);
        void(*write)(const std::vector<luaValue>&);
    } io;

};
