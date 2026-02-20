-- Sparse array benchmark: random/sparse indices
local N = tonumber(arg[1]) or 10000
local iterations = tonumber(arg[2]) or 10

for iter = 1, iterations do
    local t = {}
    
    -- Write sparse indices (powers of 2, primes-like pattern)
    for i = 1, N do
        local idx = i * 7 + (i % 13) * 100
        t[idx] = i * 1.5
    end
    
    -- Read back
    local sum = 0
    for i = 1, N do
        local idx = i * 7 + (i % 13) * 100
        sum = sum + (t[idx] or 0)
    end
end

print("done")
