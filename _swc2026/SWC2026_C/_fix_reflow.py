"""Reflow the upper-bound sentence so the phrase stays intact in the source
(the claims gate looks for the literal substring, and a line break split it)."""
import pathlib
import sys

P = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C\main.tex")
src = P.read_text(encoding="utf-8")

old = """room is in the rule, not in the knowledge. Third, we do not call the reference an upper
bound: it bounds this rule, not the information."""
new = ("room is in the rule, not in the knowledge. Third, we do not call the reference an "
       "upper bound: it bounds this rule, not the information.")
if src.count(old) != 1:
    print("FAIL found", src.count(old))
    sys.exit(1)
src = src.replace(old, new, 1)
P.write_text(src, encoding="utf-8")
print("reflowed; chars", len(src))
print("substring present:", "call the reference an upper bound" in src)