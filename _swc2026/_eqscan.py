# -*- coding: utf-8 -*-
import re
from pathlib import Path
p = Path(r"E:\数学建模\_swc2026\SWC2026_C\main.tex")
L = p.read_text(encoding="utf-8").splitlines()
pat = re.compile(r"\\(begin\{(equation|align|aligned|gather|eqnarray)\}|label\{eq:)")
for i, l in enumerate(L, 1):
    if pat.search(l):
        print(i, l.strip()[:120])
