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
// Type Conversion Helpers
// ============================================================================

template<typename T>
inline std::string to_string(T&& arg) {
    if constexpr (std::is_arithmetic_v<std::decay_t<T>>) {
        return std::to_string(arg);
    } else if constexpr (std::is_same_v<std::decay_t<T>, std::string>) {
        return arg;
    } else if constexpr (std::is_same_v<std::decay_t<T>, const char*>) {
        return std::string(arg);
    } else {
        // Fallback to luaValue
        return arg.as_string();
    }
}

template<typename T>
inline double to_number(T&& arg) {
    if constexpr (std::is_arithmetic_v<std::decay_t<T>>) {
        return static_cast<double>(arg);
    } else {
        // Fallback to luaValue
        return arg.as_number();
    }
}

template<size_t... Is>
struct index_sequence {};

template<size_t N, size_t... Is>
struct make_index_sequence_impl : make_index_sequence_impl<N-1, N-1, Is...> {};

template<size_t... Is>
struct make_index_sequence_impl<0, Is...> {
    using type = index_sequence<Is...>;
};

template<size_t N>
using make_index_sequence = typename make_index_sequence_impl<N>::type;

// ============================================================================
// Print Function (Variadic)
// ============================================================================
template<typename... Args>
inline void print(Args&&... args) {
    size_t index = 0;
    ((std::cout << (index++ > 0 ? "\t" : "") << to_string(args)), ...);
    std::cout << std::endl;
}
// Keep non-template version for backward compatibility
inline void print(const std::vector<luaValue>& args) {
    for (size_t i = 0; i < args.size(); ++i) {
        if (i > 0) std::cout << "\t";
        std::cout << args[i].as_string();
    }
    std::cout << std::endl;
}

// ============================================================================
// Assert Function
// ============================================================================
inline luaValue assert(const luaValue& condition) {
    if (!condition.is_truthy()) {
        std::cerr << "Assertion failed!" << std::endl;
        std::cerr << "Value: " << condition.as_string() << std::endl;
        std::exit(1);
    }
    return condition;
}

// ============================================================================
// IO Library
// ============================================================================
template<typename... Args>
inline void io_write(Args&&... args) {
    ((std::cout << to_string(args)), ...);
}
// Non-template version for backward compatibility
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
inline double math_pow(double base, double exp) { return std::pow(base, exp); }

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
template<size_t... Is, typename... Args>
inline std::string string_format_impl(
    const std::string& fmt,
    std::tuple<Args...> args_tuple,
    index_sequence<Is...>
) {
    std::ostringstream result;
    int pos = 1;
    size_t i = 0;
    size_t arg_count = sizeof...(Args);

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
                if (pos <= static_cast<int>(arg_count)) {
                    // Create array of arguments to index by position
                    std::array<luaValue, sizeof...(Args)> args_array{luaValue(std::get<Is>(args_tuple))...};
                    switch (spec) {
                        case 'f': {
                            double val = args_array[pos - 1].as_number();
                            pos++;
                            int actual_precision = (precision >= 0) ? precision : 6;
                            result << std::fixed << std::setprecision(actual_precision) << val;
                            break;
                        }
                        case 'd':
                            result << static_cast<int>(args_array[pos - 1].as_number());
                            pos++;
                            break;
                        case 's':
                            result << args_array[pos - 1].as_string();
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

template<typename... Args>
inline std::string string_format(const std::string& fmt, Args&&... args) {
    return string_format_impl(fmt, std::forward_as_tuple(std::forward<Args>(args)...),
                              make_index_sequence<sizeof...(Args)>{});
}

// Non-template version for backward compatibility
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

inline luaValue tonumber(const luaValue& val) {
    LuaType t = val.type();
    if (t == LuaType::NUMBER) {
        return val;
    }
    if (t == LuaType::STRING) {
        try {
            double num = std::stod(val.as_string());
            return luaValue(num);
        } catch (...) {
            return luaValue();
        }
    }
    if (t == LuaType::BOOLEAN) {
        return luaValue(val.as_number());
    }
    return luaValue();
}

} // namespace l2c
