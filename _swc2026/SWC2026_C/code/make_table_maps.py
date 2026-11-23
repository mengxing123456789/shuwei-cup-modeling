# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# -*- coding: utf-8 -*-
"""Build the five-mapping table for the body from data/up2_p3.json.

Every cell is a number the frozen rule and the capacity-aware reference actually produced on
the official seeds, under the five service mappings the statement publishes. The point of the
table is that the mapping moves the on-time rate by an order of magnitude more than any
scheduler-only change does, which is why the mapping stays in the paper as the dominant factor.
"""
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "tables" / "tab_maps.tex"

KEYS = [
    ("a1.00_b0.50", r"$\alpha=1.00$, $\beta=0.50$ (nominal)"),
    ("a0.75_b0.50", r"$\alpha=0.75$, $\beta=0.50$"),
    ("a1.50_b0.50", r"$\alpha=1.50$, $\beta=0.50$"),
    ("a1.00_b0.00", r"$\alpha=1.00$, $\beta=0.00$"),
    ("a1.00_b1.00", r"$\alpha=1.00$, $\beta=1.00$"),
]


def pct(x):
    return f"{100.0 * x:.1f}"


def main():
    d = json.load(io.open(DATA / "up2_p3.json", encoding="utf-8"))
    pm = d["per_case_map"]

    lines = []
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(r"\caption{The five service mappings the statement publishes, with the "
                 r"capacity-aware reference and the frozen rule on the same \slotNSeeds{} official "
                 r"seeds. Every entry is a weighted on-time rate in per cent. The last column is the "
                 r"paired gain of the frozen rule over the reference inside one mapping, so the "
                 r"comparison never mixes mappings.}")
    lines.append(r"\label{tab:maps}")
    lines.append(r"\scriptsize")
    lines.append(r"\setlength{\tabcolsep}{4.0pt}")
    lines.append(r"\begin{tabular}{lrrrr}")
    lines.append(r"\toprule")
    lines.append(r"Mapping & Ref.\ S2 & Ours S2 & Ref.\ S3 & Ours S3 \\")
    lines.append(r"\midrule")
    for key, label in KEYS:
        row = [label]
        for case in ("S2", "S3"):
            s = pm[case]["slack_old"][key]["on_time_all30"]
            f = pm[case]["FROZEN"][key]["on_time_all30"]
            row.append(pct(s))
            row.append(pct(f))
        lines.append(" & ".join(row) + r" \\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    text = "\n".join(lines) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("wrote", OUT, len(text), "chars")

    # The prose needs the spread, not every cell, so summarise it into its own JSON.
    summary = {"_meta": {"source": "data/up2_p3.json", "seeds": 30,
                         "mappings": [k for k, _ in KEYS]}, "cases": {}}
    for case in ("S2", "S3"):
        vals = [(k, pm[case]["slack_old"][k]["on_time_all30"],
                 pm[case]["FROZEN"][k]["on_time_all30"]) for k, _ in KEYS]
        ref = [v[1] for v in vals]
        ours = [v[2] for v in vals]
        gains = [o - r for _, r, o in vals]
        summary["cases"][case] = {
            "ref_min": min(ref), "ref_max": max(ref),
            "ours_min": min(ours), "ours_max": max(ours),
            "ref_span_pt": 100.0 * (max(ref) - min(ref)),
            "ours_span_pt": 100.0 * (max(ours) - min(ours)),
            "gain_min_pt": 100.0 * min(gains),
            "gain_max_pt": 100.0 * max(gains),
            "gain_mean_pt": 100.0 * sum(gains) / len(gains),
            "n_saturated": sum(1 for g in gains if abs(g) < 1e-9),
        }
        print(case, "ref span %.1f pt, ours span %.1f pt, min gain %.1f, max gain %.1f" % (
            summary["cases"][case]["ref_span_pt"], summary["cases"][case]["ours_span_pt"],
            summary["cases"][case]["gain_min_pt"], summary["cases"][case]["gain_max_pt"]))
    io.open(DATA / "up22_mapping_spread.json", "w", encoding="utf-8", newline="\n").write(
        json.dumps(summary, indent=1, ensure_ascii=False))
    print("wrote up22_mapping_spread.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
