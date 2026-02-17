#pragma once
// Minimal stub for integration test syntax checking - NO runtime dependency
#include <string>
#include <vector>
#include <iostream>
#include <functional>
#include <cmath>
#include <limits>

// Stub types - use double for everything to make syntax checking work
using NUMBER = double;
using STRING = std::string;
using BOOLEAN = bool;

// TABLE is a simple wrapper that can hold any value for syntax checking
struct TABLE {
    double num = 0;
    TABLE() = default;
    TABLE(double v) : num(v) {}
    TABLE(int v) : num(v) {}
    TABLE(const char*) {}
    TABLE(const std::string&) {}
    // Implicit conversion to double for numeric contexts
    operator double() const { return num; }
    TABLE& operator=(double v) { num = v; return *this; }
    TABLE& operator=(int v) { num = v; return *this; }
    TABLE& operator=(const char*) { return *this; }
    TABLE& operator=(const std::string&) { return *this; }
    TABLE operator[](int) { return *this; }
    TABLE operator[](const std::string&) { return *this; }
    bool is_truthy() const { return num != 0; }
};

using ANY = TABLE;
struct State {};

// Stub macros
#define NEW_TABLE TABLE()
constexpr TABLE NIL;

// Stub namespace functions - just enough for syntax checking
namespace l2c {
    // ===== GLOBAL FUNCTIONS =====
    template<typename... Args> inline TABLE print(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE tonumber(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE tostring(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE type(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE ipairs(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE pairs(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE next(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE error(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE assert(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE pcall(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE xpcall(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE select(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE collectgarbage(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE rawget(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE rawset(Args&&...) { return TABLE(); }
    template<typename... Args> inline NUMBER rawlen(Args&&...) { return 0; }
    template<typename... Args> inline TABLE getmetatable(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE setmetatable(Args&&...) { return TABLE(); }
    template<typename... Args> inline NUMBER get_length(Args&&...) { return 0; }
    template<typename... Args> inline bool is_truthy(Args&&...) { return true; }

    // ===== IO LIBRARY =====
    template<typename... Args> inline BOOLEAN io_close(Args&&...) { return true; }
    template<typename... Args> inline TABLE io_write(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE io_flush(Args&&...) { return TABLE(); }
    template<typename... Args> inline STRING io_input(Args&&...) { return ""; }
    template<typename... Args> inline TABLE io_lines(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE io_open(Args&&...) { return TABLE(); }
    template<typename... Args> inline STRING io_output(Args&&...) { return ""; }
    template<typename... Args> inline TABLE io_popen(Args&&...) { return TABLE(); }
    template<typename... Args> inline STRING io_read(Args&&...) { return ""; }
    template<typename... Args> inline STRING io_type(Args&&...) { return ""; }

    // ===== STRING LIBRARY =====
    template<typename... Args> inline NUMBER string_byte(Args&&...) { return 0; }
    template<typename... Args> inline STRING string_char(Args&&...) { return ""; }
    template<typename... Args> inline STRING string_dump(Args&&...) { return ""; }
    template<typename... Args> inline TABLE string_find(Args&&...) { return TABLE(); }
    template<typename... Args> inline STRING string_format(Args&&...) { return ""; }
    template<typename... Args> inline TABLE string_gmatch(Args&&...) { return TABLE(); }
    template<typename... Args> inline STRING string_gsub(Args&&...) { return ""; }
    template<typename... Args> inline NUMBER string_len(Args&&...) { return 0; }
    template<typename... Args> inline STRING string_lower(Args&&...) { return ""; }
    template<typename... Args> inline TABLE string_match(Args&&...) { return TABLE(); }
    template<typename... Args> inline STRING string_pack(Args&&...) { return ""; }
    template<typename... Args> inline NUMBER string_packsize(Args&&...) { return 0; }
    template<typename... Args> inline STRING string_rep(Args&&...) { return ""; }
    template<typename... Args> inline STRING string_reverse(Args&&...) { return ""; }
    template<typename... Args> inline STRING string_sub(Args&&...) { return ""; }
    template<typename... Args> inline TABLE string_unpack(Args&&...) { return TABLE(); }
    template<typename... Args> inline STRING string_upper(Args&&...) { return ""; }

    // ===== MATH LIBRARY =====
    template<typename... Args> inline NUMBER math_abs(Args&&... args) { return std::abs(args...); }
    template<typename... Args> inline NUMBER math_acos(Args&&... args) { return std::acos(args...); }
    template<typename... Args> inline NUMBER math_asin(Args&&... args) { return std::asin(args...); }
    template<typename... Args> inline NUMBER math_atan(Args&&... args) { return std::atan(args...); }
    template<typename... Args> inline NUMBER math_atan2(Args&&... args) { return std::atan2(args...); }
    template<typename... Args> inline NUMBER math_ceil(Args&&... args) { return std::ceil(args...); }
    template<typename... Args> inline NUMBER math_cos(Args&&... args) { return std::cos(args...); }
    template<typename... Args> inline NUMBER math_cosh(Args&&... args) { return std::cosh(args...); }
    template<typename... Args> inline NUMBER math_deg(Args&&...) { return 0; }
    template<typename... Args> inline NUMBER math_exp(Args&&... args) { return std::exp(args...); }
    template<typename... Args> inline NUMBER math_floor(Args&&... args) { return std::floor(args...); }
    template<typename... Args> inline NUMBER math_fmod(Args&&... args) { return std::fmod(args...); }
    template<typename... Args> inline NUMBER math_frexp(Args&&...) { return 0; }
    inline constexpr NUMBER math_huge = std::numeric_limits<double>::infinity();
    template<typename... Args> inline NUMBER math_ldexp(Args&&...) { return 0; }
    template<typename... Args> inline NUMBER math_log(Args&&... args) { return std::log(args...); }
    template<typename... Args> inline NUMBER math_log10(Args&&... args) { return std::log10(args...); }
    template<typename... Args> inline NUMBER math_max(Args&&...) { return 0; }
    inline constexpr NUMBER math_maxinteger = static_cast<NUMBER>(std::numeric_limits<long long>::max());
    template<typename... Args> inline NUMBER math_min(Args&&...) { return 0; }
    inline constexpr NUMBER math_mininteger = static_cast<NUMBER>(std::numeric_limits<long long>::min());
    template<typename... Args> inline NUMBER math_modf(Args&&...) { return 0; }
    inline constexpr NUMBER math_pi = 3.14159265358979323846;
    template<typename... Args> inline NUMBER math_pow(Args&&... args) { return std::pow(args...); }
    template<typename... Args> inline NUMBER math_rad(Args&&...) { return 0; }
    template<typename... Args> inline NUMBER math_random(Args&&...) { return 0; }
    template<typename... Args> inline NUMBER math_randomseed(Args&&...) { return 0; }
    template<typename... Args> inline NUMBER math_sin(Args&&... args) { return std::sin(args...); }
    template<typename... Args> inline NUMBER math_sinh(Args&&... args) { return std::sinh(args...); }
    template<typename... Args> inline NUMBER math_sqrt(Args&&... args) { return std::sqrt(args...); }
    template<typename... Args> inline NUMBER math_tan(Args&&... args) { return std::tan(args...); }
    template<typename... Args> inline NUMBER math_tanh(Args&&... args) { return std::tanh(args...); }
    template<typename... Args> inline NUMBER math_tointeger(Args&&...) { return 0; }
    template<typename... Args> inline STRING math_type(Args&&...) { return ""; }
    template<typename... Args> inline BOOLEAN math_ult(Args&&...) { return false; }

    // ===== TABLE LIBRARY =====
    template<typename... Args> inline STRING table_concat(Args&&...) { return ""; }
    template<typename... Args> inline TABLE table_insert(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE table_move(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE table_pack(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE table_remove(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE table_sort(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE table_unpack(Args&&...) { return TABLE(); }

    // ===== OS LIBRARY =====
    template<typename... Args> inline NUMBER os_clock(Args&&...) { return 0; }
    template<typename... Args> inline STRING os_date(Args&&...) { return ""; }
    template<typename... Args> inline NUMBER os_difftime(Args&&...) { return 0; }
    template<typename... Args> inline BOOLEAN os_execute(Args&&...) { return true; }
    template<typename... Args> inline BOOLEAN os_exit(Args&&...) { return true; }
    template<typename... Args> inline STRING os_getenv(Args&&...) { return ""; }
    template<typename... Args> inline BOOLEAN os_remove(Args&&...) { return true; }
    template<typename... Args> inline BOOLEAN os_rename(Args&&...) { return true; }
    template<typename... Args> inline STRING os_setlocale(Args&&...) { return ""; }
    template<typename... Args> inline NUMBER os_time(Args&&...) { return 0; }
    template<typename... Args> inline STRING os_tmpname(Args&&...) { return ""; }

    // ===== PACKAGE LIBRARY =====
    template<typename... Args> inline TABLE package_loadlib(Args&&...) { return TABLE(); }
    template<typename... Args> inline STRING package_searchpath(Args&&...) { return ""; }
    template<typename... Args> inline BOOLEAN package_seeall(Args&&...) { return true; }

    // ===== DEBUG LIBRARY =====
    template<typename... Args> inline BOOLEAN debug_debug(Args&&...) { return true; }
    template<typename... Args> inline TABLE debug_getfenv(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE debug_gethook(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE debug_getinfo(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE debug_getlocal(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE debug_getmetatable(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE debug_getregistry(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE debug_getupvalue(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE debug_getuservalue(Args&&...) { return TABLE(); }
    template<typename... Args> inline BOOLEAN debug_setfenv(Args&&...) { return true; }
    template<typename... Args> inline BOOLEAN debug_sethook(Args&&...) { return true; }
    template<typename... Args> inline STRING debug_setlocal(Args&&...) { return ""; }
    template<typename... Args> inline TABLE debug_setmetatable(Args&&...) { return TABLE(); }
    template<typename... Args> inline BOOLEAN debug_setupvalue(Args&&...) { return true; }
    template<typename... Args> inline BOOLEAN debug_setuservalue(Args&&...) { return true; }
    template<typename... Args> inline STRING debug_traceback(Args&&...) { return ""; }
    template<typename... Args> inline TABLE debug_upvalueid(Args&&...) { return TABLE(); }
    template<typename... Args> inline BOOLEAN debug_upvaluejoin(Args&&...) { return true; }

    // ===== COROUTINE LIBRARY =====
    template<typename... Args> inline TABLE coroutine_create(Args&&...) { return TABLE(); }
    template<typename... Args> inline BOOLEAN coroutine_isyieldable(Args&&...) { return true; }
    template<typename... Args> inline TABLE coroutine_resume(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE coroutine_running(Args&&...) { return TABLE(); }
    template<typename... Args> inline STRING coroutine_status(Args&&...) { return ""; }
    template<typename... Args> inline TABLE coroutine_wrap(Args&&...) { return TABLE(); }
    template<typename... Args> inline TABLE coroutine_yield(Args&&...) { return TABLE(); }
}

// Stub struct definitions for library modules
struct io {
    template<typename... Args> static void write(Args&&...) { }
};
struct string_lib {
    template<typename... Args> static STRING format(Args&&...) { return ""; }
    template<typename... Args> static NUMBER len(Args&&...) { return 0; }
};
struct math_lib {
    template<typename... Args> static NUMBER sqrt(Args&&...) { return 0; }
    template<typename... Args> static NUMBER floor(Args&&...) { return 0; }
    template<typename... Args> static NUMBER random(Args&&...) { return 0; }
    template<typename... Args> static NUMBER abs(Args&&...) { return 0; }
    template<typename... Args> static NUMBER ceil(Args&&...) { return 0; }
};
struct table_lib {
    template<typename... Args> static void sort(Args&&...) { }
    template<typename... Args> static STRING concat(Args&&...) { return ""; }
};
