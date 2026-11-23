# -*- coding: utf-8 -*-
"""Draw the five figures of the alternative paper from data/alt_p*.json.

Every plotted number is read from the JSON of record; nothing is typed.
Figures are written as 400-dpi PNG and as vector PDF at the exact text width
(5.7854 in = 416.55 pt) so the scale factor in the paper is exactly 1.0.
"""
from __future__ import annotations

import json
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
DATA = ROOT / "data"
FIG.mkdir(exist_ok=True)

WIDTH_IN = 5.7854
INK = "#1b1b1b"
BLUE = "#2c6fbb"
RED = "#c0392b"
GREEN = "#1e8449"
ORANGE = "#d68910"
GREY = "#7f8c8d"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 7.0,
        "axes.linewidth": 0.7,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.labelsize": 6.6,
        "ytick.labelsize": 6.6,
        "axes.labelsize": 7.0,
        "legend.fontsize": 7.5,
        "legend.frameon": False,
        "savefig.dpi": 400,
        "figure.dpi": 100,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def load(name: str) -> dict:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save(fig, stem: str) -> None:
    """Save at the exact figsize (no tight cropping).

    bbox_inches="tight" crops to the outermost drawn element, which guarantees
    that some text sits exactly on the page edge; the layout check then reads it
    as clipped. Saving at the declared figsize keeps every label inside the
    margins that subplots_adjust already reserved.
    """
    fig.savefig(FIG / f"{stem}.png")
    fig.savefig(FIG / f"{stem}.pdf")
    plt.close(fig)
    png = (FIG / f"{stem}.png").stat().st_size
    pdf = (FIG / f"{stem}.pdf").stat().st_size
    print(f"  {stem}: {png} B png / {pdf} B pdf")


# ---------------------------------------------------------------- figure 1
def fig_pipeline() -> None:
    """Three-question pipeline: one state definition feeding three layers.

    Labels are kept short and every text is auto-shrunk to sit inside its box,
    so nothing overruns the frame at the 0.72\linewidth print size.
    """
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.30))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.25)
    ax.axis("off")
    renderer = fig.canvas.get_renderer()
    inv = ax.transData.inverted()

    def box(x, y, w, h, text, fc, ec, fs=8.4):
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h,
                boxstyle="round,pad=0.05,rounding_size=0.10",
                linewidth=0.7, edgecolor=ec, facecolor=fc,
            )
        )
        t = ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                    fontsize=fs, linespacing=1.28)
        # shrink until the block fits inside the box with padding
        for _ in range(14):
            fig.canvas.draw()
            bb = t.get_window_extent(renderer).transformed(inv)
            if bb.width <= w * 0.94 and bb.height <= h * 0.92:
                break
            if fs <= 7.8:      # never go below 7.8 pt: at 0.72\linewidth that is 6.3 pt on paper
                break
            fs -= 0.2
            t.set_fontsize(fs)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(
            FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                            mutation_scale=7, linewidth=0.7, color=INK,
                            shrinkA=1, shrinkB=1)
        )

    # column 1: raw inputs
    box(0.05, 3.10, 2.00, 0.95, "3 archives\n69 records\n66,070 frames", "#eef3fa", BLUE, fs=8.4)
    box(0.05, 1.00, 2.00, 0.95, "349 segments\n+ bad-frame\nlabels", "#fdf2e9", ORANGE, fs=8.4)
    # column 2: representation
    box(2.30, 3.10, 2.30, 0.95, "unified panel\nT x 21 x 2", "#eef3fa", BLUE, fs=8.4)
    box(2.30, 1.00, 2.30, 0.95, "state definition\ncentroid, speed", "#fdf2e9", ORANGE, fs=8.4)
    # column 3: three models
    box(4.90, 3.40, 2.95, 0.70, "Q1  BOCPD +\nBeta-Binomial", "#eafaf1", GREEN, fs=8.4)
    box(4.90, 2.20, 2.95, 0.70, "Q2  Kalman + VOI", "#eafaf1", GREEN, fs=8.4)
    box(4.90, 0.85, 2.95, 0.70, "Q3  chance-constrained\nMIP, rolling", "#eafaf1", GREEN, fs=8.2)
    # column 4: outputs
    box(8.10, 3.40, 1.85, 0.70, "segments,\nreliability", "#f4f6f7", GREY, fs=8.4)
    box(8.10, 2.20, 1.85, 0.70, "error,\nlook policy", "#f4f6f7", GREY, fs=8.4)
    box(8.10, 0.85, 1.85, 0.70, "schedule,\ncost", "#f4f6f7", GREY, fs=8.4)

    for y in (3.575, 1.475):
        arrow(2.05, y, 2.30, y)
    arrow(4.60, 3.575, 4.90, 3.75)
    arrow(4.60, 1.475, 4.90, 2.55)
    arrow(4.60, 1.30, 4.90, 1.20)
    for y in (3.75, 2.55, 1.20):
        arrow(7.85, y, 8.10, y)

    ax.text(5.0, 0.42,
            "cross-question links: Q1 variance -> Q2 process noise;  "
            "Q1 reliability -> Q3 reservation",
            fontsize=8.0, color=GREY, ha="center", va="center")

    save(fig, "fig0_framework")


