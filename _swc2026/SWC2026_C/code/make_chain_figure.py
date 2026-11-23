# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Chain figure, two panels: one job on a timeline, and the decision it feeds.

Matplotlib primitives only, so the printed page stays vector-crisp and the
serif family matches the body.  The numeric anchors are the protocol constants
of the official C statement: prefix 0.2/0.6/1.0 s, request cost 1.0, at most
two requests per job, predicted finish p = alpha d + beta, reservation b.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

C = Path(__file__).resolve().parent.parent
OUT = C / "figures" / "fig_chain.png"
RV = json.loads((C / "data" / "up2_p3review.json").read_text(encoding="utf-8"))
N_CELLS = len(RV["cells"])
BEST = max(float(c["delta_pt"]) for c in RV["cells"])

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.04,
})

INK = "#1f2933"
MUTED = "#5b6770"
BLUE = "#2b6cb0"
GREEN = "#2f855a"
ORANGE = "#b7791f"
RED = "#b83232"
LIGHT = "#f4f6f8"


def box(ax, x, y, w, h, title, lines=(), edge=INK, fs=7.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.008,rounding_size=0.012",
                                linewidth=0.9, edgecolor=edge, facecolor="white",
                                zorder=2))
    ax.text(x + 0.010, y + h - 0.045, title, ha="left", va="top",
            fontsize=8.0, color=edge, fontweight="bold", zorder=3)
    if lines:
        dy = 0.19 if h >= 0.75 else 0.095
        ax.text(x + 0.010, y + h - dy, "\n".join(lines), ha="left", va="top",
                fontsize=fs, color=INK, linespacing=1.45, zorder=3)


def arrow(ax, p, q, color=MUTED, lw=0.9, style="-|>"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=7.0,
                                 linewidth=lw, color=color, shrinkA=1.0,
                                 shrinkB=1.0, zorder=1))


fig, (axA, axB) = plt.subplots(1, 2, figsize=(7.1, 2.85),
                               gridspec_kw={"width_ratios": [1.28, 1.0]})

# --------------------------------------------------------------------------
# Panel A: one job on a timeline
# --------------------------------------------------------------------------
axA.set_xlim(0, 10.2)
axA.set_ylim(0, 3.35)
axA.axis("off")
axA.text(0.0, 3.30, "A  one job on the timeline", ha="left", va="top",
         fontsize=9.2, color=INK, fontweight="bold")

# the job's own time line
axA.annotate("", xy=(9.7, 1.62), xytext=(0.35, 1.62),
             arrowprops=dict(arrowstyle="-|>", lw=0.9, color=INK,
                             mutation_scale=7.0, shrinkA=0, shrinkB=0))
axA.text(9.65, 1.42, "time", ha="right", va="top", fontsize=7.0, color=MUTED)

# release, prefix ends, request, due
axA.plot([0.45], [1.62], marker="o", ms=4.2, color=BLUE)
axA.text(0.45, 1.82, "release", ha="center", va="bottom", fontsize=7.0, color=BLUE)

for i, p in enumerate((0.85, 1.35, 1.95)):
    axA.plot([p], [1.62], marker="|", ms=8, color=BLUE)
axA.text(1.40, 2.06, "prefix 0.2 / 0.6 / 1.0 s", ha="center", va="bottom",
         fontsize=7.0, color=BLUE)

axA.plot([1.95], [1.62], marker="D", ms=4.4, color=ORANGE)
axA.text(1.95, 1.34, "request", ha="center", va="top", fontsize=7.0, color=ORANGE)
axA.text(2.15, 1.16, "cost 1.0, at most 2 per job", ha="left", va="top",
         fontsize=6.7, color=ORANGE)

axA.plot([8.85, 8.85], [1.35, 1.90], color=RED, lw=1.6)
axA.text(8.85, 1.96, "due", ha="center", va="bottom", fontsize=7.0, color=RED)

# predicted finish and reservation push
axA.annotate("", xy=(4.20, 0.55), xytext=(2.05, 0.55),
             arrowprops=dict(arrowstyle="-|>", lw=0.8, color=GREEN,
                             mutation_scale=7.0, shrinkA=0, shrinkB=0))
axA.plot([4.20], [0.55], marker="s", ms=4.2, color=GREEN)
axA.text(4.10, 0.92, r"$p=\alpha d+\beta$", ha="right", va="bottom",
         fontsize=7.0, color=GREEN)

axA.annotate("", xy=(6.15, 0.55), xytext=(4.35, 0.55),
             arrowprops=dict(arrowstyle="-|>", lw=1.0, color=ORANGE,
                             mutation_scale=7.0, shrinkA=0, shrinkB=0))
axA.text(5.35, 0.92, "reservation $b$", ha="center", va="bottom",
         fontsize=7.0, color=ORANGE)
axA.plot([6.15], [0.55], marker="o", ms=4.0, color=ORANGE)
axA.text(6.28, 0.42, r"start $s'=s+\max(p,b)$", ha="left", va="top",
         fontsize=6.7, color=ORANGE)

axA.text(0.0, 0.05, "the prefix fixes what the forecaster sees; the reservation is the only decision taken on it",
         ha="left", va="bottom", fontsize=6.4, color=MUTED)

# --------------------------------------------------------------------------
# Panel B: the decision the forecast feeds
# --------------------------------------------------------------------------
axB.set_xlim(0, 10.0)
axB.set_ylim(0, 3.35)
axB.axis("off")
axB.text(0.0, 3.30, "B  the decision the forecast feeds", ha="left", va="top",
         fontsize=9.2, color=INK, fontweight="bold")

box(axB, 0.15, 2.05, 3.0, 0.85, "duration law $F_d$",
    ("fitted on train jobs",), BLUE, fs=6.8)
box(axB, 3.55, 2.05, 3.0, 0.85, "threshold", ("$P(\\mathrm{on\\ time})\\geq q$",), ORANGE, fs=6.8)
box(axB, 6.95, 2.05, 2.85, 0.85, "policy $\\pi$", ("keep $b$, then EDF",), GREEN, fs=6.8)

arrow(axB, (3.15, 2.47), (3.55, 2.47), MUTED)
arrow(axB, (6.55, 2.47), (6.95, 2.47), MUTED)

# tests box
axB.add_patch(FancyBboxPatch((0.15, 0.12), 9.65, 1.45,
                             boxstyle="round,pad=0.008,rounding_size=0.012",
                             linewidth=0.8, edgecolor=MUTED, facecolor=LIGHT, zorder=1))
axB.text(0.30, 1.45, "what the three tests find", ha="left", va="top",
         fontsize=7.6, color=INK, fontweight="bold", zorder=3)
axB.text(0.30, 1.15,
         "test 1   the plateau is flat: moving $q$ from 0.50 to 0.90 only loses rate\n"
         "test 2   the law is calibrated: all nine (case, mapping) cells hit the realised rate\n"
         f"test 3   a second look buys no rate: {N_CELLS} cells, best {BEST:+.2f} points",
         ha="left", va="top", fontsize=6.7, color=INK, linespacing=1.55, zorder=3)

arrow(axB, (8.35, 2.05), (8.35, 1.60), MUTED)
axB.text(8.25, 1.80, "scored on held-out seeds", ha="right", va="center",
         fontsize=6.4, color=MUTED)

fig.savefig(OUT, dpi=400)
plt.close(fig)
print("saved", OUT)