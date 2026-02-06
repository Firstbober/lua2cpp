#pragma once

#include "lua_value.hpp"
#include <map>
#include <string>

class luaTable {
private:
    std::map<int, luaValue> array_part_;
    std::map<std::string, luaValue> hash_part_;

public:
    luaValue get(int index) const;
    luaValue get(const std::string& key) const;
    
    void set(int index, const luaValue& value);
    void set(const std::string& key, const luaValue& value);
    
    luaValue& operator[](int index);
    const luaValue& operator[](int index) const;
};
