#pragma once

class Object {
public:
    TABLE fields;  // Dynamic field storage

    Object() = default;
    virtual ~Object() = default;

    virtual void init() {}

    template<typename T>
    bool is() const {
        return dynamic_cast<const T*>(this) != nullptr;
    }
};
