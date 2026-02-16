#pragma once

#include <variant>
#include <string>
#include <vector>
#include <map>
#include <functional>

enum class LuaType {
    NIL,
    BOOLEAN,
    NUMBER,
    STRING,
    TABLE,
    FUNCTION
};

class luaValue {
private:
    LuaType type_;
    std::variant<
        std::monostate,
        bool,
        double,
        std::string,
        std::map<int, luaValue>,
        std::function<luaValue(const std::vector<luaValue>&)>
    > data_;

public:
    luaValue();
    explicit luaValue(bool val);
    luaValue(int val);
    luaValue(double val);
    luaValue(const char* val);
    luaValue(const std::string& val);
    explicit luaValue(std::map<int, luaValue> val);
    explicit luaValue(std::function<luaValue(const std::vector<luaValue>&)> val);

    LuaType type() const { return type_; }
    bool is_truthy() const;

    luaValue operator+(const luaValue& other) const;
    luaValue operator-(const luaValue& other) const;
    luaValue operator*(const luaValue& other) const;
    luaValue operator/(const luaValue& other) const;
    
    template<typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
    luaValue operator+(T rhs) const { return *this + luaValue(static_cast<double>(rhs)); }
    template<typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
    luaValue operator-(T rhs) const { return *this - luaValue(static_cast<double>(rhs)); }
    template<typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
    luaValue operator*(T rhs) const { return *this * luaValue(static_cast<double>(rhs)); }
    template<typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
    luaValue operator/(T rhs) const { return *this / luaValue(static_cast<double>(rhs)); }

    bool operator==(const luaValue& other) const;
    bool operator!=(const luaValue& other) const;
    bool operator<(const luaValue& other) const;
    bool operator<=(const luaValue& other) const;
    bool operator>(const luaValue& other) const;
    bool operator>=(const luaValue& other) const;
    
    // luaValue operator+(double other) const;
    // luaValue operator-(double other) const;
    // luaValue operator*(double other) const;
    // luaValue operator/(double other) const;

    luaValue& operator[](int index);
    luaValue& operator[](const std::string& key);
    luaValue& operator[](const luaValue& key);
    const luaValue& operator[](int index) const;
    const luaValue& operator[](const std::string& key) const;
    const luaValue& operator[](const luaValue& key) const;

    luaValue operator()(const std::vector<luaValue>& args) const;

    operator double() const { return as_number(); }
    explicit operator int() const { return static_cast<int>(as_number()); }
    
    operator bool() const { return is_truthy(); }

    double as_number() const;
    std::string as_string() const;

    static luaValue new_table();
};

template<typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
inline luaValue operator+(T lhs, const luaValue& rhs) { 
    return luaValue(static_cast<double>(lhs)) + rhs; 
}
template<typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
inline luaValue operator-(T lhs, const luaValue& rhs) { 
    return luaValue(static_cast<double>(lhs)) - rhs; 
}
template<typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
inline luaValue operator*(T lhs, const luaValue& rhs) { 
    return luaValue(static_cast<double>(lhs)) * rhs; 
}
template<typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
inline luaValue operator/(T lhs, const luaValue& rhs) { 
    return luaValue(static_cast<double>(lhs)) / rhs; 
}
