# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""make_video_figure.py -- two-panel bar chart for the video branch (Appendix L)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
FIG = os.path.abspath(os.path.join(HERE, "..", "figures"))

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 8.4, "axes.labelsize": 8.6,
    "xtick.labelsize": 7.8, "ytick.labelsize": 7.8, "legend.fontsize": 7.4,
})

d = json.load(open(os.path.join(DATA, "up3_video_badframe.json"), encoding="utf-8"))
labels = ["Pose only", "Video only", "Pose + video"]
keys = ["P", "Vsel", "P+Vsel"]
ap = [d["arms"][k]["test_ap"] for k in keys]
auc = [d["arms"][k]["test_auc"] for k in keys]
colors = ["#6b8e9e", "#c58b5a", "#4a7a5c"]

fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.7), dpi=400)
for ax, vals, title, fmt in ((axes[0], ap, "Average precision", "{:.4f}"),
                             (axes[1], auc, "ROC AUC", "{:.4f}")):
    bars = ax.bar(range(3), vals, color=colors, width=0.62, edgecolor="none")
    ax.set_xticks(range(3)); ax.set_xticklabels(labels)
    ax.set_title(title, fontsize=9.0, pad=4)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#dddddd", lw=0.5)
    ax.set_axisbelow(True)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.008, fmt.format(v),
                ha="center", va="bottom", fontsize=6.9)
    ax.set_ylim(0, max(vals) * 1.13)
fig.tight_layout(w_pad=2.2)
os.makedirs(FIG, exist_ok=True)
out = os.path.join(FIG, "fig11_video_gain.png")
fig.savefig(out, bbox_inches="tight", facecolor="white")
print("wrote", out, os.path.getsize(out))
