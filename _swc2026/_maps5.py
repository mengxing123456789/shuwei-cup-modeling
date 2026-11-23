# -*- coding: utf-8 -*-
"""Verify the two claims that decide the choice: five-mapping reporting and paired trials."""
import io
import json
import os
import re

ROOT = r"E:\数学建模\_swc2026"
M = os.path.join(ROOT, "SWC2026_C")
A = os.path.join(ROOT, "SWC2026_C_ALT_BACKUP")

print("=== main paper: does the BODY report all five mappings with numbers? ===")
main = io.open(os.path.join(M, "main.tex"), encoding="utf-8").read()
body = main.split(r"\section{Notation}")[0]
# find every slot that names a mapping
maps = sorted(set(re.findall(r"\\slot(PMap\w+|PImp\w*All\w+|PStoch\w+)", main)))
print("  mapping-related slots in main.tex:", len(maps))
for s in maps[:24]:
    print("   ", s)

print("\n  slots.tex definitions for them:")
slots = io.open(os.path.join(M, "slots.tex"), encoding="utf-8").read()
for s in maps[:24]:
    m = re.search(r"\\newcommand\{\\slot%s\}\{([^}]*)\}" % s, slots)
    print("    %-26s = %s" % (s, m.group(1) if m else "MISSING"))

print("\n=== official audit: paired trial count ===")
aud = json.loads(io.open(os.path.join(M, "data", "p3_official_audit.json"), encoding="utf-8").read())
print("  p3_official_audit summary:", json.dumps(aud.get("summary", {}), ensure_ascii=False)[:300])
cells = aud.get("cells", {})
print("  cells:", len(cells), "sample:", list(cells.items())[:1])

print("\n=== up2_p3: per-mapping paired deltas ===")
u = json.loads(io.open(os.path.join(M, "data", "up2_p3.json"), encoding="utf-8").read())
print("  top keys:", list(u.keys()))
for k in ("paired", "blocks", "per_mapping", "gate_mandated", "gate_self_imposed"):
    if k in u:
        print("  %-18s %s" % (k, json.dumps(u[k], ensure_ascii=False)[:260]))

print("\n=== ALT: how many paired trials does it claim? ===")
alt = io.open(os.path.join(A, "main.tex"), encoding="utf-8").read()
for m in re.finditer(r"[^.]*\b(450|five mappings|five service)\b[^.]*\.", alt):
    print("  *", m.group(0).strip().replace("\n", " ")[:200])
