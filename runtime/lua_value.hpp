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
    explicit luaValue(int val);
    explicit luaValue(double val);
    explicit luaValue(const char* val);
    explicit luaValue(const std::string& val);
    explicit luaValue(std::map<int, luaValue> val);
    explicit luaValue(std::function<luaValue(const std::vector<luaValue>&)> val);

    LuaType type() const { return type_; }
    bool is_truthy() const;

    luaValue operator+(const luaValue& other) const;
    luaValue operator-(const luaValue& other) const;
    luaValue operator*(const luaValue& other) const;
    luaValue operator/(const luaValue& other) const;

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

    double as_number() const;
    std::string as_string() const;

    static luaValue new_table();
};
