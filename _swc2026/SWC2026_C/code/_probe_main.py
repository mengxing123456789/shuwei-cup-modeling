import io, sys

p = sys.argv[1] if len(sys.argv) > 1 else "main.tex"
t = io.open(p, encoding="utf-8").read()
keys = [
    r"\begin{equation}",
    r"\begin{align}",
    r"tab:p3score",
    "eleven measures",
    "valid protocol",
    "eq:palmframe",
    "eq:relfuse",
    "eq:stagerule",
    "eq:conformal",
    "eq:slackscore",
    "eq:reserve",
    r"\slotPIdleSTwoOurs",
    "tab:negative",
    "tab:ablation",
    r"\includegraphics",
    r"\begin{table}",
]
for k in keys:
    print("%-24s %d" % (k, t.count(k)))
