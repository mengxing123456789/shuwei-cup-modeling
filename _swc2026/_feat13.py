# -*- coding: utf-8 -*-
"""Check the 13-feature scorecard claim and whether the main body still reports five mappings."""
import io
import json
import os
import re

ROOT = r"E:\数学建模\_swc2026"
M = os.path.join(ROOT, "SWC2026_C")
A = os.path.join(ROOT, "SWC2026_C_ALT_BACKUP")

band = json.loads(io.open(os.path.join(A, "refs", "official_standard.json"), encoding="utf-8").read())
print("=== ALT refs/official_standard.json ===")
print("  n_papers:", band.get("n_papers"), " first_prize:", band.get("n_first_prize_verified"))
print("  presence keys:")
pres = band.get("presence", {})
for k, v in list(pres.items())[:30]:
    print("    %-28s %s" % (k, v))
print("  presence_pct:")
for k, v in list(band.get("presence_pct", {}).items())[:30]:
    print("    %-28s %s" % (k, v))

print("\n=== main body: five-mapping / sensitivity reporting ===")
main = io.open(os.path.join(M, "main.tex"), encoding="utf-8").read()
body = main.split(r"\section{Notation}")[0]
for kw in ("mapping", "service", "sensitivity", "0.75", "1.50", "alpha", "beta"):
    print("  %-12s %d" % (kw, body.count(kw)))
print("\n  sentences containing 'mapping':")
for m in re.finditer(r"[^.]*mapping[^.]*\.", body):
    print("   *", m.group(0).strip().replace("\n", " ")[:190])

print("\n=== is tab:p3nom orphaned in the appendix? ===")
appn = io.open(os.path.join(M, "tables", "app_n.tex"), encoding="utf-8").read()
print("  in app_n.tex :", "tab:p3nom" in appn)
print("  body refs    :", body.count("tab:p3nom"))
print("  whole refs   :", main.count("ref{tab:p3nom}"))
