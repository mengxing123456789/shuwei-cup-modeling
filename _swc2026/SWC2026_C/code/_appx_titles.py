# -*- coding: utf-8 -*-
import io, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
t = io.open(ROOT / "main.tex", encoding="utf-8").read()
i = t.find(r"\begin{appendices}")
seg = t[i:]
print("== main.tex after begin{appendices}")
for m in re.finditer(r"\\(sub)?section\*?\{([^}]*)\}", seg):
    print("   ", m.group(0)[:100])
print("== tables/app_n.tex")
a = io.open(ROOT / "tables" / "app_n.tex", encoding="utf-8").read()
for m in re.finditer(r"\\(sub)?section\*?\{([^}]*)\}", a):
    print("   ", m.group(0)[:100])
print("== cls 400-420")
c = io.open(ROOT / "swmcmthesis.cls", encoding="utf-8", errors="ignore").read().split("\n")
for k in range(398, 420):
    print(k + 1, "|", c[k])
