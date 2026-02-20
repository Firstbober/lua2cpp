# TABLE Performance Optimization Benchmark

## Methodology

Benchmarks run with `hyperfine --warmup 2` comparing:
- **Lua 5.4** (`/usr/bin/lua5.4`)
- **LuaJIT 2.1** (`/usr/bin/luajit`)
- **C++ transpiled** code with two TABLE implementations

## Implementations Compared

### v1: std::map (original)
```cpp
struct TABLE {
    std::map<int, TABLE> array;      // O(log n) per access
    std::map<STRING, TABLE> table;   // O(log n) per access
    double num = 0;
    std::string str;
};
```

### v2: vector + unordered_map (optimized)
```cpp
struct TABLE {
    std::vector<TABLE> array;                    // O(1) for indices 1-63
    std::unordered_map<int, TABLE> hash;         // O(1) avg for sparse
    std::unordered_map<STRING, TABLE> str_hash;  // O(1) avg for strings
    double num = 0;
    std::string str;
};
```

## Results

### Dense Array Benchmark (10K elements × 10 iterations)

| Implementation | Time | vs LuaJIT |
|----------------|------|-----------|
| **LuaJIT 2.1** | 5.3 ms | baseline |
| Lua 5.4 | 6.9 ms | 1.3× slower |
| C++ v2 (vector) | 36.9 ms | 7× slower |

### Mixed Ops Benchmark (spectral-norm style, 500×5)

| Implementation | Time | vs LuaJIT |
|----------------|------|-----------|
| **LuaJIT 2.1** | 50 ms | baseline |
| C++ v2 (vector) | 975 ms | 19× slower |
| Lua 5.4 | 1256 ms | 25× slower |

## Improvement Summary (v1 → v2)

| Benchmark | v1 (std::map) | v2 (vector) | Speedup |
|-----------|---------------|-------------|---------|
| Dense array | 78.8 ms | 36.9 ms | **2.1×** |
| Mixed ops | 5710 ms | 975 ms | **5.9×** |

## Key Insights

1. **LuaJIT is extremely fast** - 25× faster than Lua 5.4, 19× faster than our C++
2. **JIT compilation advantage** - LuaJIT compiles hot loops to native machine code
3. **std::vector beats std::map** - O(1) vs O(log n) makes a huge difference
4. **C++ beats Lua 5.4** for numeric-heavy workloads after optimization

## Why LuaJIT Wins

LuaJIT's advantages over our transpiled C++:
- **Trace-based JIT** compiles hot loops to optimized machine code
- **Specialized TABLE** with array+hash split and power-of-2 sizing
- **Type specialization** - detects numeric loops and uses unboxed values
- **Allocator optimization** - custom GC with cache-friendly layout

## Future Optimization Opportunities

To narrow the gap with LuaJIT:
1. Increase array threshold beyond 64 elements
2. Use power-of-2 sizing with bitmask (like LuaJIT)
3. Generate specialized numeric loops (avoid TABLE for pure numeric code)
4. Add SIMD hints for vectorizable operations
