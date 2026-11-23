# -*- coding: utf-8 -*-
"""Score both papers against the 17 presence features ALT itself uses, plus AI-report check."""
import io
import json
import os
import re

ROOT = r"E:\数学建模\_swc2026"
M = os.path.join(ROOT, "SWC2026_C")
A = os.path.join(ROOT, "SWC2026_C_ALT_BACKUP")

main = io.open(os.path.join(M, "main.tex"), encoding="utf-8").read()
alt = io.open(os.path.join(A, "main.tex"), encoding="utf-8").read()

FEATS = {
    "has_monte_carlo": [r"monte\s*carlo", r"bootstrap"],
    "has_sensitivity": [r"sensitiv"],
    "has_backtest": [r"back\s*-?\s*test"],
    "has_limitation": [r"limitation", r"weakness", r"fails when"],
    "has_provenance": [r"sha256", r"provenance", r"ledger"],
    "has_gpu": [r"\bgpu\b", r"cuda"],
    "has_epoch": [r"\bepoch"],
    "has_loss": [r"\bloss\b", r"objective function"],
    "has_hyperparam": [r"hyper-?param"],
    "has_crossval": [r"cross-?valid", r"\bfold\b", r"leave-one-out"],
    "has_neural": [r"neural", r"\btcn\b", r"\bgru\b", r"\bmlp\b", r"transformer"],
    "has_sklearn": [r"scikit", r"sklearn", r"ridge", r"lightgbm"],
    "has_ci": [r"confidence interval", r"\bci\b", r"credible interval", r"conformal"],
    "has_robust": [r"robust"],
    "has_assumption": [r"assumption"],
    "has_error_metric": [r"\brmse\b", r"\bmse\b", r"\bmae\b", r"\bari\b", r"average precision"],
    "has_software": [r"python", r"matlab", r"software", r"numpy", r"pytorch", r"torch"],
}

print("%-22s %6s %6s" % ("feature", "MAIN", "ALT"))
print("-" * 36)
mscore = ascore = 0
for k, pats in FEATS.items():
    m = any(re.search(p, main, re.I) for p in pats)
    a = any(re.search(p, alt, re.I) for p in pats)
    mscore += m
    ascore += a
    print("%-22s %6s %6s" % (k, "yes" if m else "-", "yes" if a else "-"))
print("-" * 36)
print("%-22s %6d %6d  of %d" % ("TOTAL", mscore, ascore, len(FEATS)))

print("\n=== AI tool usage report ===")
for name, t in (("MAIN", main), ("ALT", alt)):
    has_sec = bool(re.search(r"AI\s*(tool|工具)", t, re.I))
    has_tab = bool(re.search(r"tab:aitools|AI.{0,20}table", t, re.I))
    ds = t.count("DeepSeek")
    print("  %-4s ai_section=%-5s ai_table=%-5s DeepSeek=%d" % (name, has_sec, has_tab, ds))
    for m in re.finditer(r"[^\n]*(AI\s*[Tt]ool|generative tool)[^\n]*", t):
        print("       ", m.group(0).strip()[:120])

print("\n=== epsilon / chance-constraint scan in MAIN? ===")
for kw in ("epsilon", r"\\varepsilon", "chance", "re-plan", "replan", "fallback"):
    print("  %-12s %d" % (kw, len(re.findall(kw, main, re.I))))
