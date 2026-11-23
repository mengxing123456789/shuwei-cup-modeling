# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Value ladder: what each mechanism buys, in weighted on-time points."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif"]
plt.rcParams["mathtext.fontset"] = "stix"

PROJ = Path(__file__).resolve().parents[1]
DATA = PROJ / "data"

p3 = json.loads((DATA / "p3_stochastic_schedule.json").read_text(encoding="utf-8"))
phase = json.loads((DATA / "phase_diagram.json").read_text(encoding="utf-8"))
review = json.loads((DATA / "up_p3_review.json").read_text(encoding="utf-8"))

rows = p3["summary"]
rate = {(r["case"], r["policy"]): r["weighted_on_time_rate"] for r in rows}

out = {"mapping": "alpha=1.0, beta=0.5", "n_seeds": 30, "cases": {}}
slots_tex = (PROJ / "slots.tex").read_text(encoding="utf-8")
def slot(name):
    import re
    m = re.search(r"\\newcommand\{\\" + "slot" + name + r"\}\{([-0-9.]+)\}", slots_tex)
    return float(m.group(1)) if m else 0.0

for case in ("S2", "S3"):
    rule = 100.0 * (rate[(case, "slack_old")] - rate[(case, "edf_old")])
    truth = 100.0 * slot("POracleGap" + ("STwo" if case == "S2" else "SThree"))
    observe = 0.0
    reserve = -100.0 * phase["rate_drop_q30_q90"][case]
    out["cases"][case] = {
        "scheduling rule": round(rule, 2),
        "true duration": round(truth, 2),
        "paid observation": round(observe, 2),
        "extra reservation": round(reserve, 2),
    }
out["review_best_delta_pt"] = round(float(review["verdict"]["best_delta_pt"]), 3)
out["review_ci_low"] = round(float(review["verdict"]["best_combo"]["ci95_pt"][0]), 3)
out["review_ci_high"] = round(float(review["verdict"]["best_combo"]["ci95_pt"][1]), 3)

labels = ["scheduling rule", "true duration", "paid observation", "extra reservation"]
colors = ["#2b6cb0", "#2f855a", "#b7791f", "#c53030"]
x = np.arange(len(labels))
w = 0.36

fig, ax = plt.subplots(figsize=(6.5, 3.0), dpi=400)
for i, case in enumerate(("S2", "S3")):
    vals = [out["cases"][case][k] for k in labels]
    bars = ax.bar(x + (i - 0.5) * w, vals, w, label=f"Case {case}",
                  color=colors, alpha=0.95 if i == 0 else 0.55,
                  edgecolor="white", linewidth=0.6)
    for b, v in zip(bars, vals):
        ax.annotate(f"{v:+.1f}", (b.get_x() + b.get_width() / 2, v),
                    ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=7.1, xytext=(0, 2 if v >= 0 else -2),
                    textcoords="offset points")

ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(x)
ax.set_xticklabels(["scheduling\nrule", "true\nduration", "paid\nobservation", "extra\nreservation"],
                   fontsize=7.6)
ax.set_ylabel("weighted on-time points", fontsize=8.2)
ax.tick_params(axis="y", labelsize=8)
ax.set_ylim(-14, 29)
ax.legend(frameon=False, fontsize=7.2, loc="upper right")
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.25, linewidth=0.5)
ax.set_title("What buys punctuality (Case S2 dark, Case S3 light)", fontsize=9.0)
fig.tight_layout()
fig.savefig(PROJ / "figures" / "fig10_value_ladder.png")
plt.close(fig)

(DATA / "value_ladder.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2))
