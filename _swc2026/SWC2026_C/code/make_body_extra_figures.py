# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Extra body figures for the presentation pass.

All values are read from data/*.json or data/*.npz; nothing is hand-typed.

Outputs (figures/):
  fig_stage_timeline.png  one record, five stages, speed and aperture
  fig_stage_share.png     stage composition by dataset
  fig_boundary_score.png  learned boundary score against annotated boundaries
  fig_p2_official.png     official mean 3-D distance by lead and predictor
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
FIG = ROOT / "figures"
sys.path.insert(0, str(HERE))
import state_layer as S  # noqa: E402

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 8.2,
    "axes.titlesize": 9.0,
    "axes.labelsize": 8.3,
    "xtick.labelsize": 7.6,
    "ytick.labelsize": 7.6,
    "legend.fontsize": 7.2,
    "axes.linewidth": 0.55,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "xtick.major.size": 2.4,
    "ytick.major.size": 2.4,
    "lines.linewidth": 1.2,
    "lines.markersize": 3.0,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})
COL = {
    "navy": "#1F3B73", "blue": "#2E6F9E", "cyan": "#4B9BB5",
    "orange": "#C56A1A", "red": "#A63D40", "green": "#3F6B3A",
    "gray": "#606060", "light": "#CFCFCF", "gold": "#B58B2A",
}
STAGE_COL = {
    "reach": "#BFD3E6", "pick": "#8FB8D8", "place": "#5E93BE",
    "transport": "#E3B37A", "arrange": "#C56A1A",
}


def load_json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def save(fig, name):
    fig.savefig(FIG / name, dpi=400)
    plt.close(fig)


# ---------------------------------------------------------------- 1 timeline
def stage_timeline():
    rec = 41
    st = S.build_state(rec)
    t = st["t"]
    left = st["L"]
    stage = left["stage"].astype(int)
    names = list(S.STAGES)
    fig, axes = plt.subplots(
        3, 1, figsize=(7.0, 2.95), sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.0, 0.65], "hspace": 0.10})
    ax, ax2, ax3 = axes
    i, n = 0, len(t)
    while i < n:
        j = i
        while j + 1 < n and stage[j + 1] == stage[i]:
            j += 1
        ax.axvspan(t[i], t[j], color=STAGE_COL[names[stage[i]]], alpha=0.32, lw=0)
        i = j + 1
    ax.plot(t, left["speed"], color=COL["navy"], lw=0.9)
    ax.set_ylabel("speed (m/s)", color=COL["navy"])
    ax.tick_params(axis="y", colors=COL["navy"], labelsize=7.0)
    ax.set_ylim(0, float(left["speed"].max()) * 1.03)
    ax2.plot(t, left["aperture"], color=COL["red"], lw=0.9)
    ax2.set_ylabel("aperture", color=COL["red"])
    ax2.tick_params(axis="y", colors=COL["red"], labelsize=7.0)
    ax2.set_ylim(0, float(left["aperture"].max()) * 1.05)
    arr = st["L"]["stage"].astype(int)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and arr[j + 1] == arr[i]:
            j += 1
        ax3.fill_between([t[i], t[j]], 1.0 - 0.20, 1.0 + 0.20,
                         color=STAGE_COL[names[arr[i]]], lw=0)
        i = j + 1
    ax3.set_ylim(0.55, 1.45)
    ax3.set_yticks([1.0])
    ax3.set_yticklabels(["left hand"], fontsize=7.0)
    ax3.set_xlabel("time within record (s)")
    handles = [Patch(facecolor=STAGE_COL[n], label=n) for n in names]
    ax.legend(handles=handles, ncol=5, loc="lower left", bbox_to_anchor=(0.0, 1.02),
              frameon=False, handlelength=1.0, columnspacing=1.0,
              borderaxespad=0.0)
    ax.set_xlim(t[0], t[-1])
    save(fig, "fig_stage_timeline.png")


# --------------------------------------------------------------- 2 share bars
def stage_share():
    d = load_json("state_layer.json")["records"]
    rows = []
    for r in d:
        for k, v in r["stage_share"].items():
            rows.append((r["dataset"], k, v))
    df = pd.DataFrame(rows, columns=["dataset", "stage", "share"])
    order = ["EgoDemo", "EgoPro", "EgoStandard"]
    names = list(S.STAGES)
    piv = df.groupby(["dataset", "stage"])["share"].mean().unstack()[names].loc[order]
    fig, ax = plt.subplots(figsize=(4.55, 2.55))
    bottom = np.zeros(len(piv))
    x = np.arange(len(piv))
    for nm in names:
        ax.bar(x, piv[nm].values, bottom=bottom, color=STAGE_COL[nm],
               width=0.62, label=nm, edgecolor="white", linewidth=0.4)
        bottom += piv[nm].values
    ax.set_xticks(x)
    ax.set_xticklabels(order)
    ax.set_ylabel("share of frames")
    ax.set_ylim(0, 1.02)
    ax.legend(ncol=5, loc="lower left", bbox_to_anchor=(0.0, 1.01), frameon=False,
              handlelength=0.9, columnspacing=0.8, borderaxespad=0.0)
    save(fig, "fig_stage_share.png")


# ------------------------------------------------------------ 3 score example
def boundary_score():
    rec = 41
    z = np.load(DATA / "p1a_gpu_segmentation_probs.npz", allow_pickle=True)
    score = z[f"rec{rec}"].astype(float)
    st = S.build_state(rec)
    t = st["t"]
    if len(score) != len(t):
        t = np.linspace(0, len(score) - 1, len(score))
    seg = pd.read_csv(DATA / "segments.csv")
    seg = seg[seg.rec == rec].sort_values("start")
    fig, ax = plt.subplots(figsize=(7.0, 2.0))
    for k in range(len(seg)):
        if k % 2 == 0:
            ax.axvspan(seg.start.iloc[k], seg.end.iloc[k], color="#F1F1F1", lw=0)
    ax.plot(t, score, color=COL["navy"], lw=0.95)
    for s in list(seg.start.values[1:]) + [seg.end.values[-1]]:
        ax.axvline(s, color=COL["red"], lw=0.65, ls=(0, (3, 2)))
    ax.set_xlabel("time within record (s)")
    ax.set_ylabel("boundary score")
    ax.set_xlim(t[0], t[-1])
    ax.set_ylim(0, float(score.max()) * 1.08)
    save(fig, "fig_boundary_score.png")


# ---------------------------------------------------------- 4 official 3-D R
def p2_official():
    d = load_json("p2_official_distance.json")["by_lead"]
    leads = ["6", "18", "30", "60"]
    labels = ["0.2 s", "0.6 s", "1.0 s", "2.0 s"]
    pol = [("hold", "hold-last", COL["gray"]),
           ("ridge", "ridge", COL["blue"]),
           ("quantile", "quantile GRU", COL["orange"])]
    fig, ax = plt.subplots(figsize=(5.3, 2.45))
    x = np.arange(len(leads))
    w = 0.26
    for k, (key, lab, c) in enumerate(pol):
        vals = [d[l]["test"][key]["mean_R_cm"] for l in leads]
        ax.bar(x + (k - 1) * w, vals, width=w, color=c, label=lab)
        for xi, v in zip(x + (k - 1) * w, vals):
            ax.text(xi, v + 0.08, f"{v:.1f}", ha="center", va="bottom", fontsize=6.6)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("mask length L")
    ax.set_ylabel("mean 3-D distance R (cm)")
    ax.set_ylim(0, max(d[l]["test"][p]["mean_R_cm"] for l in leads for p, _, _ in pol) * 1.28)
    ax.legend(ncol=3, loc="upper left", frameon=False, handlelength=1.0,
              columnspacing=1.1)
    save(fig, "fig_p2_official.png")


if __name__ == "__main__":
    stage_timeline()
    stage_share()
    boundary_score()
    p2_official()
    for nm in ("fig_stage_timeline", "fig_stage_share", "fig_boundary_score",
               "fig_p2_official"):
        p = FIG / f"{nm}.png"
        print(nm, p.stat().st_size)
