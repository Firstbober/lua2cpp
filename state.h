#pragma once

// Library struct definitions
struct io {
    static bool io_write(State* state);
};
struct math {
    static double math_sqrt(State* state, double /* param */);
};
struct string {
    template <typename... Args>
    static std::string string_format(State* state, Args&&... args);
};

// Global function declarations
namespace lua2c {
}  // namespace lua2c
