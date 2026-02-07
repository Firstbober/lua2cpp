#pragma once

#include "lua_value.hpp"
#include "lua_array.hpp"
#include "lua_table.hpp"
#include <vector>
#include <string>
#include <unordered_map>
#include <iostream>
#include <cmath>
#include <sstream>
#include <iomanip>
#include <ctime>
#include <algorithm>

namespace l2c {

// ============================================================================
// IO Library
// ============================================================================

inline void io_write(const std::vector<luaValue>& args) {
    for (const auto& arg : args) {
        std::cout << arg.as_string();
    }
}

inline std::string io_read(const std::string& format) {
    if (format == "*l" || format == "*L") {
        std::string line;
        std::getline(std::cin, line);
        return line;
    }
    return "";
}

inline void io_flush() {
    std::cout.flush();
}

// ============================================================================
// Math Library
// ============================================================================

inline double math_sqrt(double x) { return std::sqrt(x); }
inline double math_abs(double x) { return std::abs(x); }
inline double math_floor(double x) { return std::floor(x); }
inline double math_ceil(double x) { return std::ceil(x); }
inline double math_sin(double x) { return std::sin(x); }
inline double math_cos(double x) { return std::cos(x); }
inline double math_tan(double x) { return std::tan(x); }
inline double math_log(double x) { return std::log(x); }
inline double math_exp(double x) { return std::exp(x); }

inline double math_min(double a, double b) { return a < b ? a : b; }
inline double math_max(double a, double b) { return a > b ? a : b; }

inline double math_random() { return static_cast<double>(rand()) / RAND_MAX; }

inline double math_randomseed(double seed) {
    srand(static_cast<unsigned int>(seed));
    return 0;
}

// ============================================================================
// String Library
// ============================================================================

inline std::string string_format(const std::string& fmt, const std::vector<luaValue>& args) {
    std::ostringstream result;
    int pos = 1;
    size_t i = 0;

    while (i < fmt.size()) {
        if (fmt[i] == '%' && i + 1 < fmt.size()) {
            i++;
            std::string flags;
            int width = 0;
            int precision = -1;

            while (i < fmt.size() && (fmt[i] == '-' || fmt[i] == '+' || fmt[i] == ' ' || fmt[i] == '#' || fmt[i] == '0')) {
                flags += fmt[i++];
            }
            while (i < fmt.size() && isdigit(fmt[i])) {
                width = width * 10 + (fmt[i++] - '0');
            }
            if (i < fmt.size() && fmt[i] == '.') {
                i++;
                precision = 0;
                while (i < fmt.size() && isdigit(fmt[i])) {
                    precision = precision * 10 + (fmt[i++] - '0');
                }
            }
            if (i < fmt.size()) {
                char spec = fmt[i++];
                if (pos <= static_cast<int>(args.size())) {
                    switch (spec) {
                        case 'f': {
                            double val = args[pos - 1].as_number();
                            pos++;
                            int actual_precision = (precision >= 0) ? precision : 6;
                            result << std::fixed << std::setprecision(actual_precision) << val;
                            break;
                        }
                        case 'd':
                            result << static_cast<int>(args[pos - 1].as_number());
                            pos++;
                            break;
                        case 's':
                            result << args[pos - 1].as_string();
                            pos++;
                            break;
                        case '\n':
                            result << '\n';
                            break;
                        default:
                            result << '%' << spec;
                            break;
                    }
                } else {
                    result << '%' << spec;
                }
            } else {
                result << '%';
            }
        } else {
            result << fmt[i++];
        }
    }
    return result.str();
}

inline double string_len(const std::string& s) { return static_cast<double>(s.length()); }

inline std::string string_sub(const std::string& s, double start, double end) {
    int i = static_cast<int>(start) - 1;
    int j = static_cast<int>(end);
    if (i < 0) i = 0;
    if (j > static_cast<int>(s.length())) j = s.length();
    return s.substr(i, j - i);
}

inline std::string string_upper(const std::string& s) {
    std::string result = s;
    std::transform(result.begin(), result.end(), result.begin(), ::toupper);
    return result;
}

inline std::string string_lower(const std::string& s) {
    std::string result = s;
    std::transform(result.begin(), result.end(), result.begin(), ::tolower);
    return result;
}

// ============================================================================
// Table Library
// ============================================================================

inline luaValue table_unpack(const std::vector<luaValue>& args) {
    if (args.empty()) return luaValue();
    return args[0];
}

// ============================================================================
// OS Library
// ============================================================================

inline double os_clock() {
    return static_cast<double>(clock()) / CLOCKS_PER_SEC;
}

inline double os_time() {
    return static_cast<double>(std::time(nullptr));
}

inline std::string os_date(const std::string& format) {
    std::time_t t = std::time(nullptr);
    if (format.empty()) {
        return std::asctime(std::localtime(&t));
    }
    char buffer[256];
    std::strftime(buffer, sizeof(buffer), format.c_str(), std::localtime(&t));
    return std::string(buffer);
}

// ============================================================================
// Conversion Functions
// ============================================================================

inline double tonumber(const luaValue& val) {
    return val.as_number();
}

// ============================================================================
// Print Function
// ============================================================================

inline void print(const std::vector<luaValue>& args) {
    for (size_t i = 0; i < args.size(); ++i) {
        if (i > 0) std::cout << "\t";
        std::cout << args[i].as_string();
    }
    std::cout << std::endl;
}

} // namespace l2c
