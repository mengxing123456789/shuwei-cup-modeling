# -*- coding: utf-8 -*-
"""Dump p3_scheduling.json summary rows: which of the 11 official metrics exist."""
import json
from pathlib import Path

D = Path(r"E:\数学建模\_swc2026\SWC2026_C\data")
j = json.loads((D / "p3_scheduling.json").read_text(encoding="utf-8"))
s = j["summary"]
print("type", type(s), "len", len(s))
r0 = s[0] if isinstance(s, list) else next(iter(s.values()))
print("row keys:", list(r0.keys()))
print(json.dumps(r0, indent=1)[:1400])
print("\npolicies:", sorted({r.get("policy") for r in s}) if isinstance(s, list) else "")
