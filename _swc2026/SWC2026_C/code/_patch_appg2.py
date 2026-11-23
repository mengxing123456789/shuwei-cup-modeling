from pathlib import Path

p = Path(r"code\make_appendix_g.py")
t = p.read_text(encoding="utf-8")

t = t.replace(
    '    add(r"\\footnotesize")\n    add(r"\\begin{tabular}{llrrrrl}")\n    add(r"\\toprule")\n    add(r"Run & Model & Params & Epochs & Seeds & GPU\\,s & Test headline \\\\)")',
    '    add(r"\\footnotesize")\n    add(r"\\setlength{\\tabcolsep}{4pt}")\n    add(r"\\begin{tabular}{llrrrrl}")\n    add(r"\\toprule")\n    add(r"Run & Model & Params & Ep. & Sd. & GPU\\,s & Test \\\\)")',
)

p.write_text(t, encoding="utf-8", newline="\n")
print("ok")
