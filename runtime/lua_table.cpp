#include "lua_table.hpp"

luaValue luaTable::get(int index) const {
    auto it = array_part_.find(index);
    if (it != array_part_.end()) {
        return it->second;
    }
    return luaValue();
}

luaValue luaTable::get(const std::string& key) const {
    auto it = hash_part_.find(key);
    if (it != hash_part_.end()) {
        return it->second;
    }
    return luaValue();
}

void luaTable::set(int index, const luaValue& value) {
    array_part_[index] = value;
}

void luaTable::set(const std::string& key, const luaValue& value) {
    hash_part_[key] = value;
}

luaValue& luaTable::operator[](int index) {
    return array_part_[index];
}

const luaValue& luaTable::operator[](int index) const {
    static const luaValue nil_value;
    auto it = array_part_.find(index);
    if (it != array_part_.end()) {
        return it->second;
    }
    return nil_value;
}
