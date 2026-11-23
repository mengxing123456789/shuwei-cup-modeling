# -*- coding: utf-8 -*-
"""List body section/subsection line numbers and word counts, for page-budget work."""
import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
L = io.open(ROOT / "main.tex", encoding="utf-8").read().split("\n")

RX = re.compile(r"^\\(section|subsection)\{(.*)\}\s*$")
rows = []
for i, line in enumerate(L):
    m = RX.match(line)
    if m:
        rows.append((i + 1, m.group(1), m.group(2)))

for k, (ln, kind, title) in enumerate(rows):
    end = rows[k + 1][0] - 1 if k + 1 < len(rows) else len(L)
    chunk = "\n".join(L[ln - 1 : end])
    words = len(re.findall(r"[A-Za-z][A-Za-z-]*", chunk))
    print(f"{ln:5d} {kind[:3]} {words:5d}w  {title[:60]}")