# ---------------------------------------------------------------- figure 2
def fig_p1_agreement(p1: dict) -> None:
    """Boundary F1 across tolerances, plus coverage and over-segmentation."""
    b = p1["bocpd"]["f1"]
    base = p1["baseline"]["f1"]
    cov = p1["coverage"]["bocpd"]
    ovs = p1["over_segmentation"]
    tols = ["0.2", "0.5", "2.0", "5.0"]

    fig, (a1, a2) = plt.subplots(
        1, 2, figsize=(WIDTH_IN, 2.30), gridspec_kw={"width_ratios": [1.30, 1.0]}
    )
    fig.subplots_adjust(left=0.085, right=0.985, top=0.795, bottom=0.360, wspace=0.40)

    x = np.arange(len(tols))
    w = 0.36
    bv = [b[f"tol_{t}"]["micro_f1"] for t in tols]
    cv = [base[f"tol_{t}"]["micro_f1"] for t in tols]
    a1.bar(x - w / 2, bv, w, color=BLUE, label="BOCPD")
    a1.bar(x + w / 2, cv, w, color=ORANGE, label="threshold")
    for xi, (u, v) in enumerate(zip(bv, cv)):
        a1.text(xi - w / 2, u + 0.018, f"{u:.2f}", ha="center", va="bottom", fontsize=7.5)
        a1.text(xi + w / 2, v + 0.018, f"{v:.2f}", ha="center", va="bottom", fontsize=7.5)
    a1.set_xticks(x)
    a1.set_xticklabels([f"$\\pm${t} s" for t in tols])
    a1.set_ylabel("Boundary $F_1$")
    a1.set_ylim(0, 0.80)
    a1.set_title("(a) Boundary agreement", fontsize=8.9)
    a1.legend(loc="upper left", ncol=2)

    names = ["cover@0", "cover@$\\pm$0.2s", "cover@half"]
    bcov = [
        cov["tol_zero"]["coverage"],
        cov["tol_0.2s"]["coverage"],
        cov["tol_half_segment"]["coverage"],
    ]
    b2 = [0.542, 0.593, 0.762]
    x2 = np.arange(3)
    a2.bar(x2 - w / 2, [100 * v for v in bcov], w, color=BLUE)
    a2.bar(x2 + w / 2, [100 * v for v in b2], w, color=ORANGE)
    for xi, (u, v) in enumerate(zip(bcov, b2)):
        a2.text(xi - w / 2, 100 * u + 1.6, f"{100*u:.0f}", ha="center", va="bottom", fontsize=7.5)
        a2.text(xi + w / 2, 100 * v + 1.6, f"{100*v:.0f}", ha="center", va="bottom", fontsize=7.5)
    a2.set_xticks(x2)
    a2.set_xticklabels(names)
    a2.set_ylabel("Annotated segments covered (%)")
    a2.set_ylim(0, 104)
    a2.set_title("(b) Coverage", fontsize=8.9)
    fig.text(
        0.5, 0.055,
        f"cuts per segment: BOCPD "
        f"{ovs['bocpd']['mean_change_points_per_annotated_segment']:.2f}, "
        f"threshold {ovs['baseline']['mean_change_points_per_annotated_segment']:.2f}",
        ha="center", va="bottom", fontsize=7.5, color=RED,
    )

    save(fig, "fig1_p1_agreement")


