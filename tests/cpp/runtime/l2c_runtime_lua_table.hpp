#pragma once

/**
 * l2c_runtime_lua_table.hpp - Lightweight Lua runtime using TValue/LuaTable
 * 
 * This runtime uses the high-performance NaN-boxed TValue and Swiss Table
 * implementation from lua_table.hpp instead of the heavyweight TABLE struct.
 * API is compatible with transpiler output.
 */

#include "lua_table.hpp"
#include <iostream>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <cstring>
#include <cstdio>
#include <functional>
#include <utility>
#include <vector>
#include <string>

#ifdef assert
#undef assert
#endif

// ============================================================
// Type aliases for transpiler compatibility
// ============================================================
using TABLE = TValue;
using NUMBER = double;
using STRING = const char*;
using BOOLEAN = bool;

// ============================================================
// Macros for table initialization
// ============================================================
#define NEW_TABLE TValue::Table(LuaTable::create(8, 4))
#define NIL TValue::Nil()

// ============================================================
// Detail namespace - helper functions for type conversion
// ============================================================
namespace detail {
    inline TValue to_tvalue(TValue v) { return v; }
    inline TValue to_tvalue(double d) { return TValue::Number(d); }
    inline TValue to_tvalue(int i) { return TValue::Integer(i); }
    inline TValue to_tvalue(const char* s) { return TValue::String(s); }
    inline TValue to_tvalue(bool b) { return TValue::Boolean(b); }
}

// Include OOP support after TABLE definition
#include "object.hpp"

