#pragma once
// Minimal stub for integration test syntax checking - NO runtime dependency
#include <string>
#include <vector>
#include <iostream>
#include <functional>

// Stub types
using NUMBER = double;
using STRING = std::string;
using BOOLEAN = bool;
using TABLE = void*;
using ANY = void*;
struct State {};

// Stub macros
#define NEW_TABLE nullptr

// Stub namespace functions - just enough for syntax checking
namespace l2c {
    inline void print(auto...) { }
    inline void tonumber(auto...) { }
    inline void tostring(auto...) { }
    inline NUMBER get_length(State*, ANY) { return 0; }
}

// Stub struct definitions for library modules
struct io {
    static void write(auto...) { }
};
struct string_lib {
    static STRING format(auto...) { return ""; }
    static NUMBER len(auto...) { return 0; }
};
struct math_lib {
    static NUMBER sqrt(auto...) { return 0; }
};
struct table_lib {
    static void sort(auto...) { }
    static STRING concat(auto...) { return ""; }
};