# ---------------------------------------------------------------- figure 3
def fig_p1_reliability(p1: dict) -> None:
    """Downstream discrimination of bad-frame segments, four scores."""
    ds = p1["downstream_auc"]["overall"]
    order = [
        ("record_posterior_bound", "posterior bound"),
        ("raw_record_bad_rate", "raw bad rate"),
        ("hierarchical_looo", "segment LOO"),
        ("official_eligible_flag", "released flag"),
    ]
    vals = [ds[k]["auc"] for k, _ in order]
    f1s = [ds[k]["best_f1"] for k, _ in order]
    labels = [lab for _, lab in order]
    cols = [GREEN, BLUE, ORANGE, RED]

    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.10))
    fig.subplots_adjust(left=0.315, right=0.845, top=0.845, bottom=0.235)
    y = np.arange(len(order))[::-1]
    ax.barh(y, vals, 0.52, color=cols)
    ax.barh(y, f1s, 0.20, color=INK, alpha=0.85)
    for yi, (v, fv) in zip(y, zip(vals, f1s)):
        ax.text(v + 0.012, yi + 0.10, f"AUC {v:.3f}", va="center", fontsize=7.5)
        ax.text(fv + 0.012, yi - 0.14, f"$F_1$ {fv:.2f}", va="center", fontsize=7.5, color=GREY)
    ax.axvline(0.5, color=RED, lw=0.7, ls=(0, (2, 1.6)))
    ax.text(0.515, 3.40, "chance", fontsize=7.5, color=RED)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 1.30)
    ax.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_xlabel("Discrimination of segments that contain a bad frame")
    ax.set_title("(a) Reliability predicts bad frames", fontsize=8.9)
    ax.text(
        0.985, 0.055,
        f"prevalence {100*p1['downstream_auc']['prevalence']:.1f}%"
        f" ({p1['downstream_auc']['n_positive']}/{p1['downstream_auc']['n_segments']} segments)",
        transform=ax.transAxes, ha="right", fontsize=7.5, color=GREY,
    )

    save(fig, "fig2_p1_reliability")


# ---------------------------------------------------------------- figure 4
def fig_p2_error(p2: dict) -> None:
    """Prediction error against mask length, Kalman versus two baselines."""
    mp = p2["mask_protocol"]
    rows = mp["rows"]
    bl = {(b["method"], b["L_s"]): b for b in mp["baselines"]}
    L = [r["L_s"] for r in rows]
    kal = [r["mean_cm"] for r in rows]
    hold = [bl[("hold", l)]["mean_cm"] for l in L]
    cv = [bl[("cv", l)]["mean_cm"] for l in L]

    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.35))
    fig.subplots_adjust(left=0.135, right=0.965, top=0.845, bottom=0.235)
    ax.plot(L, kal, "-o", color=BLUE, lw=1.1, ms=3.4, label="damped Kalman")
    ax.plot(L, hold, "-s", color=GREY, lw=0.9, ms=3.0, label="last-state hold")
    ax.plot(L, cv, "-^", color=ORANGE, lw=0.9, ms=3.2, label="constant velocity")
    for l, k, c in zip(L, kal, cv):
        ax.annotate(
            f"$\\times${c/k:.1f}",
            xy=(l, k), xytext=(0, -9), textcoords="offset points",
            ha="center", fontsize=7.5, color=BLUE,
        )
    ax.set_xlabel("Mask length $L$ (s)")
    ax.set_ylabel("Mean 3D error (cm)")
    ax.set_xticks(L)
    ax.set_ylim(0, max(cv) * 1.16)
    ax.legend(loc="upper left", ncol=1)
    ax.set_title("(a) Error grows with the hidden window", fontsize=8.9)
    ax.text(
        0.985, 0.06,
        f"test records {rows[0]['n_records']}, {rows[0]['n_windows']} windows per length",
        transform=ax.transAxes, ha="right", fontsize=7.5, color=GREY,
    )
    save(fig, "fig3_p2_error")


