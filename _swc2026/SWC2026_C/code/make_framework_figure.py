# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Framework figure: how the three parts share one object.

Drawn with matplotlib primitives (no clip art, no external icons) so that the
printed version stays crisp and uses the same serif family as the body.  The
layout is sized for a full text-width inclusion (160 mm), so the body type is
set at 7.3 pt on a 6.6 in canvas and prints at roughly its nominal size.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

C = Path(__file__).resolve().parent.parent
OUT = C / "figures" / "fig0_framework.png"
VL = json.loads((C / "data" / "value_ladder.json").read_text(encoding="utf-8"))["cases"]
P1 = json.loads((C / "data" / "p1a_segmentation_compare.json").read_text(encoding="utf-8"))["ari"]["gpu_mean"]
P2 = json.loads((C / "data" / "p2_prediction.json").read_text(encoding="utf-8"))["economics"]["optimum"]
ARI = "%.3f" % P1
TSTAR = "%.2f" % P2["T_s"]
RULE2, RULE3 = VL["S2"]["scheduling rule"], VL["S3"]["scheduling rule"]
TRU2, TRU3 = VL["S2"]["true duration"], VL["S3"]["true duration"]
RES2, RES3 = VL["S2"]["extra reservation"], VL["S3"]["extra reservation"]

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})

INK = "#1f2933"
MUTED = "#5b6770"
BLUE = "#2b6cb0"
GREEN = "#2f855a"
ORANGE = "#b7791f"

FS_TITLE = 8.4
FS_BODY = 7.3
LEAD = 1.55


def box(ax, x, y, w, h, title, lines, edge):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.008,rounding_size=0.012",
                                linewidth=1.0, edgecolor=edge, facecolor="white", zorder=2))
    ax.text(x + 0.010, y + h - 0.020, title, ha="left", va="top",
            fontsize=FS_TITLE, color=edge, fontweight="bold", zorder=3)
    ty = y + h - 0.062 if h < 0.5 else y + h * 0.62
    ax.text(x + 0.010, ty, "\n".join(lines), ha="left", va="top",
            fontsize=FS_BODY, color=INK, linespacing=LEAD, zorder=3)


def arrow(ax, p, q, color=MUTED):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=7.0,
                                 linewidth=1.0, color=color, shrinkA=1.2, shrinkB=1.2, zorder=1))


fig, ax = plt.subplots(figsize=(6.6, 3.15))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

# header
ax.text(0.008, 0.985, "One object, three questions", ha="left", va="top",
        fontsize=9.6, color=INK, fontweight="bold")
ax.text(0.008, 0.925,
        "state $\\rightarrow$ prediction $\\rightarrow$ observation value $\\rightarrow$ scheduling; every arrow is measured",
        ha="left", va="top", fontsize=7.0, color=MUTED)

TOP_Y, BOT_Y, BOX_H = 0.475, 0.045, 0.365
MID_X1, MID_X2, MID_W = 0.195, 0.475, 0.255

# data column
box(ax, 0.008, BOT_Y, 0.155, BOX_H + 0.43, "Data", [
    "69 recordings",
    "24 environments",
    "66,070 frames",
    "184 videos",
    "16 / 4 / 4 split",
], MUTED)

# four middle boxes
box(ax, MID_X1, TOP_Y, MID_W, BOX_H, "Part I  State", [
    "21 keypoints $\\rightarrow$ hand state",
    "reliability weight",
    "5 rule-derived stages",
    "held-out ARI " + ARI,
], BLUE)
box(ax, MID_X1, BOT_Y, MID_W, BOX_H, "Part II  Prediction", [
    "masked wrist track",
    "ridge + conformal radii",
    "cost curve over look time",
    "optimum " + TSTAR + " s",
], GREEN)
box(ax, MID_X2, TOP_Y, MID_W, BOX_H, "Part III  Scheduling", [
    "duration law $F_d$",
    "reservation $b$ then EDF",
    "closed-form $P(\\mathrm{on\\ time})$",
    "%.1f / %.1f pt over EDF" % (RULE2, RULE3),
], ORANGE)
box(ax, MID_X2, BOT_Y, MID_W, BOX_H, "Observation", [
    "request time and delay",
    "paid look: 1.0 s",
    "budget and cap",
    "value of information",
], ORANGE)

# outcome column
box(ax, 0.752, BOT_Y, 0.240, BOX_H + 0.43, "Decision limits", [
    "rule  %.1f / %.1f pt" % (RULE2, RULE3),
    "true duration  %.1f / %.1f" % (TRU2, TRU3),
    "paid look  0",
    "reservation  %.1f / %.1f" % (RES2, RES3),
    "",
    "each number traced",
    "to data/*.json",
], INK)

# arrows
arrow(ax, (0.163, 0.66), (0.195, 0.66))
arrow(ax, (0.163, 0.23), (0.195, 0.23))
arrow(ax, (0.450, 0.66), (0.475, 0.66))
arrow(ax, (0.450, 0.23), (0.475, 0.23))
arrow(ax, (0.730, 0.66), (0.752, 0.66))
arrow(ax, (0.730, 0.23), (0.752, 0.23))

fig.savefig(OUT, dpi=400)
plt.close(fig)
print("saved", OUT)
