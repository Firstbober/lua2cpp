// Auto-generated main for test_type_inference
// Runtime is provided by the included .cpp file below
#include <iostream>
#include <exception>
// Include the .cpp directly (which includes the appropriate runtime)
#include "test_type_inference.cpp"

// Detect if test_type_inference_module_init takes a TABLE argument using SFINAE
template<typename T, typename = void>
struct TakesTableArg : std::false_type {};

template<typename T>
struct TakesTableArg<T, std::void_t<decltype(std::declval<T>()(std::declval<TABLE>()))>> : std::true_type {};

// Helper to call the function
template<typename Func>
void call_module_init(Func func, TABLE arg) {
    if constexpr (TakesTableArg<Func>::value) {
        func(arg);
    } else {
        func();
    }
}

int main(int argc, char* argv[]) {
    try {
        // Create arg table (Lua 1-indexed)
        TABLE arg = TABLE::Table(LuaTable::create(argc, 0));
        for (int i = 1; i < argc; ++i) {
            arg[i] = TABLE(argv[i]);
        }

        // Call module init with automatic dispatch
        call_module_init(test_type_inference_module_init, arg);
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << std::endl;
        return 1;
    }
}