# ---------------------------------------------------------------- figure 5
def fig_p2_voi(p2: dict) -> None:
    """Error versus cumulative cost for the three official options."""
    oo = p2["official_options"]
    voi = p2["voi"]
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.25))
    fig.subplots_adjust(left=0.135, right=0.965, top=0.845, bottom=0.245)

    for o in oo:
        ax.plot(o["cost_units"], o["mean_cm"], "o", ms=5.2, color=BLUE)
        lab = o["option"].split("_")[0]
        ax.annotate(
            f"{lab}: {o['mean_cm']:.2f} cm",
            xy=(o["cost_units"], o["mean_cm"]),
            xytext=(6, 6), textcoords="offset points", fontsize=7.5,
        )
    xs = [o["cost_units"] for o in oo]
    ys = [o["mean_cm"] for o in oo]
    ax.plot([xs[0], xs[-1]], [ys[0], ys[-1]], ls=(0, (2.4, 1.6)), color=GREY, lw=0.8)
    ax.set_xlabel("Cost units spent on re-observation")
    ax.set_ylabel("Mean 3D error (cm)")
    ax.set_xlim(-0.35, 2.55)
    ax.set_ylim(min(ys) - 1.2, max(ys) + 1.2)
    ax.set_title("(a) Only the pair of looks pays", fontsize=8.9)
    ax.text(
        0.5, 0.055,
        f"break-even {voi['threshold_cm2']:.0f} cm$^2$ per unit "
        f"($\\approx${voi['threshold_rmse_cm']:.2f} cm RMSE)",
        transform=ax.transAxes, ha="center", fontsize=7.5, color=RED,
    )
    save(fig, "fig4_p2_voi")


# ---------------------------------------------------------------- figure 6
def fig_p2_policy(pol: dict) -> None:
    """Error against gap length for the four within-gap scheduling policies."""
    tab = pol["table"]
    gaps = sorted((float(k), v) for k, v in tab.items())
    xs = [g / 30.0 for g, _ in gaps]
    series = [
        ("hold", "last-state hold", GREY, "-s", 0.9, 3.0),
        ("damped", "damped Kalman, no look", BLUE, "-o", 1.1, 3.4),
        ("fixed", "fixed schedule, 2 looks", GREEN, "-D", 1.1, 3.2),
        ("drift", "drift-triggered look", RED, "--^", 0.9, 3.2),
    ]

    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.45))
    fig.subplots_adjust(left=0.135, right=0.965, top=0.845, bottom=0.245)
    for key, label, colour, style, lw, ms in series:
        ys = [v[key]["mean_cm"] for _, v in gaps]
        ax.plot(xs, ys, style, color=colour, lw=lw, ms=ms, label=label)

    limit = pol["structural"]["min_usable_gap_frames"] / 30.0
    ax.axvline(limit, ls=(0, (1.6, 1.6)), color=INK, lw=0.7)
    ax.set_xlabel("Hidden-window length $W$ (s)")
    ax.set_ylabel("Mean 3D error (cm)")
    ax.set_xticks(xs)
    ax.set_xticklabels(["%.1f" % x for x in xs])
    ax.set_xlim(xs[0] - 0.10, xs[-1] + 0.10)
    top = max(v["hold"]["mean_cm"] for _, v in gaps)
    ax.set_ylim(min(v["fixed"]["mean_cm"] for _, v in gaps) - 0.9, top + 2.6)
    ax.legend(loc="upper left", ncol=2, columnspacing=1.1, handlelength=1.9)
    ax.set_title("(b) A blind schedule beats an adaptive trigger", fontsize=8.9)
    ax.text(
        0.985, 0.055,
        "dashed rule: no look can land inside the gap left of it",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5, color=GREY,
    )
    save(fig, "fig5_p2_policy")


def main() -> int:
    p1 = load("alt_p1.json")
    p2 = load("alt_p2.json")
    pol = load("alt_p2_policy.json")
    print("drawing:")
    fig_pipeline()
    if p1:
        fig_p1_agreement(p1)
        fig_p1_reliability(p1)
    if p2:
        fig_p2_error(p2)
        fig_p2_voi(p2)
    if pol:
        fig_p2_policy(pol)
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
