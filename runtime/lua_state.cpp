#include "lua_state.hpp"

luaState::luaState() {
    // sol_state_.open_libraries(sol::lib::base, sol::lib::math, sol::lib::string);  // TODO: Enable sol2 when needed

    stdlib_functions_["io.write"] = [](const std::vector<luaValue>& args) -> luaValue {
        for (const auto& arg : args) {
            std::cout << arg.as_string();
        }
        return luaValue();
    };

    stdlib_functions_["string.format"] = [](const std::vector<luaValue>& args) -> luaValue {
        if (args.empty()) {
            return luaValue();
        }
        std::string format = args[0].as_string();
        std::ostringstream result;
        int pos = 1;
        size_t i = 0;
        while (i < format.size()) {
            if (format[i] == '%' && i + 1 < format.size()) {
                i++;
                std::string flags;
                int width = 0;
                int precision = -1;

                while (i < format.size() && (format[i] == '-' || format[i] == '+' || format[i] == ' ' || format[i] == '#' || format[i] == '0')) {
                    flags += format[i++];
                }

                while (i < format.size() && isdigit(format[i])) {
                    width = width * 10 + (format[i++] - '0');
                }

                if (i < format.size() && format[i] == '.') {
                    i++;
                    precision = 0;
                    while (i < format.size() && isdigit(format[i])) {
                        precision = precision * 10 + (format[i++] - '0');
                    }
                }

                if (i < format.size()) {
                    char spec = format[i++];
                    if (pos < static_cast<int>(args.size())) {
                        switch (spec) {
                            case 'f': {
                                double val = args[pos++].as_number();
                                int actual_precision = (precision >= 0) ? precision : 6;
                                result << std::fixed << std::setprecision(actual_precision) << val;
                                break;
                            }
                            case 'd':
                                result << static_cast<int>(args[pos++].as_number());
                                break;
                            case 's':
                                result << args[pos++].as_string();
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
                result << format[i++];
            }
        }
        return luaValue(result.str());
    };

    stdlib_functions_["math.sqrt"] = [](const std::vector<luaValue>& args) -> luaValue {
        if (args.empty()) {
            return luaValue();
        }
        return luaValue(std::sqrt(args[0].as_number()));
    };

    stdlib_functions_["tonumber"] = [](const std::vector<luaValue>& args) -> luaValue {
        if (args.empty()) {
            return luaValue();
        }
        return luaValue(args[0].as_number());
    };

    stdlib_functions_["print"] = [](const std::vector<luaValue>& args) -> luaValue {
        for (size_t i = 0; i < args.size(); ++i) {
            if (i > 0) {
                std::cout << "\t";
            }
            std::cout << args[i].as_string();
        }
        std::cout << std::endl;
        return luaValue();
    };
}

luaValue luaState::get_global(const std::string& name) {
    if (name == "arg") {
        luaValue arg_table = luaValue::new_table();
        for (size_t i = 0; i < arg_.size(); ++i) {
            arg_table[i + 1] = arg_[i];
        }
        return arg_table;
    }

    auto it = globals_.find(name);
    if (it != globals_.end()) {
        return it->second;
    }

    auto stdlib_it = stdlib_functions_.find(name);
    if (stdlib_it != stdlib_functions_.end()) {
        return luaValue([name, this](const std::vector<luaValue>& args) -> luaValue {
            return stdlib_functions_[name](args);
        });
    }

    return luaValue();
}

void luaState::set_global(const std::string& name, const luaValue& value) {
    globals_[name] = value;
}