// ============================================================
// l2c namespace - core runtime functions
// ============================================================
namespace l2c {

// ---------- Truthiness ----------
inline bool is_truthy(const TValue& t) {
    return !t.isFalsy();
}

inline bool is_truthy(double d) { return d != 0; }
inline bool is_truthy(bool b) { return b; }
inline bool is_truthy(const char* s) { return s != nullptr && s[0] != '\0'; }
inline bool is_truthy(const TableSlotProxy& p) { return is_truthy(static_cast<TValue>(p)); }

// ---------- Print helpers ----------
inline void print_single(const TValue& value) {
    uint64_t tag = value.bits & TValue::TAG_MASK;
    
    if ((value.bits & TValue::NANBOX_BASE) != TValue::NANBOX_BASE) {
        // It's a double (not NaN-boxed special)
        std::cout << value.toNumber();
    } else {
        switch (tag) {
            case TValue::TAG_NIL:
                std::cout << "nil";
                break;
            case TValue::TAG_FALSE:
                std::cout << "false";
                break;
            case TValue::TAG_TRUE:
                std::cout << "true";
                break;
            case TValue::TAG_STRING:
                std::cout << static_cast<const char*>(value.toPtr());
                break;
            case TValue::TAG_INT:
                std::cout << value.toInteger();
                break;
            case TValue::TAG_TABLE:
                std::cout << "table: " << value.toTable();
                break;
            case TValue::TAG_LIGHTUD:
                std::cout << "userdata: " << value.toPtr();
                break;
            case TValue::TAG_FUNCTION:
                std::cout << "function: " << value.toPtr();
                break;
            default:
                std::cout << "unknown";
                break;
        }
    }
}

inline void io_write_single(const TValue& value) {
    print_single(value);
}

// ---------- Variadic print ----------
template<typename... Args>
void print(Args&&... args) {
    (print_single(args), ...);
    std::cout << std::endl;
}

template<typename... Args>
void io_write(Args&&... args) {
    (io_write_single(args), ...);
}

// ---------- Type conversion ----------
inline TValue tonumber(const TValue& value) {
    // If it's already a number, return as-is
    if (value.isNumber()) {
        return value;
    }
    // If it's an integer, convert to double
    if (value.isInteger()) {
        return TValue::Number(static_cast<double>(value.toInteger()));
    }
    // If it's a string, try to parse as number
    if (value.isString()) {
        const char* s = static_cast<const char*>(value.toPtr());
        char* end;
        double d = std::strtod(s, &end);
        if (end != s && *end == '\0') {
            return TValue::Number(d);
        }
    }
    return NIL;
}

inline TValue tostring(const TValue& value) {
    uint64_t tag = value.bits & TValue::TAG_MASK;
    
    if ((value.bits & TValue::NANBOX_BASE) != TValue::NANBOX_BASE) {
        // It's a double
        static char buf[64];
        std::snprintf(buf, sizeof(buf), "%g", value.toNumber());
        return TValue::String(buf);
    }
    
    if (value.isString()) {
        return value;  // Already a string
    }
    
    if (value.isInteger()) {
        static char buf[32];
        std::snprintf(buf, sizeof(buf), "%d", value.toInteger());
        return TValue::String(buf);
    }
    
    switch (tag) {
        case TValue::TAG_NIL:
            return TValue::String("nil");
        case TValue::TAG_FALSE:
            return TValue::String("false");
        case TValue::TAG_TRUE:
            return TValue::String("true");
        case TValue::TAG_TABLE: {
            static char buf[64];
            std::snprintf(buf, sizeof(buf), "table: %p", value.toTable());
            return TValue::String(buf);
        }
        default:
            return TValue::String("unknown");
    }
}

// ---------- Length ----------
inline NUMBER get_length(const TValue& t) {
    if (t.isTable()) {
        return static_cast<NUMBER>(t.toTable()->length());
    }
    if (t.isString()) {
        const char* s = static_cast<const char*>(t.toPtr());
        return static_cast<NUMBER>(std::strlen(s));
    }
    return 0;
}

inline NUMBER get_length(const char* s) {
    return static_cast<NUMBER>(std::strlen(s));
}

// ---------- Math functions ----------
inline NUMBER math_sqrt(const TValue& value) {
    if (value.isNumber()) return std::sqrt(value.toNumber());
    if (value.isInteger()) return std::sqrt(static_cast<double>(value.toInteger()));
    return std::nan("");
}

inline NUMBER math_sqrt(NUMBER x) { return std::sqrt(x); }
inline NUMBER math_floor(NUMBER x) { return std::floor(x); }
inline NUMBER math_ceil(NUMBER x) { return std::ceil(x); }
inline NUMBER math_abs(NUMBER x) { return std::fabs(x); }

inline NUMBER math_random(NUMBER min = 0.0, NUMBER max = 1.0) {
    static bool seeded = false;
    if (!seeded) {
        std::srand(static_cast<unsigned>(std::time(nullptr)));
        seeded = true;
    }
    NUMBER scale = static_cast<NUMBER>(std::rand()) / RAND_MAX;
    return min + scale * (max - min);
}

// ---------- Lua modulo (with correct sign) ----------
inline NUMBER mod(NUMBER a, NUMBER b) {
    if (b == 0) return std::nan("");
    NUMBER r = std::fmod(a, b);
    if ((a < 0) != (b < 0) && r != 0) r += b;
    return r;
}

// ---------- String functions ----------
inline bool is_int_format(const char* fmt) {
    const char* p = fmt;
    if (*p != '%') return false;
    p++;
    while (*p == '-' || *p == '+' || *p == ' ' || *p == '#' || *p == '0') p++;
    while (*p >= '0' && *p <= '9') p++;
    if (*p == '.') { p++; while (*p >= '0' && *p <= '9') p++; }
    if (*p == 'l' || *p == 'h' || *p == 'L') p++;
    return (*p == 'd' || *p == 'i' || *p == 'x' || *p == 'X' || *p == 'o' || *p == 'u');
}

inline TValue string_format_single(const char* fmt, const TValue& value) {
    static char buf[1024];
    if (value.isNumber()) {
        double num = value.toNumber();
        if (is_int_format(fmt)) {
            std::snprintf(buf, sizeof(buf), fmt, static_cast<long long>(num));
        } else {
            std::snprintf(buf, sizeof(buf), fmt, num);
        }
    } else if (value.isInteger()) {
        std::snprintf(buf, sizeof(buf), fmt, value.toInteger());
    } else if (value.isString()) {
        std::snprintf(buf, sizeof(buf), fmt, static_cast<const char*>(value.toPtr()));
    } else {
        std::snprintf(buf, sizeof(buf), fmt, "?");
    }
    return TValue::String(buf);
}

inline TValue string_format(const char* fmt) {
    return TValue::String(fmt);
}

// Find the end of a format specifier (e.g., "%d", "%.2f", "%5s")
// Returns the position right after the specifier letter
inline size_t find_spec_end(const char* fmt) {
    size_t i = 0;
    if (fmt[i] != '%') return 0;
    i++; // skip '%'
    
    // Skip flags: -, +, space, #, 0
    while (fmt[i] == '-' || fmt[i] == '+' || fmt[i] == ' ' || fmt[i] == '#' || fmt[i] == '0') {
        i++;
    }
    
    // Skip width (digits or *)
    while (fmt[i] >= '0' && fmt[i] <= '9') {
        i++;
    }
    
    // Skip precision (.digits)
    if (fmt[i] == '.') {
        i++;
        while (fmt[i] >= '0' && fmt[i] <= '9') {
            i++;
        }
    }
    
    // Skip length modifier (l, ll, h, etc.)
    if (fmt[i] == 'l' || fmt[i] == 'h' || fmt[i] == 'L' || fmt[i] == 'z' || fmt[i] == 'j') {
        i++;
        if (fmt[i] == 'l') i++; // 'll'
    }
    
    // The conversion specifier letter
    if (fmt[i] != '\0') {
        i++;
    }
    
    return i;
}

template<typename T, typename... Args>
TValue string_format(const char* fmt, T&& first, Args&&... args) {
    static char result_buf[4096];
    
    size_t i = 0;
    while (fmt[i] != '\0') {
        if (fmt[i] == '%') {
            if (fmt[i + 1] == '%') {
                i += 2;
                continue;
            }
            size_t spec_end = find_spec_end(fmt + i);
            
            char spec[32];
            size_t spec_len = spec_end;
            if (spec_len >= sizeof(spec)) spec_len = sizeof(spec) - 1;
            std::memcpy(spec, fmt + i, spec_len);
            spec[spec_len] = '\0';
            
            TValue formatted = string_format_single(spec, detail::to_tvalue(first));
            const char* formatted_str = static_cast<const char*>(formatted.toPtr());
            
            std::snprintf(result_buf, sizeof(result_buf), "%.*s%s",
                (int)i, fmt, formatted_str);
            size_t prefix_len = std::strlen(result_buf);
            
            if constexpr (sizeof...(args) > 0) {
                TValue rest = string_format(fmt + i + spec_end, std::forward<Args>(args)...);
                std::snprintf(result_buf + prefix_len, sizeof(result_buf) - prefix_len, "%s",
                    static_cast<const char*>(rest.toPtr()));
            } else {
                std::strncpy(result_buf + prefix_len, fmt + i + spec_end, sizeof(result_buf) - prefix_len - 1);
                result_buf[sizeof(result_buf) - 1] = '\0';
            }
            
            return TValue::String(result_buf);
        }
        i++;
    }
    
    return TValue::String(fmt);
}

inline TValue string_find(const char* s, const char* pattern, NUMBER init = 1) {
    int len = static_cast<int>(std::strlen(s));
    int start = static_cast<int>(init) - 1;
    if (start < 0) start = 0;
    if (start > len) start = len;
    
    const char* pos = std::strstr(s + start, pattern);
    if (pos != nullptr) {
        LuaTable* result = LuaTable::create(2, 0);
        result->set(1, TValue::Integer(static_cast<int>(pos - s) + 1));
        result->set(2, TValue::Integer(static_cast<int>(pos - s) + std::strlen(pattern)));
        return TValue::Table(result);
    }
    return NIL;
}

inline NUMBER string_len(const char* s) {
    return static_cast<NUMBER>(std::strlen(s));
}

inline const char* string_sub(const char* s, NUMBER i, NUMBER j = -1) {
    int len = static_cast<int>(std::strlen(s));
    int start = (i < 0) ? len + static_cast<int>(i) : static_cast<int>(i) - 1;
    int end = (j < 0) ? len + static_cast<int>(j) : static_cast<int>(j) - 1;
    if (start < 0) start = 0;
    if (end >= len) end = len - 1;
    if (start > end || len == 0) return "";
    
    static char buf[4096];
    int sublen = end - start + 1;
    std::memcpy(buf, s + start, sublen);
    buf[sublen] = '\0';
    return buf;
}

// ---------- Table functions ----------
inline void table_insert(TValue& t, const TValue& value) {
    if (!t.isTable()) return;
    LuaTable* tbl = t.toTable();
    int len = static_cast<int>(tbl->length());
    tbl->set(len + 1, value);
}

inline void table_insert(TValue& t, NUMBER pos, const TValue& value) {
    if (!t.isTable()) return;
    LuaTable* tbl = t.toTable();
    int idx = static_cast<int>(pos);
    int len = static_cast<int>(tbl->length());
    if (idx < 1) idx = 1;
    if (idx > len + 1) idx = len + 1;
    
    // Shift elements up
    for (int i = len; i >= idx; --i) {
        tbl->set(i + 1, tbl->get(i));
    }
    tbl->set(idx, value);
}

inline void table_sort(TValue& t, std::function<bool(const TValue&, const TValue&)> comparator = nullptr) {
    if (!t.isTable()) return;
    LuaTable* tbl = t.toTable();
    int len = static_cast<int>(tbl->length());
    if (len <= 1) return;
    
    auto default_less = [](const TValue& a, const TValue& b) -> bool {
        if (a.isNumber() && b.isNumber()) return a.toNumber() < b.toNumber();
        if (a.isInteger() && b.isInteger()) return a.toInteger() < b.toInteger();
        if (a.isString() && b.isString()) {
            return std::strcmp(static_cast<const char*>(a.toPtr()), 
                              static_cast<const char*>(b.toPtr())) < 0;
        }
        return a.bits < b.bits;
    };
    
    auto comp = comparator ? comparator : default_less;
    
    // Insertion sort
    for (int i = 2; i <= len; ++i) {
        TValue key = tbl->get(i);
        int j = i - 1;
        while (j >= 1 && comp(key, tbl->get(j))) {
            tbl->set(j + 1, tbl->get(j));
            --j;
        }
        tbl->set(j + 1, key);
    }
}

inline TValue table_remove(TValue& t, NUMBER pos = 1) {
    if (!t.isTable()) return NIL;
    LuaTable* tbl = t.toTable();
    int idx = static_cast<int>(pos);
    int len = static_cast<int>(tbl->length());
    if (idx < 1 || idx > len) return NIL;
    TValue removed = tbl->get(idx);
    for (int i = idx; i < len; i++) {
        tbl->set(i, tbl->get(i + 1));
    }
    tbl->set(len, NIL);
    return removed;
}

inline std::vector<TValue> table_unpack(TValue& t, NUMBER first = 1, NUMBER last = -1) {
    std::vector<TValue> result;
    if (!t.isTable()) return result;
    LuaTable* tbl = t.toTable();
    int len = static_cast<int>(tbl->length());
    int start = static_cast<int>(first);
    int end = (last < 0) ? len : static_cast<int>(last);
    for (int i = start; i <= end && i <= len; i++) {
        result.push_back(tbl->get(i));
    }
    return result;
}

// ---------- I/O functions ----------
inline TValue io_read(const char* format = "*a") {
    static char buf[1048576];  // 1MB buffer
    if (std::strcmp(format, "*a") == 0) {
        std::string all;
        char line[4096];
        while (std::fgets(line, sizeof(line), stdin)) {
            all += line;
        }
        std::strncpy(buf, all.c_str(), sizeof(buf) - 1);
        buf[sizeof(buf) - 1] = '\0';
    } else if (std::strcmp(format, "*l") == 0) {
        if (!std::fgets(buf, sizeof(buf), stdin)) {
            return NIL;
        }
        size_t len = std::strlen(buf);
        if (len > 0 && buf[len - 1] == '\n') buf[len - 1] = '\0';
    } else {
        buf[0] = '\0';
    }
    return TValue::String(buf);
}

// ---------- OS functions ----------
inline NUMBER os_clock() {
    return static_cast<NUMBER>(std::clock()) / CLOCKS_PER_SEC;
}

inline std::pair<TValue, TValue> next(TValue& t, const TValue& key = NIL) {
    if (!t.isTable()) return {NIL, NIL};
    
    LuaTable* tbl = t.toTable();
    TValue k = key;
    TValue v;
    
    if (tbl->next(k, v)) {
        return {k, v};
    }
    return {NIL, NIL};
}

// ---------- Type function ----------
inline const char* type(const TValue& t) {
    uint64_t tag = t.bits & TValue::TAG_MASK;
    
    if ((t.bits & TValue::NANBOX_BASE) != TValue::NANBOX_BASE) {
        return "number";
    }
    
    switch (tag) {
        case TValue::TAG_NIL:     return "nil";
        case TValue::TAG_FALSE:   
        case TValue::TAG_TRUE:    return "boolean";
        case TValue::TAG_STRING:  return "string";
        case TValue::TAG_INT:     return "number";
        case TValue::TAG_TABLE:   return "table";
        case TValue::TAG_FUNCTION: return "function";
        case TValue::TAG_LIGHTUD: return "userdata";
        default: return "userdata";
    }
}

inline const char* type(double) { return "number"; }
inline const char* type(const char*) { return "string"; }
inline const char* type(std::nullptr_t) { return "nil"; }
inline const char* type(bool) { return "boolean"; }

// ---------- Assert ----------
inline void assert(bool cond) {
    if (!cond) {
        std::cerr << "assertion failed" << std::endl;
        std::abort();
    }
}

// ---------- Protected call ----------
template<typename Func, typename... Args>
std::pair<bool, TValue> pcall(Func func, Args... args) {
    try {
        TValue result = func(args...);
        return {true, result};
    } catch (...) {
        return {false, TValue::String("error in protected call")};
    }
}

// ---------- Garbage collection ----------
inline void collectgarbage() { }

// ---------- Debug functions ----------
inline TValue debug_getinfo(NUMBER, const char*) {
    return TValue::Table(LuaTable::create(0, 4));
}

// ---------- Math min/max ----------
inline NUMBER math_min(NUMBER a, NUMBER b) { return std::fmin(a, b); }
inline NUMBER math_max(NUMBER a, NUMBER b) { return std::fmax(a, b); }

