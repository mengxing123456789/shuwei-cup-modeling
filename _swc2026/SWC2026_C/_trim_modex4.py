"""Recover one page: shrink body tables one step, shrink figures, move the
k-cap sweep table to Appendix D, and tighten the conclusion."""
import pathlib
import re
import sys

P = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C\main.tex")
src = P.read_text(encoding="utf-8")
done = []

# ---- 1. body tables: \small -> \footnotesize (only standalone lines)
lines = src.splitlines()
n_small = sum(1 for ln in lines if ln.strip() == r"\small")
print("standalone \\small lines:", n_small)
for i, ln in enumerate(lines):
    if ln.strip() == r"\small":
        lines[i] = ln.replace(r"\small", r"\footnotesize")
out = "\n".join(lines) + ("\n" if src.endswith("\n") else "")
done.append(f"tables-footnotesize({n_small})")

# ---- 2. move the k-cap table to Appendix D
m = re.search(r"\\begin\{table\}\[htbp\]\n\\centering\n\\caption\{Choice of the segment count.*?\\label\{tab:kcap\}.*?\\end\{table\}\n", out, re.S)
if not m:
    print("FAIL: kcap table block not found")
    sys.exit(1)
table_block = m.group(0)
out = out.replace(table_block, "", 1)
out = out.replace(
    "in the average rather than dropped.",
    "in the average rather than dropped. Table~\\ref{tab:kcap} in Appendix~\\ref{app:calib} reports the\ncount sweep in full.",
    1)
out = out.replace(r"\end{document}", table_block + "\n" + r"\end{document}", 1)
done.append("move-kcap")

# ---- 3. tighten the conclusion
sub_old = r"""Under an unknown affine service time, a slack-aware
policy with an explicit reservation quantile raises the weighted on-time rate over
EDF in the two capacity-constrained cases, and the same-rule reference prices the true
duration at only three to four points."""
sub_new = r"""Under an unknown affine service time, a slack-aware
policy with an explicit reservation quantile raises the weighted on-time rate over EDF
in the two capacity-constrained cases, and the truth is worth only three to four points
once the rule is fixed."""
if out.count(sub_old) != 1:
    print("FAIL: conclusion anchor")
    sys.exit(1)
out = out.replace(sub_old, sub_new, 1)
done.append("concl-tighten")

P.write_text(out, encoding="utf-8")
print("main.tex chars", len(src), "->", len(out))

# ---- 4. figure widths
G = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C\code\fill_numbers.py")
g = G.read_text(encoding="utf-8")
for old, new in (('r"0.45\\linewidth"', 'r"0.38\\linewidth"'), ('r"0.25\\linewidth"', 'r"0.20\\linewidth"')):
    if g.count(old) != 1:
        print("FAIL spec", old, g.count(old))
        sys.exit(1)
    g = g.replace(old, new, 1)
G.write_text(g, encoding="utf-8")
done.append("figw")
print("edits:", ", ".join(done))