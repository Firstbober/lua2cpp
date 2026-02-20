#pragma once
// Minimal working runtime header for simple.lua and spectral-norm.lua tests
#include <iostream>
#include <cmath>
#include <string>
#include <map>
#include <sstream>
#include <cstdio>

// Simplified types for runtime
using NUMBER = double;
using STRING = std::string;
using BOOLEAN = bool;

// TABLE struct with sparse array support for Lua-like indexing
struct TABLE {
    // Internal representation - sparse array for Lua tables
    std::map<int, TABLE> array;  // Numeric keys (1-indexed)
    std::map<STRING, TABLE> table;  // String keys

    // Default constructor
    TABLE() = default;

    // Value constructor (numeric/string)
    TABLE(double v) : num(v) {}
    TABLE(int v) : num(static_cast<double>(v)) {}
    TABLE(const char* v) : str(v) {}
    TABLE(const std::string& v) : str(v) {}

    // Numeric value for backwards compatibility
    double num = 0;
    std::string str;

    // Implicit conversion to double for numeric contexts
    operator double() const { return num; }
    
    // Boolean conversion for ternary and conditionals (Lua: only nil/false are falsy)
    explicit operator bool() const { return true; }  // Tables are always truthy

    // Assignment operators
    TABLE& operator=(double v) { num = v; str.clear(); return *this; }
    TABLE& operator=(int v) { num = static_cast<double>(v); str.clear(); return *this; }
    TABLE& operator=(const char* v) { str = v; num = 0; return *this; }
    TABLE& operator=(const std::string& v) { str = v; num = 0; return *this; }

    // Array indexing (numeric keys)
    TABLE& operator[](int index) {
        return array[index];
    }

    // Table indexing (string keys)
    TABLE& operator[](const std::string& key) {
        return table[key];
    }

    // Get value by numeric index (returns 0 for non-existent)
    TABLE get(int index) const {
        auto it = array.find(index);
        if (it != array.end()) {
            return it->second;
        }
        return TABLE(0);  // Return NIL-like value
    }

    // Get value by string key (returns empty TABLE for non-existent)
    TABLE get(const std::string& key) const {
        auto it = table.find(key);
        if (it != table.end()) {
            return it->second;
        }
        return TABLE();  // Return empty TABLE (NIL-like)
    }

    // Set numeric key
    void set(int index, const TABLE& value) {
        array[index] = value;
    }

    // Set string key
    void set(const std::string& key, const TABLE& value) {
        table[key] = value;
    }

    // Check if table is truthy
    bool is_truthy() const {
        if (!array.empty() || !table.empty()) {
            return true;
        }
        return num != 0;
    }

    // Get length (number of array elements)
    int get_length() const {
        int len = 0;
        for (const auto& [key, val] : array) {
            if (key > len) break;
            len = key;
        }
        return len;
    }
};

// NIL constant
extern const TABLE NIL;

// Macro for creating new table
#define NEW_TABLE TABLE()

// ===== Functions in l2c:: namespace =====
namespace l2c {
    void print(const TABLE& value);
    TABLE tonumber(const TABLE& value);
    TABLE tostring(const TABLE& value);
    TABLE string_format(const std::string& fmt, const TABLE& value);
    NUMBER math_sqrt(const TABLE& value);
    void io_write(const TABLE& value);
}
