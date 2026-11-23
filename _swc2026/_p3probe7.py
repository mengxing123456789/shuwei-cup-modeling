# -*- coding: utf-8 -*-
"""Check which metrics the frozen adaptive-policy engine recorded."""
import json
from pathlib import Path

D = Path(r"E:\数学建模\_swc2026\SWC2026_C\data")
j = json.loads((D / "up2_p3.json").read_text(encoding="utf-8"))
print("top keys:", list(j.keys()))
for k in ("cases", "results", "summary"):
    if k in j:
        v = j[k]
        print(k, type(v), (list(v.keys())[:6] if isinstance(v, dict) else len(v)))
c = j.get("cases")
if isinstance(c, dict):
    k0 = next(iter(c))
    print("\ncase", k0, "keys:", list(c[k0].keys())[:20])
    print(json.dumps(c[k0], indent=1)[:1600])
