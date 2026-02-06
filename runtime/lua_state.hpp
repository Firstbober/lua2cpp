#pragma once

#include "lua_value.hpp"
// #include <sol/sol.hpp>  // TODO: Enable sol2 when needed for actual Lua integration
#include <string>
#include <map>
#include <functional>
#include <iostream>
#include <cmath>
#include <cstdio>
#include <sstream>
#include <iomanip>

class luaState {
private:
    // sol::state sol_state_;  // TODO: Enable sol2 when needed
    std::map<std::string, std::function<luaValue(const std::vector<luaValue>&)>> stdlib_functions_;
    std::map<std::string, luaValue> globals_;
    std::vector<luaValue> arg_;

public:
    luaState();

    luaValue get_global(const std::string& name);
    void set_global(const std::string& name, const luaValue& value);

    // sol::state& get_sol_state() { return sol_state_; }  // TODO: Enable sol2 when needed

    const std::vector<luaValue>& get_arg() const { return arg_; }
    void set_arg(const std::vector<luaValue>& arg) { arg_ = arg; }
};
