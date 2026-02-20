-- Dense array benchmark: sequential access 1..N
local N = tonumber(arg[1]) or 10000
local iterations = tonumber(arg[2]) or 10

for iter = 1, iterations do
    local t = {}
    
    -- Write phase
    for i = 1, N do
        t[i] = i * 1.5
    end
    
    -- Read phase
    local sum = 0
    for i = 1, N do
        sum = sum + t[i]
    end
    
    -- Update phase
    for i = 1, N do
        t[i] = t[i] * 2
    end
end

print("done")
