# -*- coding: utf-8 -*-
"""Inspect the P3 result files to see which of the eleven official metrics exist."""
import json
from pathlib import Path

D = Path(r"E:\数学建模\_swc2026\SWC2026_C\data")

for name in ["p3_stochastic_schedule.json", "p3_scheduling.json", "p3_improved_verify.json"]:
    p = D / name
    if not p.exists():
        print(name, "MISSING")
        continue
    j = json.loads(p.read_text(encoding="utf-8"))
    print("=" * 78)
    print(name, p.stat().st_size, "B")
    print("top keys:", list(j.keys())[:12])
    s = j.get("summary")
    if isinstance(s, dict):
        k = list(s.keys())[:6]
        print("summary keys:", list(s.keys()))
        for kk in k:
            v = s[kk]
            if isinstance(v, dict):
                print("  ", kk, "->", list(v.keys())[:20])
            else:
                print("  ", kk, "=", v)
    pol = j.get("policies") or j.get("by_policy") or j.get("results")
    if isinstance(pol, dict):
        print("policy names:", list(pol.keys())[:12])
        first = next(iter(pol.values()))
        if isinstance(first, dict):
            print("policy fields:", list(first.keys())[:24])
