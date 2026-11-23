# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Regenerate the appendix figures that were too small or unevenly paired:
the per-dataset flag distribution, the two appendix-N panels (equal size), and
the value ladder (larger, legend outside the axes)."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif"]
plt.rcParams["mathtext.fontset"] = "stix"
plt.rcParams["axes.linewidth"] = 0.7

PROJ = Path(__file__).resolve().parents[1]
DATA = PROJ / "data"
FIG = PROJ / "figures"

NAVY = "#1f3b73"
BLUE = "#2b6cb0"
ORANGE = "#c05621"
GREEN = "#2f6b3f"
RED = "#9b2c2c"
GRAY = "#6b7280"


def _clean(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color="#E6E6E6", linewidth=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=7.6)


# ---------------------------------------------------------------- Figure 8
def fig_bad_ratio():
    recs = pd.read_csv(DATA / "panel_records.csv")
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.6), dpi=400,
                           gridspec_kw={"width_ratios": [1, 1]})
    bins = np.linspace(0, max(5.0, 100 * recs.badL.max()), 22)
    for d, c in zip(["EgoDemo", "EgoPro", "EgoStandard"], [BLUE, ORANGE, GREEN]):
        v = 100 * recs.loc[recs.dataset == d, "badL"].values
        ax[0].hist(v, bins=bins, alpha=0.60, label=d, color=c,
                   edgecolor="white", linewidth=0.4)
    ax[0].set_xlabel("flagged frames per record (%)", fontsize=8.2)
    ax[0].set_ylabel("records", fontsize=8.2)
    ax[0].set_title("Distribution across records", fontsize=9.0)
    ax[0].legend(frameon=False, fontsize=7.2, loc="upper right")

    m = recs.groupby("dataset")[["badL", "badR"]].mean().loc[
        ["EgoDemo", "EgoPro", "EgoStandard"]] * 100
    x = np.arange(3)
    b1 = ax[1].bar(x - 0.19, m.badL, 0.38, label="left hand", color=NAVY)
    b2 = ax[1].bar(x + 0.19, m.badR, 0.38, label="right hand", color=ORANGE)
    for bars in (b1, b2):
        for b in bars:
            h = b.get_height()
            ax[1].annotate(f"{h:.2f}", (b.get_x() + b.get_width() / 2, h),
                           ha="center", va="bottom", fontsize=7.0,
                           xytext=(0, 1.5), textcoords="offset points")
    ax[1].set_xticks(x)
    ax[1].set_xticklabels(["EgoDemo", "EgoPro", "EgoStandard"], fontsize=8.0)
    ax[1].set_ylabel("mean flagged share (%)", fontsize=8.2)
    ax[1].set_title("Left versus right hand", fontsize=9.0)
    ax[1].legend(frameon=False, fontsize=7.2, loc="upper left")
    for a in ax:
        _clean(a)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_bad_ratio.png")
    plt.close(fig)
    print("wrote fig2_bad_ratio.png")


# ------------------------------------------------------ Appendix N, panel (a)
def fig_n_badshare():
    """Per-record flag share in the 38 annotated records (17 carry any flag)."""
    ann = json.loads((DATA / "p1_badtype.json").read_text(encoding="utf-8"))
    recs = ann["records"]
    vals = [(100.0 * r["n_bad_frames"] / r["n_frames"], r["dataset"])
            for r in recs]
    vals = sorted([v for v in vals if v[0] > 0], key=lambda x: -x[0])
    share = [v[0] for v in vals]
    sets = [v[1] for v in vals]
    cmap = {"EgoDemo": BLUE, "EgoPro": ORANGE, "EgoStandard": GREEN}
    fig, ax = plt.subplots(figsize=(3.45, 2.5), dpi=400)
    ax.bar(np.arange(len(share)), share, color=[cmap[d] for d in sets],
           width=0.72, edgecolor="white", linewidth=0.35)
    ax.set_xlabel(f"flagged records, largest first ({len(share)} of {len(recs)})",
                  fontsize=7.8)
    ax.set_ylabel("flagged frames per record (%)", fontsize=8.0)
    ax.set_xlim(-0.8, len(share) - 0.2)
    ax.set_xticks([])
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cmap.values()]
    ax.legend(handles, list(cmap), frameon=False, fontsize=6.6, loc="upper right")
    _clean(ax)
    fig.tight_layout()
    fig.savefig(FIG / "fig_n_badshare.png")
    plt.close(fig)
    print(f"wrote fig_n_badshare.png (n={len(share)} of {len(recs)})")


