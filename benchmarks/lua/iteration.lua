-- Iteration benchmark (# operator and pairs)
local N = tonumber(arg[1]) or 10000
local iterations = tonumber(arg[2]) or 10

for iter = 1, iterations do
    local t = {}
    
    -- Build table
    for i = 1, N do
        t[i] = i
    end
    
    -- Length operator (multiple times)
    local len = 0
    for i = 1, 100 do
        len = #t
    end
    
    -- Iterate with pairs
    local sum = 0
    for k, v in pairs(t) do
        sum = sum + v
    end
end

print("done")
