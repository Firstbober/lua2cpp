# C++ Tests for Lua Benchmarks

This directory contains C++ test executables for all Lua benchmarks.

## Test List

### ack.lua
- **Test executable**: `ack_test`
- **C++ main file**: `ack_main.cpp`
- **Lua source**: `lua/ack.lua`
- **Arguments**: N M (defaults: 3, 8)
- **Usage**:
```bash
./ack_test
# with argument 1=3
./ack_test 3
# with argument 2=8
./ack_test 8
```

### binary-trees.lua
- **Test executable**: `binary_trees_test`
- **C++ main file**: `binary_trees_main.cpp`
- **Lua source**: `lua/binary-trees.lua`
- **Arguments**: N (default: 0)
- **Usage**:
```bash
./binary_trees_test
# with argument 1=0
./binary_trees_test 0
```

### comparisons.lua
- **Test executable**: `comparisons_test`
- **C++ main file**: `comparisons_main.cpp`
- **Lua source**: `lua/comparisons.lua`
- **Arguments**: No arguments
- **Usage**:
```bash
./comparisons_test
```

### fannkuch-redux.lua
- **Test executable**: `fannkuch_redux_test`
- **C++ main file**: `fannkuch_redux_main.cpp`
- **Lua source**: `lua/fannkuch-redux.lua`
- **Arguments**: n (default: 7)
- **Usage**:
```bash
./fannkuch_redux_test
# with argument 1=7
./fannkuch_redux_test 7
```

### fasta.lua
- **Test executable**: `fasta_test`
- **C++ main file**: `fasta_main.cpp`
- **Lua source**: `lua/fasta.lua`
- **Arguments**: N (default: 1000)
- **Usage**:
```bash
./fasta_test
# with argument 1=1000
./fasta_test 1000
```

### fixpoint-fact.lua
- **Test executable**: `fixpoint_fact_test`
- **C++ main file**: `fixpoint_fact_main.cpp`
- **Lua source**: `lua/fixpoint-fact.lua`
- **Arguments**: N (default: 100)
- **Usage**:
```bash
./fixpoint_fact_test
# with argument 1=100
./fixpoint_fact_test 100
```

### heapsort.lua
- **Test executable**: `heapsort_test`
- **C++ main file**: `heapsort_main.cpp`
- **Lua source**: `lua/heapsort.lua`
- **Arguments**: num_iterations N (defaults: 4, 10000)
- **Usage**:
```bash
./heapsort_test
# with argument 1=4
./heapsort_test 4
# with argument 2=10000
./heapsort_test 10000
```

### k-nucleotide.lua
- **Test executable**: `k_nucleotide_test`
- **C++ main file**: `k_nucleotide_main.cpp`
- **Lua source**: `lua/k-nucleotide.lua`
- **Arguments**: No arguments (reads from stdin)
- **Usage**:
```bash
./k_nucleotide_test
```

### mandel.lua
- **Test executable**: `mandel_test`
- **C++ main file**: `mandel_main.cpp`
- **Lua source**: `lua/mandel.lua`
- **Arguments**: N (default: 256)
- **Usage**:
```bash
./mandel_test
# with argument 1=256
./mandel_test 256
```

### n-body.lua
- **Test executable**: `n_body_test`
- **C++ main file**: `n_body_main.cpp`
- **Lua source**: `lua/n-body.lua`
- **Arguments**: N (default: 1000)
- **Usage**:
```bash
./n_body_test
# with argument 1=1000
./n_body_test 1000
```

### qt.lua
- **Test executable**: `qt_test`
- **C++ main file**: `qt_main.cpp`
- **Lua source**: `lua/qt.lua`
- **Arguments**: No arguments
- **Usage**:
```bash
./qt_test
```

### queen.lua
- **Test executable**: `queen_test`
- **C++ main file**: `queen_main.cpp`
- **Lua source**: `lua/queen.lua`
- **Arguments**: N (default: 8)
- **Usage**:
```bash
./queen_test
# with argument 1=8
./queen_test 8
```

### regex-dna.lua
- **Test executable**: `regex_dna_test`
- **C++ main file**: `regex_dna_main.cpp`
- **Lua source**: `lua/regex-dna.lua`
- **Arguments**: No arguments (reads from stdin)
- **Usage**:
```bash
./regex_dna_test
```

### scimark.lua
- **Test executable**: `scimark_test`
- **C++ main file**: `scimark_main.cpp`
- **Lua source**: `lua/scimark.lua`
- **Arguments**: No arguments
- **Usage**:
```bash
./scimark_test
```

### sieve.lua
- **Test executable**: `sieve_test`
- **C++ main file**: `sieve_main.cpp`
- **Lua source**: `lua/sieve.lua`
- **Arguments**: num_iterations limit (defaults: 100, 8192)
- **Usage**:
```bash
./sieve_test
# with argument 1=100
./sieve_test 100
# with argument 2=8192
./sieve_test 8192
```

### simple.lua
- **Test executable**: `simple_test`
- **C++ main file**: `simple_main.cpp`
- **Lua source**: `lua/simple.lua`
- **Arguments**: No arguments
- **Usage**:
```bash
./simple_test
```

### spectral-norm.lua
- **Test executable**: `spectral_norm_test`
- **C++ main file**: `spectral_norm_main.cpp`
- **Lua source**: `lua/spectral-norm.lua`
- **Arguments**: N (default: 100)
- **Usage**:
```bash
./spectral_norm_test
# with argument 1=100
./spectral_norm_test 100
```

## Build Instructions

```bash
cd tests/cpp/build
cmake ..
make
```

## Run All Tests

```bash
cd tests/cpp/build
for test in *_test; do echo "=== Running $test ==="; ./$test; echo; done
```