# ------------------------------------------------------ Appendix N, panel (b)
def fig_n_arigain():
    d = json.loads((DATA / "p1a_segmentation_compare.json").read_text(encoding="utf-8"))
    per = d["ari"]["per_record"]
    recs = sorted(per, key=lambda x: int(x))
    vals = [100 * per[r] for r in recs]
    fig, ax = plt.subplots(figsize=(3.45, 2.5), dpi=400)
    colors = [GREEN if v >= 0 else RED for v in vals]
    bars = ax.bar([f"R{r}" for r in recs], vals, color=colors, width=0.62,
                  edgecolor="white", linewidth=0.4)
    for b, v in zip(bars, vals):
        ax.annotate(f"{v:+.1f}", (b.get_x() + b.get_width() / 2, v),
                    ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=6.6, xytext=(0, 1.5 if v >= 0 else -1.5),
                    textcoords="offset points")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_ylabel("ARI gain over Ward (points)", fontsize=8.0)
    ax.set_xlabel("held-out recording", fontsize=8.0)
    ax.tick_params(axis="x", labelsize=6.8, rotation=0)
    ax.set_ylim(min(-4, min(vals) - 2), max(vals) + 3)
    _clean(ax)
    fig.tight_layout()
    fig.savefig(FIG / "fig_n_arigain.png")
    plt.close(fig)
    print("wrote fig_n_arigain.png")


# ---------------------------------------------------------------- Figure 10
def fig_value_ladder():
    # numbers come from data/value_ladder.json, itself written by make_value_figure.py
    out = json.loads((DATA / "value_ladder.json").read_text(encoding="utf-8"))
    labels = ["scheduling rule", "true duration", "paid observation", "extra reservation"]
    colors = ["#2b6cb0", "#2f855a", "#b7791f", "#c53030"]
    x = np.arange(len(labels))
    w = 0.34
    fig, ax = plt.subplots(figsize=(6.9, 3.55), dpi=400)
    for i, case in enumerate(("S2", "S3")):
        vals = [out["cases"][case][k] for k in labels]
        bars = ax.bar(x + (i - 0.5) * w, vals, w, label=f"Case {case}",
                      color=colors, alpha=0.95 if i == 0 else 0.50,
                      edgecolor="white", linewidth=0.6)
        for b, v in zip(bars, vals):
            ax.annotate(f"{v:+.1f}", (b.get_x() + b.get_width() / 2, v),
                        ha="center", va="bottom" if v >= 0 else "top",
                        fontsize=8.0, xytext=(0, 2.5 if v >= 0 else -2.5),
                        textcoords="offset points")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(["scheduling\nrule", "true\nduration", "paid\nobservation",
                        "extra\nreservation"], fontsize=8.6)
    ax.set_ylabel("weighted on-time points", fontsize=9.0)
    ax.set_ylim(-14.5, 30)
    ax.legend(frameon=False, fontsize=8.0, loc="upper center", ncol=2,
              bbox_to_anchor=(0.5, 1.06))
    _clean(ax)
    ax.tick_params(axis="y", labelsize=8.2)
    fig.tight_layout()
    fig.savefig(FIG / "fig10_value_ladder.png")
    plt.close(fig)
    print("wrote fig10_value_ladder.png")


if __name__ == "__main__":
    fig_bad_ratio()
    fig_n_badshare()
    fig_n_arigain()
    fig_value_ladder()
