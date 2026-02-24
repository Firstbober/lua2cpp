#include "../runtime/l2c_runtime_lua_table.hpp"
extern void n_body_module_init(TABLE arg);
int main(int argc, char* argv[]) {
    TABLE arg = NEW_TABLE;
    for (int i = 1; i < argc; ++i) {
        arg[NUMBER(i)] = STRING(argv[i]);
    }
    n_body_module_init(arg);
    return 0;
}
