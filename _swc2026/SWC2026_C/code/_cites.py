# -*- coding: utf-8 -*-
import io, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
t = io.open(ROOT / "main.tex", encoding="utf-8").read()
print("== cite calls")
for m in re.finditer(r"\\cite\{([^}]*)\}", t):
    ln = t[: m.start()].count("\n") + 1
    print("  line %d: %s  || ctx: %r" % (ln, m.group(0), t[max(0, m.start() - 90): m.start()].replace("\n", " ")[-90:]))
print("== bibitems")
for m in re.finditer(r"\\bibitem\{([^}]*)\}", t):
    ln = t[: m.start()].count("\n") + 1
    print("  line %d: %s" % (ln, m.group(1)))
