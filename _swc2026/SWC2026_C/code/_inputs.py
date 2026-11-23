import io, re, sys

p = sys.argv[1] if len(sys.argv) > 1 else "main.tex"
t = io.open(p, encoding="utf-8").read().splitlines()
for i, l in enumerate(t, 1):
    s = l.strip()
    if s.startswith("\\input"):
        print(i, s)
