-- Hash/string key benchmark
local N = tonumber(arg[1]) or 10000
local iterations = tonumber(arg[2]) or 10

for iter = 1, iterations do
    local t = {}
    
    -- Write string keys
    for i = 1, N do
        t["key_" .. i] = i * 1.5
    end
    
    -- Read back
    local sum = 0
    for i = 1, N do
        sum = sum + (t["key_" .. i] or 0)
    end
end

print("done")
