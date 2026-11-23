# -*- coding: utf-8 -*-
"""Dump the per-policy metric fields for the stochastic P3 run (summary is a list)."""
import json
from pathlib import Path

D = Path(r"E:\数学建模\_swc2026\SWC2026_C\data")
j = json.loads((D / "p3_stochastic_schedule.json").read_text(encoding="utf-8"))
s = j["summary"]
print("summary type:", type(s), "len:", len(s))
print("first row keys:", list(s[0].keys()))
print(json.dumps(s[0], indent=1)[:1200])
print("\nall policies seen:", sorted({r.get("policy") for r in s}))
print("cases seen:", sorted({str(r.get("case")) for r in s}))
print("mappings seen:", sorted({str(r.get("mapping")) for r in s}))
