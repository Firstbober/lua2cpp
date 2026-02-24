#include "runtime/lua_table.hpp"
#include <cstring>

int main() {
    // Test operator==
    TValue s1 = TValue::String("test");
    TValue s2 = TValue::String("test");
    TValue s3 = TValue::String("other");
    TValue i1 = TValue::Integer(42);
    
    if (!(s1 == s2)) return 1;
    if (s1 == s3) return 1;
    if (!(s1 == s1)) return 1;  // same value should be equal
    if (s1 == i1) return 1;
    
    // Test hashTValue for strings
    uint32_t h1 = hashTValue(s1);
    uint32_t h2 = hashTValue(s2);
    if (h1 != h2) return 1;
    
    // Test hashString
    uint32_t h3 = hashString("test", 4);
    if (h3 != h1) return 1;
    
    return 0;
}
