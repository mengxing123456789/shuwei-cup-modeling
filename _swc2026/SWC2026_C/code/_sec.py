import io, re

P = r"main.tex"
lines = io.open(P, encoding="utf-8").read().split("\n")
pat = re.compile(r"^\\(section|subsection)\{")
for i, l in enumerate(lines, 1):
    if pat.match(l.strip()):
        print(i, l.strip()[:100])
print("total lines", len(lines))
