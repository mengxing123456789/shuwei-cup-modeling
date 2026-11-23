import pathlib, sys
P = pathlib.Path("main.tex"); t = P.read_text(encoding="utf-8")
old = """large still costs capacity later, which is the mechanism behind the reversal in
Section~\\ref{sec:limits}."""
new = """large still costs capacity later, which is the mechanism behind the reversal in
Section~\\ref{sec:limits}.}"""
if t.count(old) != 1:
    print("MISS", t.count(old)); sys.exit(1)
t = t.replace(old, new)
P.write_text(t, encoding="utf-8", newline="\n")
print("closing brace restored")
