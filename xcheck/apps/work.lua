-- deterministic lua workload: recursion, tables, strings
local function fib(n) if n < 2 then return n end return fib(n-1) + fib(n-2) end
local acc = fib(27)
local t = {}
for i = 1, 200000 do t[i] = (i * 2654435761) % 1000003 end
table.sort(t)
local s = {}
for i = 1, 20000 do s[#s+1] = string.format("%x", t[i]) end
local str = table.concat(s, ",")
print("lua", acc, t[1], t[100000], #str)
