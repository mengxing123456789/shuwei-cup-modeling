# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""make_appendix_n_p3.py -- LaTeX table for the P3 one-at-a-time sensitivity."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "tables", "tab_p3_sensitivity.tex")

d = json.load(open(os.path.join(DATA, "up9_p3_sensitivity.json"), encoding="utf-8"))
order = ["q_hi", "gate", "late_tol", "mix", "gam", "ksk", "qsl", "tau"]
pretty = {"q_hi": "reservation quantile $q$", "gate": "release gate",
          "late_tol": "lateness tolerance (s)", "mix": "selector mix",
          "gam": "blocking weight", "ksk": "slack coefficient $k$",
          "qsl": "slack quantile", "tau": "review hurdle $\\tau$"}

lines = []
lines.append(r"\begin{table}[H]")
lines.append(r"\centering")
lines.append(r"\caption{One-at-a-time sensitivity of the frozen Part III policy. "
             r"Every other sub-parameter is held at its selected value; each row moves "
             r"one knob to two nearby values and re-runs all 30 seeds on five mappings. "
             r"$\Delta$ is the weighted on-time rate in percentage points against the frozen row.}")
lines.append(r"\label{tab:p3-sensitivity}")
lines.append(r"\footnotesize")
lines.append(r"\begin{tabular}{llrrr}")
lines.append(r"\toprule")
lines.append(r"Case & Knob moved & Values & $\Delta$ range (pt) & Cost ratio \\")
lines.append(r"\midrule")
for case, blob in d["cases"].items():
    rows = blob["rows"][1:]
    for key in order:
        rs = [r for r in rows if r["key"] == key]
        if not rs:
            continue
        vals = ", ".join(r["name"].split("=")[1] for r in rs)
        ds = [r["delta_all30_pt"] for r in rs]
        cr = [r["cost_ratio"] for r in rs if r["cost_ratio"] is not None]
        dr = f"[{min(ds):+.2f}, {max(ds):+.2f}]"
        crr = f"[{min(cr):.3f}, {max(cr):.3f}]" if cr else "--"
        lines.append(f"{case} & {pretty[key]} & {vals} & {dr} & {crr} \\\\")
    lines.append(r"\midrule")
lines[-1] = r"\bottomrule"
lines.append(r"\end{tabular}")
lines.append(r"\end{table}")

with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")
print("wrote", OUT, len(lines), "lines")