#pragma once

#include <deque>
#include <cmath>
#include <stdexcept>
#include <limits>

template<typename T>
class luaArray {
private:
    std::deque<T> data_;

public:
    luaArray() = default;
    
    explicit luaArray(size_t count) : data_(count) {}
    
    luaArray(std::initializer_list<T> init) : data_(init) {}
    
    // Bounds-checked write access - auto-grows array with 10% buffer
    T& operator[](size_t index) {
        if (index >= data_.size()) {
            size_t new_size = static_cast<size_t>(std::max(index + 1, 
                                          static_cast<size_t>(data_.size() * 1.1)));
            data_.resize(new_size, T{});
        }
        return data_[index];
    }
    
    // Bounds-checked read access - returns default value for out-of-bounds
    const T& operator[](size_t index) const {
        if (index >= data_.size()) {
            static const T default_value = T{};
            return default_value;
        }
        return data_[index];
    }
    
    // Size access
    size_t size() const {
        return data_.size();
    }
    
    // Check if index is valid (doesn't grow array)
    bool has_index(size_t index) const {
        return index < data_.size();
    }
};

// Specialization for double to return NAN instead of 0.0 for out-of-bounds
template<>
inline const double& luaArray<double>::operator[](size_t index) const {
    if (index >= data_.size()) {
        static const double nan_value = std::numeric_limits<double>::quiet_NaN();
        return nan_value;
    }
    return data_[index];
}

// Specialization for std::string to return empty string for out-of-bounds
template<>
inline const std::string& luaArray<std::string>::operator[](size_t index) const {
    if (index >= data_.size()) {
        static const std::string empty_string;
        return empty_string;
    }
    return data_[index];
}