    // ---------- Metatable stub ----------
inline TValue setmetatable(TValue t, const TValue& mt) {
        return t;
    }

    // ---------- Load stubs ----------
    inline TValue loadstring(const char*) { return NIL; }
    inline TValue load(const char*) { return NIL; }

    // ---------- OS exit ----------
    inline void os_exit(NUMBER code = 0) {
        std::exit(static_cast<int>(code));
    }

    // ---------- Pi constant ----------
    constexpr NUMBER pi = 3.14159265358979323846;

} // namespace l2c

// ============================================================
// jit namespace
// ============================================================
namespace jit {
    inline TValue off() { return NIL; }
}

// ============================================================
// io namespace
// ============================================================
namespace io {
    template<typename... Args>
    void write(Args&&... args) {
        l2c::io_write(std::forward<Args>(args)...);
    }
}

// ============================================================
// math_lib namespace
// ============================================================
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
        if (!seeded) {
            std::srand(static_cast<unsigned>(std::time(nullptr)));
            seeded = true;
        }
        NUMBER scale = static_cast<NUMBER>(std::rand()) / RAND_MAX;
        return min + scale * (max - min);
    }
    
    inline NUMBER min(NUMBER a, NUMBER b) { return std::fmin(a, b); }
    inline NUMBER max(NUMBER a, NUMBER b) { return std::fmax(a, b); }
    
    constexpr NUMBER pi = 3.14159265358979323846;
    
    inline NUMBER huge() { return INFINITY; }
}

