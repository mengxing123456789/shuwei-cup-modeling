import io, re, sys

p = sys.argv[1] if len(sys.argv) > 1 else "main.tex"
t = io.open(p, encoding="utf-8").read()
lines = t.splitlines()
print("bytes", len(t.encode("utf-8")), "lines", len(lines))
pat = re.compile(r"\\(section|subsection)\{")
n = 0
for i, l in enumerate(lines, 1):
    if pat.match(l):
        n += 1
        print(i, l.strip())
print("count", n)
