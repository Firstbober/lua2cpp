-- Test for comparison operators
local function test_comparisons()
    local a = 5
    local b = 10

    -- Equality
    if a == 5 then
        print("a == 5: true")
    else
        print("a == 5: false")
    end

    -- Inequality
    if a ~= b then
        print("a ~= b: true")
    else
        print("a ~= b: false")
    end

    -- Less than
    if a < b then
        print("a < b: true")
    else
        print("a < b: false")
    end

    -- Less than or equal
    if a <= 5 then
        print("a <= 5: true")
    else
        print("a <= 5: false")
    end

    -- Greater than
    if b > a then
        print("b > a: true")
    else
        print("b > a: false")
    end

    -- Greater than or equal
    if b >= 10 then
        print("b >= 10: true")
    else
        print("b >= 10: false")
    end

    -- Complex comparison with arithmetic
    local x = a + b
    if x == 15 then
        print("a + b == 15: true")
    else
        print("a + b == 15: false")
    end
end

test_comparisons()