// ============================================================
// string_lib namespace
// ============================================================
namespace string_lib {
    inline const char* format(const char* fmt) { return fmt; }
    
    template<typename... Args>
    const char* format(const char* fmt, Args&&... args) {
        TValue t = l2c::string_format(fmt, std::forward<Args>(args)...);
        return static_cast<const char*>(t.toPtr());
    }
    
    inline NUMBER byte(const char* s, int i = 1) {
        int len = static_cast<int>(std::strlen(s));
        if (i >= 1 && i <= len) {
            return static_cast<NUMBER>(static_cast<unsigned char>(s[i - 1]));
        }
        return 0;
    }
    
    inline const char* char_(NUMBER c) {
        static char buf[2];
        buf[0] = static_cast<char>(c);
        buf[1] = '\0';
        return buf;
    }
    
    inline NUMBER len(const char* s) {
        return static_cast<NUMBER>(std::strlen(s));
    }
    
    inline const char* sub(const char* s, NUMBER i, NUMBER j = -1) {
        return l2c::string_sub(s, i, j);
    }
    
    inline TValue upper(const TValue& s) {
        if (!s.isString()) return s;
        const char* str = static_cast<const char*>(s.toPtr());
        static char buf[4096];
        size_t len = std::strlen(str);
        for (size_t i = 0; i < len && i < sizeof(buf) - 1; i++) {
            buf[i] = static_cast<char>(std::toupper(static_cast<unsigned char>(str[i])));
        }
        buf[len] = '\0';
        return TValue::String(buf);
    }

