# -*- coding: utf-8 -*-
"""Inspect up2_p3 strategies: do they carry all eleven official metrics?"""
import json
from pathlib import Path

D = Path(r"E:\数学建模\_swc2026\SWC2026_C\data")
j = json.loads((D / "up2_p3.json").read_text(encoding="utf-8"))
st = j["strategies"]
print("strategies type:", type(st), "keys:", list(st.keys())[:8])
k0 = next(iter(st))
print("\nstrategy", k0, "->", list(st[k0].keys())[:20])
print(json.dumps(st[k0], indent=1)[:2000])
