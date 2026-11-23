# -*- coding: utf-8 -*-
"""Move the value-ladder figure from Appendix K to the body and keep the
appendix text as a pointer. Also refresh the Appendix K manifest."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
k = (ROOT / "tables" / "app_k.tex").read_text(encoding="utf-8")

start = k.index(r"\begin{figure}[H]")
end = k.index(r"\end{figure}", start) + len(r"\end{figure}")
k2 = k[:start] + "% figure moved to Section 6 (fig:value)\n" + k[end:]
(ROOT / "tables" / "app_k.tex").write_text(k2, encoding="utf-8")

gen = ROOT / "code" / "make_appendix_k.py"
g = gen.read_text(encoding="utf-8")
# drop the figure block from the generator, if present
g2 = re.sub(r"\nfig = \[\n(?:.*\n)*?\]\n", "\n", g, count=1)
if g2 == g:
    print("warning: generator figure block pattern not matched")
gen.write_text(g2, encoding="utf-8")

man_path = ROOT / "data" / "app_k_manifest.json"
man = json.loads(man_path.read_text(encoding="utf-8"))
man["output_sha256"] = hashlib.sha256(k2.encode("utf-8")).hexdigest()
man["output_bytes"] = len(k2.encode("utf-8"))
man_path.write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
print("app_k.tex", len(k2.encode("utf-8")), "bytes; manifest refreshed")