    inline TValue gsub(const TValue& s, const TValue& pattern, const TValue& replacement) {
        if (!s.isString()) return s;
        const char* str = static_cast<const char*>(s.toPtr());
        const char* pat = pattern.isString() ? static_cast<const char*>(pattern.toPtr()) : "";
        const char* repl = replacement.isString() ? static_cast<const char*>(replacement.toPtr()) : "";
        
        static char buf[16384];
        size_t pat_len = std::strlen(pat);
        if (pat_len == 0) {
            std::strncpy(buf, str, sizeof(buf) - 1);
            buf[sizeof(buf) - 1] = '\0';
            return TValue::String(buf);
        }
        
        std::string result;
        const char* pos = str;
        while (*pos) {
            const char* found = std::strstr(pos, pat);
            if (!found) {
                result += pos;
                break;
            }
            result += std::string(pos, found - pos);
            result += repl;
            pos = found + pat_len;
        }
        std::strncpy(buf, result.c_str(), sizeof(buf) - 1);
        buf[sizeof(buf) - 1] = '\0';
        return TValue::String(buf);
    }
}

// ============================================================
// table_lib namespace
// ============================================================
namespace table_lib {
    inline const char* concat(const char* a, const char* b) {
        static char buf[8192];
        int la = static_cast<int>(std::strlen(a));
        int lb = static_cast<int>(std::strlen(b));
        std::memcpy(buf, a, la);
        std::memcpy(buf + la, b, lb + 1);
        return buf;
    }
    
    // For convenience, also provide overloads for TValue strings
    inline const char* concat(const TValue& a, const TValue& b) {
        const char* sa = a.isString() ? static_cast<const char*>(a.toPtr()) : "";
        const char* sb = b.isString() ? static_cast<const char*>(b.toPtr()) : "";
        return concat(sa, sb);
    }
}

// ============================================================
// END l2c_runtime_lua_table.hpp
// ============================================================
