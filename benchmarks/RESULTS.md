# TABLE Performance Optimization Benchmark

## Key Finding

**Hand-optimized C++ beats LuaJIT by 3.5×** for numeric-heavy workloads!  
But transpiled C++ is 76× slower than hand-optimized C++ due to template overhead.

## Final Results (N=1000, 5 iterations)

| Implementation | Time | vs LuaJIT | Notes |
|----------------|------|-----------|-------|
| **Standalone C++ (O3+LTO)** | 53 ms | **3.5× faster** | Concrete types, no templates |
| **LuaJIT 2.1** | 183 ms | baseline | JIT-compiled |
| Lua 5.4 | ~2500 ms | 14× slower | Interpreted |
| Transpiled C++ (v2) | 4045 ms | 22× slower | Template bloat |

## Scaling Analysis (C++ O3+LTO vs LuaJIT)

| N | LuaJIT | C++ Standalone | Speedup |
|---|--------|----------------|---------|
| 500 | 52 ms | 21 ms | **2.5×** |
| 1000 | 183 ms | 53 ms | **3.5×** |
| 2000 | 699 ms | 195 ms | **3.6×** |

## Why Standalone C++ Beats LuaJIT

1. **Static typing** - No runtime type checks or tag dispatch
2. **Compile-time optimization** - Inlining, vectorization, loop unrolling
3. **No GC** - Pre-allocated arrays, no allocation overhead
4. **LTO** - Whole-program optimization across translation units

## Why Transpiled C++ Is 76× Slower

1. **Template bloat** - `template<typename T> void f(T&& x)` prevents inlining
2. **TABLE abstraction** - Every number wrapped in TABLE struct
3. **Indirect calls** - Function pointers through state struct
4. **No specialization** - Generic code for what should be `double`

## Transpiler Improvements Needed

To match standalone C++ performance:

1. **Type specialization** - Detect `local x = 0` → use `double` not `TABLE`
2. **Numeric loop detection** - `for i=1,N` → `for (int i=1; i<=N; ++i)`
3. **Array specialization** - `t[i] = x` where `t` is numeric array → `std::vector<double>`
4. **Remove templates** - Generate concrete types for known numeric code

## Benchmark Implementations

### v1: std::map (original)
```cpp
struct TABLE {
    std::map<int, TABLE> array;      // O(log n) per access
    std::map<STRING, TABLE> table;
    double num = 0;
    std::string str;
};
```

### v2: vector + unordered_map (optimized runtime)
```cpp
struct TABLE {
    std::vector<TABLE> array;                    // O(1) for indices 1-63
    std::unordered_map<int, TABLE> hash;         // O(1) avg
    std::unordered_map<STRING, TABLE> str_hash;  // O(1) avg
    double num = 0;
    std::string str;
};
```

### Standalone: Concrete types (optimal)
```cpp
static double N_val;
static std::vector<double> u_val, v_val, t_val;

void Av(std::vector<double>& x, std::vector<double>& y) {
    for (int i = 1; i <= N_val; ++i) {
        double a = 0;
        for (int j = 1; j <= N_val; ++j) {
            a += x[j] * A(i, j);
        }
        y[i] = a;
    }
}
```

## Conclusion

- **LuaJIT is impressive** - 25× faster than Lua 5.4
- **C++ can beat LuaJIT** - With proper type specialization
- **Our transpiler needs work** - 76× gap to hand-optimized C++
- **Type specialization is key** - Generic code kills performance
