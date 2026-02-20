#include "l2c_runtime_v2.hpp"

namespace l2c {
    void print(const TABLE& value) {
        if (value.str.empty()) {
            std::cout << value.num << std::endl;
        } else {
            std::cout << value.str << std::endl;
        }
    }

    TABLE tonumber(const TABLE& value) {
        TABLE result;
        if (!value.str.empty()) {
            try {
                result.num = std::stod(value.str);
            } catch (...) {
                result.num = 0;
            }
        } else {
            result.num = value.num;
        }
        return result;
    }

    TABLE tostring(const TABLE& value) {
        TABLE result;
        if (value.str.empty()) {
            std::ostringstream oss;
            oss << value.num;
            result.str = oss.str();
        } else {
            result.str = value.str;
        }
        return result;
    }

    TABLE string_format(const std::string& fmt, const TABLE& value) {
        TABLE result;
        char buffer[256];
        
        if (fmt.find("%f") != std::string::npos || fmt.find("%0.") != std::string::npos) {
            std::snprintf(buffer, sizeof(buffer), fmt.c_str(), value.num);
            result.str = buffer;
        }
        else if (fmt.find("%d") != std::string::npos) {
            std::snprintf(buffer, sizeof(buffer), fmt.c_str(), static_cast<int>(value.num));
            result.str = buffer;
        }
        else if (fmt.find("%s") != std::string::npos) {
            std::snprintf(buffer, sizeof(buffer), fmt.c_str(), value.str.c_str());
            result.str = buffer;
        }
        else {
            result.str = fmt;
        }
        
        return result;
    }

    NUMBER math_sqrt(const TABLE& value) {
        return std::sqrt(value.num);
    }

    void io_write(const TABLE& value) {
        if (value.str.empty()) {
            std::cout << value.num;
        } else {
            std::cout << value.str;
        }
    }
}
