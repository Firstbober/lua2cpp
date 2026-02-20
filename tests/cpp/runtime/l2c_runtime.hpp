#pragma once
#include <iostream>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <string>
#include <vector>
#include <unordered_map>
#include <sstream>
#include <cstdio>

#ifdef assert
#undef assert
#endif

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

    TABLE& operator[](const char* key) {
        return str_hash[key];
    }

    const TABLE& operator[](const char* key) const {
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
#define NIL TABLE()

namespace l2c {
    inline bool is_truthy(const TABLE& t) {
        return t.num != 0 || !t.str.empty() || !t.array.empty() || !t.hash.empty() || !t.str_hash.empty();
    }
    inline bool is_truthy(double d) { return d != 0; }
    inline bool is_truthy(bool b) { return b; }
    inline bool is_truthy(const std::string& s) { return !s.empty(); }
    
    void print_single(const TABLE& value);
    TABLE tonumber(const TABLE& value);
    TABLE tostring(const TABLE& value);
    TABLE string_format_single(const std::string& fmt, const TABLE& value);
    NUMBER math_sqrt(const TABLE& value);
    void io_write_single(const TABLE& value);
    
    inline NUMBER get_length(const TABLE& t) { return static_cast<NUMBER>(t.get_length()); }
    inline NUMBER get_length(const std::string& s) { return static_cast<NUMBER>(s.size()); }
    inline NUMBER math_floor(NUMBER x) { return std::floor(x); }
    inline NUMBER math_ceil(NUMBER x) { return std::ceil(x); }
    inline NUMBER math_abs(NUMBER x) { return std::fabs(x); }
    NUMBER math_random(NUMBER min = 0.0, NUMBER max = 1.0);
    
    inline void assert(bool cond) {
        if (!cond) {
            std::cerr << "assertion failed" << std::endl;
            std::abort();
        }
    }
    
    template<typename... Args>
    void print(Args&&... args) {
        (print_single(args), ...);
        std::cout << std::endl;
    }
    
    template<typename... Args>
    void io_write(Args&&... args) {
        (io_write_single(args), ...);
    }
    
    inline TABLE string_format(const std::string& fmt) {
        TABLE result;
        result.str = fmt;
        return result;
    }
    
    template<typename T, typename... Args>
    TABLE string_format(const std::string& fmt, T&& first, Args&&... args) {
        return string_format_single(fmt, first);
    }
    
    inline NUMBER mod(NUMBER a, NUMBER b) {
        if (b == 0) return std::nan("");
        NUMBER r = std::fmod(a, b);
        if ((a < 0) != (b < 0) && r != 0) r += b;
        return r;
    }
}

namespace io {
    template<typename... Args>
    void write(Args&&... args) {
        l2c::io_write(std::forward<Args>(args)...);
    }
}

namespace math_lib {
    inline NUMBER sqrt(NUMBER x) { return std::sqrt(x); }
    inline NUMBER floor(NUMBER x) { return std::floor(x); }
    inline NUMBER ceil(NUMBER x) { return std::ceil(x); }
    inline NUMBER abs(NUMBER x) { return std::fabs(x); }
    inline NUMBER sin(NUMBER x) { return std::sin(x); }
    inline NUMBER cos(NUMBER x) { return std::cos(x); }
    inline NUMBER tan(NUMBER x) { return std::tan(x); }
    inline NUMBER log(NUMBER x) { return std::log(x); }
    inline NUMBER exp(NUMBER x) { return std::exp(x); }
    inline NUMBER pow(NUMBER x, NUMBER y) { return std::pow(x, y); }
    inline NUMBER fmod(NUMBER x, NUMBER y) { return std::fmod(x, y); }
    inline NUMBER random(NUMBER min = 0.0, NUMBER max = 1.0) {
        static bool seeded = false;
        if (!seeded) { std::srand(static_cast<unsigned>(std::time(nullptr))); seeded = true; }
        NUMBER scale = static_cast<NUMBER>(std::rand()) / RAND_MAX;
        return min + scale * (max - min);
    }
    inline NUMBER min(NUMBER a, NUMBER b) { return std::fmin(a, b); }
    inline NUMBER max(NUMBER a, NUMBER b) { return std::fmax(a, b); }
    constexpr NUMBER pi = 3.14159265358979323846;
    inline NUMBER huge() { return INFINITY; }
}

namespace string_lib {
    inline std::string format(const std::string& fmt) { return fmt; }
    template<typename... Args>
    std::string format(const std::string& fmt, Args&&... args) {
        TABLE t = l2c::string_format(fmt, std::forward<Args>(args)...);
        return t.str;
    }
    inline NUMBER byte(const std::string& s, int i = 1) {
        if (i >= 1 && i <= static_cast<int>(s.size())) return static_cast<NUMBER>(static_cast<unsigned char>(s[i-1]));
        return 0;
    }
    inline std::string char_(NUMBER c) {
        return std::string(1, static_cast<char>(c));
    }
    inline NUMBER len(const std::string& s) { return static_cast<NUMBER>(s.size()); }
    inline std::string sub(const std::string& s, NUMBER i, NUMBER j = -1) {
        int start = static_cast<int>(i) - 1;
        int end = (j < 0) ? static_cast<int>(s.size()) : static_cast<int>(j);
        if (start < 0) start = 0;
        if (end > static_cast<int>(s.size())) end = static_cast<int>(s.size());
        if (start >= end) return "";
        return s.substr(start, end - start);
    }
}

namespace table_lib {
    inline std::string concat(const std::string& a, const std::string& b) {
        return a + b;
    }
    inline std::string concat(const char* a, const std::string& b) {
        return std::string(a) + b;
    }
    inline std::string concat(const std::string& a, const char* b) {
        return a + std::string(b);
    }
    inline std::string concat(const char* a, const char* b) {
        return std::string(a) + std::string(b);
    }
}
