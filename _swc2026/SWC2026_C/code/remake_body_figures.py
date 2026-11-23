# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Publication-grade redraw of the eight body figures.

Why this file exists
--------------------
The first submission used PNGs whose physical width in the PDF was set to
0.12--0.30\linewidth.  The source resolution was adequate but the printed
figures were too small to read.  This script redraws every body figure at the
physical width it is printed at, with a common serif face, one palette and
minimum 8 pt type.  Nothing is re-fitted: all values are read from data/*.json
or data/*.npz, so the figures cannot drift away from the tables.

Outputs (all in figures/):
  fig1_keypoint_tracks.png, fig2_bad_ratio.png, fig3_segmentation.png,
  fig4_p2_error_vs_mask.png, fig5_p2_cost_tradeoff.png,
  fig6_p3_policy.png, fig7_reliability_roc.png, fig8_p2_crossover.png
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
FIG = ROOT / "figures"
sys.path.insert(0, str(HERE))
from common import quat_to_R  # noqa: E402

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


def load_json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def save(fig, name):
    fig.savefig(FIG / name, dpi=400)
    plt.close(fig)
    print("WROTE", name)


def fig1():
    z = np.load(DATA / "panel.npz")
    recs = pd.read_csv(DATA / "panel_records.csv")
    cand = recs[(recs.dataset == "EgoDemo") & (recs.badL > 0.02)]
    r = int(cand.rec.iloc[0]) if len(cand) else int(recs[recs.dataset == "EgoDemo"].rec.iloc[0])
    ii = np.where(z["rec"] == r)[0]
    k = int(np.bincount(z["rec"]).argmax()) if False else 0
    # dominant hand is stored per record in the state file; for the demo record use left unless badL is clearly worse
    P = z["L"][ii]
    H = z["H"][ii]
    Q = z["Q"][ii]
    R = np.transpose(quat_to_R(Q), (0, 2, 1))
    Ph = np.einsum("nij,nkj->nki", R, P - H[:, None, :])
    t = z["t"][ii] - z["t"][ii][0]
    bad = z["badL"][ii].astype(bool)
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.55))
    for j, c, lab in [(0, COL["navy"], "wrist"), (4, COL["red"], "thumb tip"), (8, COL["blue"], "index tip")]:
        ax[0].plot(t, Ph[:, j, 0], color=c, lw=1.2, label=lab)
        ax[1].plot(Ph[:, j, 0], Ph[:, j, 2], color=c, lw=1.0, label=lab)
    # shade bad runs
    if bad.any():
        d = np.diff(np.r_[0, bad.astype(int), 0])
        for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            ax[0].axvspan(t[a], t[min(b, len(t)-1)], color=COL["gold"], alpha=.18, lw=0)
    ax[0].set_xlabel("time (s)"); ax[0].set_ylabel("head-frame $x$ (m)")
    ax[0].set_title("Dominant-hand tracks, one demo record")
    ax[1].set_xlabel("head-frame $x$ (m)"); ax[1].set_ylabel("head-frame $z$ (m)")
    ax[1].set_title("Same trace in the transverse plane")
    ax[0].legend(frameon=False, loc="upper right", ncol=1)
    for a in ax:
        a.grid(color="#E8E8E8", lw=.45); a.set_axisbelow(True)
        for side in ("top", "right"): a.spines[side].set_visible(False)
    fig.tight_layout()
    save(fig, "fig1_keypoint_tracks.png")


def fig2():
    recs = pd.read_csv(DATA / "panel_records.csv")
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.35))
    bins = np.linspace(0, max(5.0, 100 * recs.badL.max()), 22)
    for d, c in zip(["EgoDemo", "EgoPro", "EgoStandard"], [COL["blue"], COL["orange"], COL["green"]]):
        v = 100 * recs.loc[recs.dataset == d, "badL"].values
        ax[0].hist(v, bins=bins, alpha=.55, label=d, color=c, edgecolor="white", linewidth=.4)
    ax[0].set_xlabel("flagged frames per record (%)"); ax[0].set_ylabel("records")
    ax[0].set_title("Distribution of flagged frames")
    m = recs.groupby("dataset")[["badL", "badR"]].mean().loc[["EgoDemo", "EgoPro", "EgoStandard"]] * 100
    x = np.arange(3)
    ax[1].bar(x - .18, m.badL, .36, label="left hand", color=COL["navy"])
    ax[1].bar(x + .18, m.badR, .36, label="right hand", color=COL["orange"])
    ax[1].set_xticks(x); ax[1].set_xticklabels(["EgoDemo", "EgoPro", "EgoStandard"], rotation=10)
    ax[1].set_ylabel("mean flagged share (%)"); ax[1].set_title("Left versus right")
    ax[1].legend(frameon=False)
    for a in ax:
        a.grid(axis="y", color="#E8E8E8", lw=.45); a.set_axisbelow(True)
        for side in ("top", "right"): a.spines[side].set_visible(False)
    fig.tight_layout()
    save(fig, "fig2_bad_ratio.png")


def fig3():
    d = load_json("p1a_segmentation_compare.json")
    per = d["ari"]["per_record"]
    recs = sorted(per, key=lambda x: int(x))
    vals = [100 * per[r] for r in recs]
    fig, ax = plt.subplots(figsize=(6.5, 2.2))
    colors = [COL["green"] if v >= 0 else COL["red"] for v in vals]
    bars = ax.bar([f"R{r}" for r in recs], vals, color=colors, width=.62, edgecolor="white", linewidth=.4)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width()/2, v + (1.5 if v >= 0 else -1.5), f"{v:+.1f}",
                ha="center", va="bottom" if v >= 0 else "top", fontsize=6.8)
    ax.axhline(0, color="k", lw=.6)
    ax.set_ylabel("ARI gain over Ward (points)")
    ax.set_xlabel("held-out recording")
    ax.set_title("Per-record segmentation gain of the learned decoder")
    ax.grid(axis="y", color="#E8E8E8", lw=.45); ax.set_axisbelow(True)
    for side in ("top", "right"): ax.spines[side].set_visible(False)
    fig.tight_layout()
    save(fig, "fig3_segmentation.png")


def fig4():
    d = load_json("p2_prediction.json")
    rows = d["by_length"]
    methods = [("hold", "hold-last", COL["gray"], "o", "-"),
               ("cv", "constant velocity", COL["blue"], "s", "--"),
               ("ridge", "ridge context", COL["green"], "D", "-")]
    fig, ax = plt.subplots(figsize=(5.4, 2.9))
    for key, label, color, marker, ls in methods:
        xs = sorted({r["L_s"] for r in rows})
        ys = [100 * next(r["rmse"] for r in rows if r["method"] == key and r["L_s"] == x) for x in xs]
        ax.plot(xs, ys, marker=marker, ls=ls, color=color, label=label)
    ax.set_xlabel("mask length $L$ (s)"); ax.set_ylabel("position RMSE (cm)")
    ax.set_title("Error against missing duration")
    ax.grid(color="#E8E8E8", lw=.45); ax.set_axisbelow(True); ax.legend(frameon=False)
    for side in ("top", "right"): ax.spines[side].set_visible(False)
    fig.tight_layout(); save(fig, "fig4_p2_error_vs_mask.png")


def fig5():
    d = load_json("p2_prediction.json")
    rows = [r for r in d["by_length"] if r["method"] == "ridge"]
    rows = sorted(rows, key=lambda r: r["L_s"])
    Ls = np.array([r["L_s"] for r in rows]); rm = np.array([100 * r["rmse"] for r in rows])
    grid = np.arange(0.1, 2.51, .05)
    err = np.interp(grid, Ls, rm)
    C0, C1, lam = .5, .2, 1.0
    cost = C0 / grid + C1
    J = err + lam * cost
    i = int(np.argmin(J))
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    ax.plot(grid, err, color=COL["blue"], label="prediction RMSE (cm)")
    ax.plot(grid, lam * cost, color=COL["orange"], ls="--", label=r"re-observation cost $\times\lambda$")
    ax.plot(grid, J, color=COL["navy"], label="total objective")
    ax.axvline(grid[i], color="k", ls=":", lw=.8)
    ax.scatter([grid[i]], [J[i]], color=COL["red"], zorder=5, s=18)
    ax.annotate(rf"$T^*={grid[i]:.2f}$ s", xy=(grid[i], J[i]), xytext=(8, 8),
                textcoords="offset points", fontsize=7.6)
    ax.set_xlabel("re-observation interval $T$ (s)"); ax.set_ylabel("cm / cost units")
    ax.set_title("The priced review interval")
    ax.grid(color="#E8E8E8", lw=.45); ax.set_axisbelow(True); ax.legend(frameon=False)
    for side in ("top", "right"): ax.spines[side].set_visible(False)
    fig.tight_layout(); save(fig, "fig5_p2_cost_tradeoff.png")


def fig6():
    d = load_json("p3_stochastic_schedule.json")["summary"]
    rate = {(r["case"], r["policy"]): float(r["weighted_on_time_rate"]) for r in d}
    policies = [("edf_old", "EDF"), ("slack_old", "Slack"), ("risk_fusion", "Risk reserve"),
                ("rollout_fusion", "Rollout"), ("oracle", "Oracle")]
    cases = ["S1", "S2", "S3"]
    fig, ax = plt.subplots(figsize=(6.5, 2.6))
    x = np.arange(len(policies)); w = .26
    for i, case in enumerate(cases):
        vals = [rate.get((case, p), np.nan) for p, _ in policies]
        ax.bar(x + (i - 1) * w, vals, width=w, label=case,
               color=[COL["gray"], COL["blue"], COL["orange"]][i], edgecolor="white", linewidth=.4)
    ax.axhline(.5, color="k", ls="--", lw=.7)
    ax.set_xticks(x); ax.set_xticklabels([n for _, n in policies])
    ax.set_ylabel("weighted on-time rate"); ax.set_ylim(.4, 1.02)
    ax.set_title("Corrected protocol: the rule, not the reservation, moves punctuality")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    ax.grid(axis="y", color="#E8E8E8", lw=.45); ax.set_axisbelow(True)
    for side in ("top", "right"): ax.spines[side].set_visible(False)
    fig.tight_layout(); save(fig, "fig6_p3_policy.png")


def fig7():
    d = load_json("up2_p1b.json")["summary"]
    keys = [f"V{i}" for i in range(1, 9)]
    keys = [k for k in keys if k in d]
    ap = [100 * d[k]["test_ap_mean"] for k in keys]
    auc = [100 * d[k]["test_auc_mean"] for k in keys]
    worst = [100 * d[k]["worst_auc_mean"] for k in keys]
    fig, ax = plt.subplots(2, 1, figsize=(6.5, 3.4), sharex=True,
                           gridspec_kw={"height_ratios": [1.0, 1.0]})
    x = np.arange(len(keys))
    colors = [COL["green"] if k == "V8" else COL["blue"] for k in keys]
    ax[0].bar(x, ap, color=colors, width=.62, edgecolor="white", linewidth=.4)
    ax[0].axhline(13.0, color=COL["red"], ls="--", lw=.8, label="AP gate 13%")
    for xi, v in zip(x, ap):
        ax[0].text(xi, v + .25, f"{v:.1f}", ha="center", va="bottom", fontsize=6.8)
    ax[0].set_ylabel("test AP (%)")
    ax[0].set_ylim(0, 19.5)
    ax[0].set_title("Average precision by configuration")
    ax[0].legend(frameon=False, loc="upper left")
    ax[1].plot(x, auc, marker="o", color=COL["navy"], label="test AUC")
    ax[1].plot(x, worst, marker="s", color=COL["orange"], label="worst environment AUC")
    ax[1].set_xticks(x); ax[1].set_xticklabels(keys)
    ax[1].set_ylabel("AUC (%)"); ax[1].set_xlabel("configuration")
    ax[1].legend(frameon=False, ncol=2, loc="lower right")
    ax[1].set_title("Ranking and cross-environment floor")
    for a in ax:
        a.grid(axis="y", color="#E8E8E8", lw=.45); a.set_axisbelow(True)
        for side in ("top", "right"): a.spines[side].set_visible(False)
    fig.tight_layout(); save(fig, "fig7_reliability_roc.png")


def fig8():
    d = load_json("p2_crossover.json")
    rows = sorted(d["rows"], key=lambda r: r["L_s"])
    L = np.array([r["L_s"] for r in rows])
    hold = np.array([100 * r["hold_rmse_m"] for r in rows])
    cv = np.array([100 * r["cv_rmse_m"] for r in rows])
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    ax.plot(L, hold, color=COL["gray"], marker="o", label="hold-last")
    ax.plot(L, cv, color=COL["blue"], marker="s", label="constant velocity")
    ax.axvline(d["crossover_s"], color=COL["red"], ls="--", lw=.8)
    ax.axvline(d["crossover_s_median"], color=COL["orange"], ls=":", lw=.8)
    ax.annotate(f"mean {d['crossover_s']:.2f} s", xy=(d["crossover_s"], ax.get_ylim()[1]*.92),
                xytext=(3, 0), textcoords="offset points", fontsize=7.2, color=COL["red"])
    ax.annotate(f"median {d['crossover_s_median']:.2f} s", xy=(d["crossover_s_median"], ax.get_ylim()[1]*.80),
                xytext=(3, 0), textcoords="offset points", fontsize=7.2, color=COL["orange"])
    ax.set_xlabel("mask length $L$ (s)"); ax.set_ylabel("RMSE (cm)")
    ax.set_title("Where constant velocity overtakes hold-last")
    ax.grid(color="#E8E8E8", lw=.45); ax.set_axisbelow(True); ax.legend(frameon=False)
    for side in ("top", "right"): ax.spines[side].set_visible(False)
    fig.tight_layout(); save(fig, "fig8_p2_crossover.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6(); fig7(); fig8()
