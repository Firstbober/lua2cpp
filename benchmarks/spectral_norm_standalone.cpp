#include <iostream>
#include <chrono>
#include <cmath>
#include <vector>
#include <unordered_map>
#include <sstream>
#include <cstdio>

using NUMBER = double;
using STRING = std::string;

struct TABLE {
    static constexpr int ARRAY_INITIAL_SIZE = 8;
    std::vector<TABLE> array;
    std::unordered_map<int, TABLE> hash;
    std::unordered_map<STRING, TABLE> str_hash;
    double num = 0;
    std::string str;

    TABLE() { array.reserve(ARRAY_INITIAL_SIZE); }
    TABLE(double v) : num(v) {}
    TABLE(int v) : num(static_cast<double>(v)) {}
    TABLE(const char* v) : str(v) {}
    TABLE(const std::string& v) : str(v) {}

    operator double() const { return num; }
    explicit operator bool() const { return true; }

    TABLE& operator=(double v) { num = v; str.clear(); return *this; }
    TABLE& operator=(int v) { num = static_cast<double>(v); str.clear(); return *this; }

    TABLE& operator[](int index) {
        if (index >= 1 && index < 64) {
            if (index >= static_cast<int>(array.size())) array.resize(index + 1);
            return array[index];
        }
        return hash[index];
    }

    TABLE& operator[](const std::string& key) { return str_hash[key]; }
};

#define NEW_TABLE TABLE()

namespace l2c {
    TABLE tonumber(const TABLE& value) {
        TABLE result;
        if (!value.str.empty()) {
            try { result.num = std::stod(value.str); } catch (...) { result.num = 0; }
        } else { result.num = value.num; }
        return result;
    }
    NUMBER math_sqrt(const TABLE& value) { return std::sqrt(value.num); }
    void io_write(const TABLE& value) {
        if (value.str.empty()) std::cout << value.num;
        else std::cout << value.str;
    }
    TABLE string_format(const std::string& fmt, const TABLE& value) {
        TABLE result; char buffer[256];
        std::snprintf(buffer, sizeof(buffer), fmt.c_str(), value.num);
        result.str = buffer;
        return result;
    }
}

static NUMBER N_val;
static TABLE t_val, u_val, v_val;

template<typename i_t, typename j_t>
double A(i_t&& i, j_t&& j) {
    double ij = (i + j) - 1;
    return 1.0 / ((ij * (ij - 1)) * 0.5 + i);
}

template<typename x_t, typename y_t>
void Av(x_t&& x, y_t&& y) {
    for (double i = 1; i <= N_val; i += 1) {
        double a = 0;
        for (double j = 1; j <= N_val; j += 1) {
            a = a + (x[j] * A(i, j));
        }
        y[i] = a;
    }
}

template<typename x_t, typename y_t>
void Atv(x_t&& x, y_t&& y) {
    for (double i = 1; i <= N_val; i += 1) {
        double a = 0;
        for (double j = 1; j <= N_val; j += 1) {
            a = a + (x[j] * A(j, i));
        }
        y[i] = a;
    }
}

template<typename x_t, typename y_t, typename t_t>
void AtAv(x_t&& x, y_t&& y, t_t&& t) {
    Av(x, t);
    Atv(t, y);
}

void run(int N, int iters) {
    N_val = N;
    u_val = NEW_TABLE;
    v_val = NEW_TABLE;
    t_val = NEW_TABLE;

    for (double i = 1; i <= N_val; i++) u_val[i] = 1;

    for (int i = 0; i < iters; i++) {
        AtAv(u_val, v_val, t_val);
        AtAv(v_val, u_val, t_val);
    }

    double vBv = 0, vv = 0;
    for (double i = 1; i <= N_val; i++) {
        double ui = u_val[i], vi = v_val[i];
        vBv += ui * vi;
        vv += vi * vi;
    }
    l2c::io_write(l2c::string_format("%0.9f\n", l2c::math_sqrt(TABLE(vBv / vv))));
}

int main(int argc, char* argv[]) {
    int N = argc > 1 ? std::atoi(argv[1]) : 100;
    int iters = argc > 2 ? std::atoi(argv[2]) : 10;
    
    auto start = std::chrono::high_resolution_clock::now();
    run(N, iters);
    auto end = std::chrono::high_resolution_clock::now();
    
    auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
    std::cerr << "Time: " << ns / 1e6 << " ms" << std::endl;
    return 0;
}
