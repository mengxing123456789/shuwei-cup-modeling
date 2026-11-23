# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""make_table_loto.py -- LOTO table generated from p1b_loto.json (no hand-typed cells)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "tables", "tab_loto.tex")

d = json.load(open(os.path.join(DATA, "p1b_loto.json"), encoding="utf-8"))
ref = d["in_sample_reference"]["per_class_matched_to_loto_eval_sets"]
rows = [r for r in d["per_class"] if r.get("tier") == "primary" and not r.get("skipped")]

lines = [r"\begin{table}[htbp]", r"\centering",
         r"\caption{Leave-one-task-out on the training half. Each row retrains the detector with one",
         r"semantic task class removed and scores it on that class; the reference is the same",
         r"architecture trained with the class present, evaluated on the same windows.}",
         r"\label{tab:loto}", r"\footnotesize",
         r"\begin{tabular}{lrrrrr}", r"\toprule",
         r"Held-out class & Records & Positives & AUC out & AUC in & Gap \\", r"\midrule"]
for r in rows:
    m = ref.get(r["task"], {})
    in_auc = m.get("auc")
    gap = (in_auc - r["auc"]) if (in_auc is not None and r["auc"] is not None) else None
    lines.append("%s & %d & %d & %.4f & %.4f & %+.4f \\\\" %
                 (r["task"], r["n_records"], r["positives"], r["auc"], in_auc, gap))
s = d["summary"]
lines.append(r"\midrule")
lines.append(r"Mean over the three & & & %.4f & %.4f & %+.4f \\" %
             (s["mean_auc_loto"], s["mean_auc_in_sample_reference"], s["gap_mean"]))
lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("wrote", OUT, len(rows), "rows")