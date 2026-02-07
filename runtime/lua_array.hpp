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
    
    // Get element at index - returns value (not reference) to avoid undefined behavior
    T get(size_t index) const {
        if (index >= data_.size()) {
            return T{};  // Return default-constructed value
        }
        return data_[index];
    }
    
    // Set element at index - auto-grows array with 10% buffer
    void set(size_t index, const T& value) {
        if (index >= data_.size()) {
            size_t new_size = static_cast<size_t>(std::max(index + 1,
                                          static_cast<size_t>(data_.size() * 1.1)));
            data_.resize(new_size, T{});
        }
        data_[index] = value;
    }
    
    // Bounds-checked write access - auto-grows array with 10% buffer
    // Deprecated: Use set() instead for clarity
    T& operator[](size_t index) {
        if (index >= data_.size()) {
            size_t new_size = static_cast<size_t>(std::max(index + 1,
                                          static_cast<size_t>(data_.size() * 1.1)));
            data_.resize(new_size, T{});
        }
        return data_[index];
    }
    
    // Bounds-checked read access - returns default value for out-of-bounds
    // Deprecated: Use get() instead for clarity
    T operator[](size_t index) const {
        if (index >= data_.size()) {
            return T{};
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
