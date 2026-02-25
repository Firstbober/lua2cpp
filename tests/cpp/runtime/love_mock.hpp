// Mock Love2D API for testing flat_nested convention
#ifndef LUA2CPP_LOVE_MOCK_HPP
#define LUA2CPP_LOVE_MOCK_HPP

#include "lua_table.hpp"

namespace love {
namespace timer {
    // Mock timer.step function
    inline TValue step(...) {
        return TValue::Nil();
    }
} // namespace timer
} // namespace love

#endif // LUA2CPP_LOVE_MOCK_HPP
