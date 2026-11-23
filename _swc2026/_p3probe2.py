# -*- coding: utf-8 -*-
"""Dump the per-policy metric fields for the stochastic P3 run."""
import json
from pathlib import Path

D = Path(r"E:\数学建模\_swc2026\SWC2026_C\data")
j = json.loads((D / "p3_stochastic_schedule.json").read_text(encoding="utf-8"))
s = j["summary"]
print("summary keys:", list(s.keys()))
for case, blk in s.items():
    print("\n--", case, "->", list(blk.keys()) if isinstance(blk, dict) else type(blk))
    if isinstance(blk, dict):
        for pol, m in blk.items():
            if isinstance(m, dict):
                print("   ", pol, "->", list(m.keys()))
                break
