# -*- coding: utf-8 -*-
"""Word budget per body section, so prose can be traded for equations and figures
without guessing where the fat is."""
import re
from pathlib import Path

TEX = Path(r"E:\数学建模\_swc2026\SWC2026_C\main.tex")
lines = TEX.read_text(encoding="utf-8").splitlines()

BODY_END = next(i for i, l in enumerate(lines) if l.strip().startswith(r"\begin{appendices}"))
secs = []
for i, l in enumerate(lines[:BODY_END]):
    s = l.strip()
    if s.startswith(r"\section{") or s.startswith(r"\subsection{"):
        secs.append((i, s))
secs.append((BODY_END, r"\end{body}"))

def words(chunk):
    # strip latex commands but keep words inside braces
    t = re.sub(r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?", " ", chunk)
    t = re.sub(r"[{}$\\%&_^~]", " ", t)
    return len(re.findall(r"[A-Za-z][A-Za-z\-']+", t))

rows = []
for k in range(len(secs) - 1):
    a, name = secs[k]
    b = secs[k + 1][0]
    chunk = "\n".join(lines[a:b])
    rows.append((name[:58], b - a, words(chunk)))

tot = sum(r[2] for r in rows)
print("%-60s %5s %6s %5s" % ("section", "lines", "words", "%"))
print("-" * 82)
for name, nl, w in rows:
    print("%-60s %5d %6d %5.1f" % (name, nl, w, 100.0 * w / tot))
print("-" * 82)
print("%-60s %5s %6d" % ("TOTAL BODY", "", tot))
