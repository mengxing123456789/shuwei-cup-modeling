
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Missing audit figures for the SWC2026 C paper.

Generates four PDF-only figures from data/*.json and data/p1b_probs.npz:
  fig9_p1a_per_record_ari.pdf
  fig10_p2_mask_error.pdf
  fig11_p3_policy_on_time.pdf
  fig12_calibration_reliability.pdf

Design contract:
  * vector PDF (font type 42), no PNG output;
  * physical width 3.905 in = 281.2 pt = 0.62\\linewidth in the compiled A4 paper;
  * every text element >= 6.4 pt at that width;
  * never overwrite an existing figure.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FIGS = ROOT / "figures"
WIDTH_IN = 281.2 / 72.0  # observed width of \\slotFigWSmall in main.pdf

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 6.5,
        "axes.titlesize": 7.2,
        "axes.labelsize": 6.8,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "legend.fontsize": 6.3,
        "figure.titlesize": 7.3,
        "axes.linewidth": 0.55,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "xtick.major.size": 2.2,
        "ytick.major.size": 2.2,
        "lines.linewidth": 1.05,
        "lines.markersize": 2.7,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    }
)

COL = {
    "navy": "#23445D",
    "blue": "#2E6F9E",
    "cyan": "#4B9BB5",
    "orange": "#D9822B",
    "red": "#A63D40",
    "green": "#4F7942",
    "purple": "#6B5B95",
    "gray": "#7A7A7A",
    "lightgray": "#C9C9C9",
}


def load_json(name: str):
    with (DATA / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def out_path(name: str) -> Path:
    path = FIGS / name
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing figure: {path}")
    return path


def save_pdf(fig, name: str) -> Path:
    path = out_path(name)
    fig.savefig(path, format="pdf", dpi=600)
    plt.close(fig)
    return path


def fig9_p1a_per_record_ari() -> Path:
    sweep = load_json("best_p1a_ksweep.json")["bic"]
    caps = ["8", "16", "25"]
    colors = [COL["gray"], COL["blue"], COL["orange"]]

    recs = [str(r["rec"]) for r in sweep[caps[0]]["records"]]
    values = {cap: [float(r["ari"]) for r in sweep[cap]["records"]] for cap in caps}
    means = {cap: float(sweep[cap]["mean"]["ari"]) for cap in caps}

    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.95), constrained_layout=True)
    x = np.arange(len(recs))
    total_width = 0.78
    bar_width = total_width / len(caps)
    for i, cap in enumerate(caps):
        offset = (i - (len(caps) - 1) / 2.0) * bar_width
        ax.bar(
            x + offset,
            values[cap],
            width=bar_width * 0.92,
            color=colors[i],
            edgecolor="white",
            linewidth=0.35,
            label=f"cap {cap}  (mean {means[cap]:.3f})",
        )

    ax.set_xticks(x)
    ax.set_xticklabels([f"R{rec}" for rec in recs])
    ax.set_ylim(0.0, 0.88)
    ax.set_yticks(np.arange(0.0, 0.81, 0.2))
    ax.set_xlabel("Held-out test recording")
    ax.set_ylabel("ARI versus annotated segments")
    ax.set_title("Per-record segmentation agreement at three segment caps")
    ax.grid(axis="y", color="#E4E4E4", linewidth=0.45)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", ncol=1, frameon=False, handlelength=1.1)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return save_pdf(fig, "fig9_p1a_per_record_ari.pdf")


def fig10_p2_mask_error() -> Path:
    d = load_json("p2_masked.json")
    ks = [int(k) for k in d["_meta"]["KS_EVAL"]]
    arms = [
        ("clean_only", "Clean reference", COL["gray"], "o", "-"),
        ("locf_mask", "LOCF fill", COL["orange"], "s", "--"),
        ("interp_mask", "Linear interp.", COL["blue"], "^", "-."),
    ]

    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.35), constrained_layout=True)
    x = np.arange(len(ks))
    for key, label, color, marker, ls in arms:
        vals = np.asarray(
            [d["arms"][key]["mask"][str(k)]["rmse"] for k in ks], dtype=float
        )
        ax.plot(
            x,
            vals,
            color=color,
            marker=marker,
            linestyle=ls,
            label=f"{label}: {vals[0]:.2f} to {vals[-1]:.2f} cm",
        )
        ax.annotate(
            f"{vals[-1]:.2f}",
            xy=(x[-1], vals[-1]),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=6.3,
            color=color,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([str(k) for k in ks])
    ax.set_xlim(-0.18, len(ks) - 0.52)
    lo = min(
        float(d["arms"][a]["mask"][str(k)]["rmse"]) for a, *_ in arms for k in ks
    )
    hi = max(
        float(d["arms"][a]["mask"][str(k)]["rmse"]) for a, *_ in arms for k in ks
    )
    pad = max(0.025, 0.18 * (hi - lo))
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlabel("Masked frames $k$ within the 30-frame horizon")
    ax.set_ylabel("Position RMSE (cm)")
    ax.set_title("Error grows slowly with missing-label mask length")
    ax.grid(axis="y", color="#E4E4E4", linewidth=0.45)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, handlelength=1.7)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return save_pdf(fig, "fig10_p2_mask_error.pdf")


def fig11_p3_policy_on_time() -> Path:
    rows = load_json("p3_stochastic_schedule.json")["summary"]
    rate = {(r["case"], r["policy"]): float(r["weighted_on_time_rate"]) for r in rows}

    policies = [
        ("edf_old", "EDF (old)"),
        ("edf_fusion", "EDF (fusion)"),
        ("slack_old", "Slack (old)"),
        ("slack_fusion", "Slack (fusion)"),
        ("risk_fusion", "Risk reserve"),
        ("rollout_fusion", "Rollout MPC"),
        ("oracle", "Oracle"),
    ]
    colors = [
        COL["gray"],
        COL["cyan"],
        COL["orange"],
        COL["red"],
        COL["purple"],
        COL["green"],
        COL["navy"],
    ]
    cases = [("S1", "S1: loose capacity"), ("S2", "S2: medium"), ("S3", "S3: tight")]

    fig, axes = plt.subplots(
        3, 1, figsize=(WIDTH_IN, 4.25), sharex=True, constrained_layout=True
    )
    ypos = np.arange(len(policies))
    for ax, (case, title), in zip(axes, cases):
        vals = [rate[(case, p)] for p, _ in policies]
        ax.barh(
            ypos,
            vals,
            color=colors,
            height=0.72,
            edgecolor="white",
            linewidth=0.35,
        )
        for y, value in zip(ypos, vals):
            ax.text(
                value + 0.006,
                y,
                f"{value:.3f}",
                va="center",
                ha="left",
                fontsize=6.3,
                color="#222222",
            )
        ax.set_yticks(ypos)
        ax.set_yticklabels([name for _, name in policies])
        ax.invert_yaxis()
        ax.set_xlim(0.48, 1.045)
        ax.set_xticks(np.arange(0.5, 1.01, 0.1))
        ax.set_title(title, loc="left", pad=1.5)
        ax.grid(axis="x", color="#E4E4E4", linewidth=0.45)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    axes[-1].set_xlabel("Weighted on-time rate (higher is better)")
    fig.suptitle("Corrected stochastic schedule: policy comparison", y=1.01)
    return save_pdf(fig, "fig11_p3_policy_on_time.pdf")


def _reliability(p: np.ndarray, y: np.ndarray, edges: np.ndarray):
    """Reliability coordinates with a fixed set of explicit bin edges."""
    xs, ys, ns = [], [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        if hi >= 1.0:
            m = (p >= lo) & (p <= hi)
        else:
            m = (p >= lo) & (p < hi)
        if m.any():
            xs.append(float(p[m].mean()))
            ys.append(float(y[m].mean()))
            ns.append(int(m.sum()))
    return np.asarray(xs), np.asarray(ys), np.asarray(ns)


def _ece(p: np.ndarray, y: np.ndarray, edges: np.ndarray) -> float:
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p <= hi if hi >= 1.0 else p < hi)
        if m.any():
            total += m.mean() * abs(float(p[m].mean() - y[m].mean()))
    return float(total)


def _brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def fig12_calibration_reliability() -> Path:
    z = np.load(DATA / "p1b_probs.npz")
    y = z["yte"].astype(float)
    series = [
        ("Raw", z["pt"].astype(float), COL["gray"], "o", "-"),
        ("Temperature", z["pcal"].astype(float), COL["orange"], "s", "--"),
        ("Platt", z["ppl"].astype(float), COL["blue"], "^", "-."),
    ]
    full_edges = np.linspace(0.0, 1.0, 16)
    zoom_edges = np.linspace(0.0, 0.25, 11)

    fig, axes = plt.subplots(
        1, 2, figsize=(WIDTH_IN, 3.0), constrained_layout=True
    )
    panels = [
        (axes[0], full_edges, "Full range (15 equal-width bins)", (0.0, 1.0), (0.0, 0.62)),
        (axes[1], zoom_edges, "Low-probability zoom (10 bins)", (0.0, 0.25), (0.0, 0.12)),
    ]

    for ax, edges, title, xlim, ylim in panels:
        ax.plot([0, 1], [0, 1], color="#9A9A9A", linewidth=0.6, linestyle=":", label="Perfect")
        ax.axhline(
            float(y.mean()),
            color="#BDBDBD",
            linewidth=0.65,
            linestyle=":",
        )
        for label, p, color, marker, ls in series:
            xs, ys, _ = _reliability(p, y, edges)
            ax.plot(
                xs,
                ys,
                color=color,
                marker=marker,
                linestyle=ls,
                label=label,
                clip_on=True,
            )
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_xlabel("Predicted bad-frame probability")
        ax.set_ylabel("Observed bad-frame frequency")
        ax.set_title(title, loc="left")
        ax.grid(color="#E8E8E8", linewidth=0.45)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    axes[0].text(
        0.98,
        0.04,
        "dotted: base rate 0.019",
        ha="right",
        va="bottom",
        fontsize=6.3,
        color="#666666",
        transform=axes[0].transAxes,
    )

    labels = []
    for name, p, _, _, _ in series:
        labels.append(f"{name}: Brier {_brier(p, y):.3f}, ECE {_ece(p, y, full_edges):.3f}")
    handles = [
        plt.Line2D([], [], color=color, marker=marker, linestyle=ls, label=lab)
        for (name, p, color, marker, ls), lab in zip(series, labels)
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=1,
        frameon=False,
        bbox_to_anchor=(0.5, -0.015),
        handlelength=2.0,
        labelspacing=0.2,
    )
    fig.suptitle("Calibration diagnostics: TCN probabilities on held-out windows", y=1.02)
    return save_pdf(fig, "fig12_calibration_reliability.pdf")


def main() -> None:
    paths = [
        fig9_p1a_per_record_ari(),
        fig10_p2_mask_error(),
        fig11_p3_policy_on_time(),
        fig12_calibration_reliability(),
    ]
    for path in paths:
        print(f"WROTE {path}  {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()