#pragma once

#include <string>
#include <vector>
#include <iostream>
#include <map>
#include <functional>
#include <utility>
#include <cmath>

// Basic type aliases
using NUMBER = double;
using STRING = std::string;
using BOOLEAN = bool;

// Table class supporting both int and string indexing
class Table {
private:
    std::map<std::string, Table> string_keys;
    std::map<int, Table> int_keys;
    std::map<std::string, NUMBER> string_values;
    std::map<int, NUMBER> int_values;
    bool _has_value = false;

public:
    Table() = default;

    // Truthiness check
    operator bool() const { return true; }

    // Indexing with string key
    Table& operator[](const std::string& key);
    const Table& operator[](const std::string& key) const;

    // Indexing with const char* key
    Table& operator[](const char* key);
    const Table& operator[](const char* key) const;

    // Indexing with int key
    Table& operator[](int key);
    const Table& operator[](int key) const;

    // Assign string values
    Table& operator=(const STRING& value);
    Table& operator=(NUMBER value);

    // Get values
    bool has_string_key(const std::string& key) const;
    bool has_int_key(int key) const;
    STRING get_string(const std::string& key) const;
    NUMBER get_number(int key) const;
};

using TABLE = Table;
#define NEW_TABLE Table()

// Lua-like namespace stub functions
namespace l2c {
    // Stub functions - do nothing, just for syntax checking
    // Template overloads to accept any type
    template<typename... Args>
    void print(Args&&... args) {}

    template<typename T>
    NUMBER tonumber(const T&) { return 0; }

    template<typename T>
    STRING tostring(const T&) { return ""; }

    template<typename T>
    void assert(const T&) {}

    int get_length(const TABLE& table);
    int get_length(const STRING& str);
}

// IO stub struct
struct io {
    template<typename... Args>
    static void write(Args&&...) {}
};

// String library stub
struct string_lib {
    template<typename... Args>
    static STRING format(Args&&...) { return ""; }
};

// Math library stub
struct math_lib {
    template<typename T>
    static NUMBER sqrt(const T&) { return 0; }
    template<typename T>
    static NUMBER floor(const T&) { return 0; }
    template<typename T>
    static NUMBER ceil(const T&) { return 0; }
    static NUMBER pi() { return 3.14159265358979; }
    static NUMBER random() { return 0.5; }
    template<typename T>
    static NUMBER ifloor(const T&) { return 0; }
};

// Table library stub
struct table_lib {
    template<typename T>
    static void sort(T&) {}
    template<typename... Args>
    static STRING concat(Args&&...) { return ""; }
};

// Truthiness helper template - C++17 compatible (no auto... syntax)
template<typename... Args>
bool is_truthy(Args&&...) {
    return true;   // Always true for stub
}
