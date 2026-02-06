#include "lua_value.hpp"
#include <stdexcept>
#include <functional>

luaValue::luaValue() : type_(LuaType::NIL), data_(std::monostate{}) {}

luaValue::luaValue(bool val) : type_(LuaType::BOOLEAN), data_(val) {}

luaValue::luaValue(int val) : type_(LuaType::NUMBER), data_(static_cast<double>(val)) {}

luaValue::luaValue(double val) : type_(LuaType::NUMBER), data_(val) {}

luaValue::luaValue(const char* val) : type_(LuaType::STRING), data_(std::string(val)) {}

luaValue::luaValue(const std::string& val) : type_(LuaType::STRING), data_(val) {}

luaValue::luaValue(std::map<int, luaValue> val) : type_(LuaType::TABLE), data_(val) {}

luaValue::luaValue(std::function<luaValue(const std::vector<luaValue>&)> val)
    : type_(LuaType::FUNCTION), data_(val) {}

bool luaValue::is_truthy() const {
    if (type_ == LuaType::NIL) {
        return false;
    }
    if (type_ == LuaType::BOOLEAN) {
        return std::get<bool>(data_);
    }
    return true;
}

luaValue luaValue::operator+(const luaValue& other) const {
    double lhs = as_number();
    double rhs = other.as_number();
    return luaValue(lhs + rhs);
}

luaValue luaValue::operator-(const luaValue& other) const {
    double lhs = as_number();
    double rhs = other.as_number();
    return luaValue(lhs - rhs);
}

luaValue luaValue::operator*(const luaValue& other) const {
    double lhs = as_number();
    double rhs = other.as_number();
    return luaValue(lhs * rhs);
}

luaValue luaValue::operator/(const luaValue& other) const {
    double lhs = as_number();
    double rhs = other.as_number();
    return luaValue(lhs / rhs);
}

bool luaValue::operator==(const luaValue& other) const {
    if (type_ != other.type_) {
        return false;
    }
    if (type_ == LuaType::NIL) {
        return true;
    }
    if (type_ == LuaType::NUMBER) {
        return as_number() == other.as_number();
    }
    if (type_ == LuaType::BOOLEAN) {
        return std::get<bool>(data_) == std::get<bool>(other.data_);
    }
    if (type_ == LuaType::STRING) {
        return as_string() == other.as_string();
    }
    return false;
}

bool luaValue::operator!=(const luaValue& other) const {
    return !(*this == other);
}

bool luaValue::operator<(const luaValue& other) const {
    double lhs = as_number();
    double rhs = other.as_number();
    return lhs < rhs;
}

bool luaValue::operator<=(const luaValue& other) const {
    double lhs = as_number();
    double rhs = other.as_number();
    return lhs <= rhs;
}

bool luaValue::operator>(const luaValue& other) const {
    double lhs = as_number();
    double rhs = other.as_number();
    return lhs > rhs;
}

bool luaValue::operator>=(const luaValue& other) const {
    double lhs = as_number();
    double rhs = other.as_number();
    return lhs >= rhs;
}


luaValue& luaValue::operator[](int index) {
    if (type_ != LuaType::TABLE) {
        throw std::runtime_error("Attempt to index non-table value");
    }
    return std::get<std::map<int, luaValue>>(data_)[index];
}

luaValue& luaValue::operator[](const std::string& key) {
    if (type_ != LuaType::TABLE) {
        throw std::runtime_error("Attempt to index non-table value");
    }
    // For string keys, hash them to int for now
    // TODO: Implement proper hash table with string keys
    size_t hash = std::hash<std::string>{}(key);
    return std::get<std::map<int, luaValue>>(data_)[static_cast<int>(hash)];
}

luaValue& luaValue::operator[](const luaValue& key) {
    if (type_ != LuaType::TABLE) {
        throw std::runtime_error("Attempt to index non-table value");
    }
    // For luaValue keys, convert to int or string
    if (key.type_ == LuaType::NUMBER) {
        return std::get<std::map<int, luaValue>>(data_)[static_cast<int>(key.as_number())];
    } else if (key.type_ == LuaType::STRING) {
        std::string str_key = key.as_string();
        size_t hash = std::hash<std::string>{}(str_key);
        return std::get<std::map<int, luaValue>>(data_)[static_cast<int>(hash)];
    } else {
        throw std::runtime_error("Invalid table key type");
    }
}

const luaValue& luaValue::operator[](int index) const {
    if (type_ != LuaType::TABLE) {
        throw std::runtime_error("Attempt to index non-table value");
    }
    static const luaValue nil_value;
    auto& table = std::get<std::map<int, luaValue>>(data_);
    auto it = table.find(index);
    if (it != table.end()) {
        return it->second;
    }
    return nil_value;
}

const luaValue& luaValue::operator[](const std::string& key) const {
    if (type_ != LuaType::TABLE) {
        throw std::runtime_error("Attempt to index non-table value");
    }
    static const luaValue nil_value;
    size_t hash = std::hash<std::string>{}(key);
    auto& table = std::get<std::map<int, luaValue>>(data_);
    auto it = table.find(static_cast<int>(hash));
    if (it != table.end()) {
        return it->second;
    }
    return nil_value;
}

const luaValue& luaValue::operator[](const luaValue& key) const {
    if (type_ != LuaType::TABLE) {
        throw std::runtime_error("Attempt to index non-table value");
    }
    static const luaValue nil_value;
    auto& table = std::get<std::map<int, luaValue>>(data_);

    if (key.type_ == LuaType::NUMBER) {
        int int_key = static_cast<int>(key.as_number());
        auto it = table.find(int_key);
        if (it != table.end()) {
            return it->second;
        }
    } else if (key.type_ == LuaType::STRING) {
        std::string str_key = key.as_string();
        size_t hash = std::hash<std::string>{}(str_key);
        int int_key = static_cast<int>(hash);
        auto it = table.find(int_key);
        if (it != table.end()) {
            return it->second;
        }
    }

    return nil_value;
}

luaValue luaValue::operator()(const std::vector<luaValue>& args) const {
    if (type_ != LuaType::FUNCTION) {
        throw std::runtime_error("Attempt to call non-function value");
    }
    return std::get<std::function<luaValue(const std::vector<luaValue>&)>>(data_)(args);
}

double luaValue::as_number() const {
    if (type_ == LuaType::NUMBER) {
        return std::get<double>(data_);
    }
    if (type_ == LuaType::BOOLEAN) {
        return std::get<bool>(data_) ? 1.0 : 0.0;
    }
    if (type_ == LuaType::STRING) {
        try {
            return std::stod(as_string());
        } catch (...) {
            return 0.0;
        }
    }
    return 0.0;
}

std::string luaValue::as_string() const {
    if (type_ == LuaType::STRING) {
        return std::get<std::string>(data_);
    }
    if (type_ == LuaType::NUMBER) {
        return std::to_string(as_number());
    }
    if (type_ == LuaType::BOOLEAN) {
        return std::get<bool>(data_) ? "true" : "false";
    }
    if (type_ == LuaType::NIL) {
        return "nil";
    }
    return "";
}

luaValue luaValue::new_table() {
    return luaValue(std::map<int, luaValue>{});
}
