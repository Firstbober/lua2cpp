-- Mixed operations benchmark (spectral-norm style)
local N = tonumber(arg[1]) or 500
local iterations = tonumber(arg[2]) or 5

local function A(i, j)
    local ij = i + j - 1
    return 1.0 / ((ij * (ij - 1)) * 0.5 + i)
end

local function Av(x, y, N)
    for i = 1, N do
        local a = 0
        for j = 1, N do
            a = a + x[j] * A(i, j)
        end
        y[i] = a
    end
end

local function Atv(x, y, N)
    for i = 1, N do
        local a = 0
        for j = 1, N do
            a = a + x[j] * A(j, i)
        end
        y[i] = a
    end
end

local function AtAv(x, y, t, N)
    Av(x, t, N)
    Atv(t, y, N)
end

for iter = 1, iterations do
    local u = {}
    local v = {}
    local t = {}
    
    for i = 1, N do
        u[i] = 1
    end
    
    for i = 1, 10 do
        AtAv(u, v, t, N)
        AtAv(v, u, t, N)
    end
    
    local vBv = 0
    local vv = 0
    for i = 1, N do
        local ui = u[i]
        local vi = v[i]
        vBv = vBv + ui * vi
        vv = vv + vi * vi
    end
    
    local result = math.sqrt(vBv / vv)
end

print("done")
