import io, re, sys

p = sys.argv[1] if len(sys.argv) > 1 else "tables/app_n.tex"
lines = io.open(p, encoding="utf-8").read().splitlines()
print("lines", len(lines))
for i, l in enumerate(lines, 1):
    s = l.strip()
    if re.match(r"\\(sub)?section", s) or s.startswith("\\begin{table}") or s.startswith("\\label{tab:") or s.startswith("\\label{sec:"):
        print(i, s[:100])
