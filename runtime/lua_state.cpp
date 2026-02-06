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
        for (size_t i = 0; i < format.size(); ++i) {
            if (format[i] == '%' && i + 1 < format.size()) {
                char spec = format[++i];
                if (pos < static_cast<int>(args.size())) {
                    switch (spec) {
                        case 'f': {
                            double val = args[pos++].as_number();
                            int precision = 6;
                            if (i + 1 < format.size() && format[i + 1] == '.') {
                                i += 2;
                                std::string prec_str;
                                while (i < format.size() && isdigit(format[i])) {
                                    prec_str += format[i++];
                                }
                                if (!prec_str.empty()) {
                                    precision = std::stoi(prec_str);
                                    i--;
                                }
                            }
                            result << std::fixed << std::setprecision(precision) << val;
                            break;
                        }
                        case 'd':
                            result << static_cast<int>(args[pos++].as_number());
                            break;
                        case 's':
                            result << args[pos++].as_string();
                            break;
                        default:
                            result << '%' << spec;
                            break;
                    }
                } else {
                    result << '%' << spec;
                }
            } else {
                result << format[i];
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
