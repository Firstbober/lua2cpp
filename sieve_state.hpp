#pragma once

#include "l2c_runtime.hpp"
#include <unordered_map>

struct sieve_lua_State {
    // Special globals
    // NUM (user-defined)
    double NUM;
    // arg
    luaArray<luaValue> arg;
    // k (user-defined)
    luaValue k;
    // lim (user-defined)
    double lim;

    // Standalone functions
    luaValue(*assert)(const luaValue&);
    void(*print)(const std::vector<luaValue>&);
    luaValue(*tonumber)(const luaValue&);

};
