#pragma once
#include <iostream>
#include <cmath>
#include <string>
#include <vector>
#include <unordered_map>
#include <sstream>
#include <cstdio>

using NUMBER = double;
using STRING = std::string;
using BOOLEAN = bool;

struct TABLE {
    static constexpr int ARRAY_INITIAL_SIZE = 8;
    
    std::vector<TABLE> array;
    std::unordered_map<int, TABLE> hash;
    std::unordered_map<STRING, TABLE> str_hash;
    
    double num = 0;
    std::string str;

    TABLE() {
        array.reserve(ARRAY_INITIAL_SIZE);
    }

    TABLE(double v) : num(v) {}
    TABLE(int v) : num(static_cast<double>(v)) {}
    TABLE(const char* v) : str(v) {}
    TABLE(const std::string& v) : str(v) {}

    operator double() const { return num; }
    explicit operator bool() const { return true; }

    TABLE& operator=(double v) { num = v; str.clear(); return *this; }
    TABLE& operator=(int v) { num = static_cast<double>(v); str.clear(); return *this; }
    TABLE& operator=(const char* v) { str = v; num = 0; return *this; }
    TABLE& operator=(const std::string& v) { str = v; num = 0; return *this; }

    TABLE& operator[](int index) {
        if (index >= 1 && index < 64) {
            if (index >= static_cast<int>(array.size())) {
                array.resize(index + 1);
            }
            return array[index];
        }
        return hash[index];
    }

    const TABLE& operator[](int index) const {
        if (index >= 1 && index < static_cast<int>(array.size())) {
            return array[index];
        }
        static TABLE nil;
        auto it = hash.find(index);
        return it != hash.end() ? it->second : nil;
    }

    TABLE& operator[](const std::string& key) {
        return str_hash[key];
    }

    const TABLE& operator[](const std::string& key) const {
        static TABLE nil;
        auto it = str_hash.find(key);
        return it != str_hash.end() ? it->second : nil;
    }

    int get_length() const {
        int len = 0;
        for (int i = 1; i < static_cast<int>(array.size()); ++i) {
            if (array[i].num != 0 || !array[i].str.empty() || !array[i].array.empty()) {
                len = i;
            }
        }
        return len;
    }
};

#define NEW_TABLE TABLE()

namespace l2c {
    void print(const TABLE& value);
    TABLE tonumber(const TABLE& value);
    TABLE tostring(const TABLE& value);
    TABLE string_format(const std::string& fmt, const TABLE& value);
    NUMBER math_sqrt(const TABLE& value);
    void io_write(const TABLE& value);
}
