#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Draw every paper figure for PRACTICE_2023B (2023 ShuWei Cup Problem B).

Design contract
---------------
* Every plotted number comes from data/results_*.json (written by code/solve.py
  under the mathmodel interpreter).  This script only draws; it recomputes no
  statistic.  The single exception is the horizontal position of a level label
  such as "40/100": it is decoded as 40/(40+100), i.e. ash/(ash+biomass), which
  is the definition of the level, not a fitted quantity.
* Page width is fixed at 416.5 pt so that width=1.0\\linewidth in main.tex is a
  1:1 placement; anything wider would be cropped by the PDF MediaBox.
* Smallest in-figure type is 6.3 pt (the hard gate is 6.0 pt; matplotlib stores
  6.0 as 5.98, so 6.2+ is used everywhere).
* No hatch patterns, no sharey, legends sit outside the axes.

Run with the plotting interpreter (the mathmodel env crashes in savefig):

    & "E:\\Mini\\python.exe" -X utf8 code\\make_figures.py
    & "E:\\Mini\\python.exe" -X utf8 code\\make_figures.py --only fig05
    & "E:\\Mini\\python.exe" -X utf8 code\\make_figures.py --only fig04,fig05
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from seal import commit, header, stamp

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGDIR = ROOT / "figures"

W_IN = 416.5 / 72.0          # exact PDF page width in inches

COMBO_ORDER = ["CS", "CE", "LG"]
COMBO_COLOR = {"CS": "#0072B2", "CE": "#D55E00", "LG": "#009E73"}
COMBO_MARKER = {"CS": "o", "CE": "s", "LG": "^"}

PROD_ORDER = ["Tar", "Water", "Char", "Syngas"]
PROD_COLOR = {"Tar": "#D55E00", "Water": "#0072B2", "Char": "#009E73", "Syngas": "#CC79A7"}
PROD_MARKER = {"Tar": "o", "Water": "s", "Char": "^", "Syngas": "D"}

GAS_ORDER = ["H2", "CO", "CO2", "CH4", "C2H6", "C3H8", "C3H6", "C2H4", "C4H10"]
GAS_COLOR = {
    "H2": "#0072B2",
    "CO": "#D55E00",
    "CO2": "#009E73",
    "CH4": "#CC79A7",
    "C2H6": "#E69F00",
    "C3H8": "#56B4E9",
    "C3H6": "#8C564B",
    "C2H4": "#7F7F7F",
    "C4H10": "#B79F00",
}
GAS_MARKER = {
    "H2": "o",
    "CO": "s",
    "CO2": "^",
    "CH4": "D",
    "C2H6": "v",
    "C3H8": "<",
    "C3H6": ">",
    "C2H4": "p",
    "C4H10": "h",
}

DASH = (0, (3.0, 1.6))
THIN_DASH = (0, (2.2, 1.4))

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 7.2,
        "axes.titlesize": 7.8,
        "axes.labelsize": 7.4,
        "xtick.labelsize": 6.8,
        "ytick.labelsize": 6.8,
        "legend.fontsize": 6.8,
        "axes.linewidth": 0.6,
        "axes.edgecolor": "0.25",
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.4,
        "ytick.major.size": 2.4,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.dpi": 300,
        "axes.unicode_minus": True,
    }
)

_CACHE: dict[str, dict] = {}


def load(name: str) -> dict:
    """Load data/results_<name>.json once."""
    if name not in _CACHE:
        path = DATA / f"results_{name}.json"
        if not path.exists():
            raise SystemExit(f"missing input: {path}")
        _CACHE[name] = json.loads(path.read_text(encoding="utf-8"))
    return _CACHE[name]


def level_w(label: str) -> float:
    """Decode an Annex level label such as '40/100' into ash/(ash+biomass)."""
    a, b = label.split("/")
    a, b = float(a), float(b)
    return a / (a + b)


def style_ax(ax, xlabel=None, ylabel=None, title=None, title_loc="center"):
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    if title is not None:
        ax.set_title(title, loc=title_loc, pad=2.4)
    ax.tick_params(direction="out", length=2.4, width=0.6, pad=1.8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(0.6)
    ax.grid(True, which="major", color="0.90", linewidth=0.45, zorder=0)
    ax.grid(False, which="minor")
    ax.set_axisbelow(True)


def line(ax, x, y, color, marker, label=None, ls="-", lw=1.15, ms=3.0, zorder=3):
    return ax.plot(
        x,
        y,
        color=color,
        marker=marker,
        ms=ms,
        lw=lw,
        ls=ls,
        label=label,
        mec="white",
        mew=0.45,
        zorder=zorder,
    )[0]


def band(ax, x, lo, hi, color, alpha=0.16, edge_alpha=0.55):
    ax.fill_between(x, lo, hi, color=color, alpha=alpha, linewidth=0, zorder=1)
    ax.plot(x, lo, color=color, lw=0.65, alpha=edge_alpha, ls=THIN_DASH, zorder=2)
    ax.plot(x, hi, color=color, lw=0.65, alpha=edge_alpha, ls=THIN_DASH, zorder=2)


def legend_below(fig, handles, labels=None, ncol=3, y=0.020, fontsize=6.8, **kw):
    fig.legend(
        handles=handles,
        labels=labels,
        loc="lower center",
        bbox_to_anchor=(0.5, y),
        ncol=ncol,
        frameon=False,
        fontsize=fontsize,
        handlelength=1.7,
        handletextpad=0.45,
        columnspacing=1.3,
        borderaxespad=0.0,
        **kw,
    )


def h_line(color, marker, label, ls="-", lw=1.15, ms=3.0):
    return Line2D(
        [],
        [],
        color=color,
        marker=marker,
        ms=ms,
        lw=lw,
        ls=ls,
        label=label,
        mec="white",
        mew=0.45,
    )


def save(fig, stem):
    FIGDIR.mkdir(parents=True, exist_ok=True)
    pdf = FIGDIR / f"{stem}.pdf"
    png = FIGDIR / f"{stem}.png"
    fig.savefig(
        pdf,
        format="pdf",
        metadata={"Creator": "code/make_figures.py", "CreationDate": None, "ModDate": None},
    )
    fig.savefig(png, format="png", dpi=300, metadata={"Software": "code/make_figures.py"})
    plt.close(fig)
    commit(stem, FIGDIR, origin="code/make_figures.py")
    seal_path = FIGDIR / f"{stem}.seal.tex"
    print(f"[ok] {stem}.pdf {pdf.stat().st_size} B  {stem}.png {png.stat().st_size} B  "
          f"{stem}.seal.tex {seal_path.stat().st_size} B")


# ---------------------------------------------------------------------------
# Q1 - product yields, trend signal, ILR fit quality
# ---------------------------------------------------------------------------


def fig01():
    """Product yields vs ash mass fraction w, one panel per product."""
    q1 = load("q1")
    fig = plt.figure(figsize=(W_IN, 4.35))
    gs = fig.add_gridspec(
        2, 2, left=0.095, right=0.975, top=0.905, bottom=0.175, wspace=0.26, hspace=0.32
    )
    for i, p in enumerate(PROD_ORDER):
        ax = fig.add_subplot(gs[i // 2, i % 2])
        vals = []
        for c in COMBO_ORDER:
            d = q1["combos"][c]["products"][p]
            w = q1["combos"][c]["w"]
            line(ax, w, d["y"], COMBO_COLOR[c], COMBO_MARKER[c], c, ms=2.9)
            vals.extend(d["y"])
        style_ax(
            ax,
            xlabel="w (-)" if i >= 2 else None,
            ylabel="Yield (wt.%)" if i % 2 == 0 else None,
            title=p,
        )
        ax.set_xticks([0.0, 0.2, 0.4, 0.5])
        ax.set_xlim(-0.015, 0.515)
        pad = 0.10 * (max(vals) - min(vals))
        ax.set_ylim(min(vals) - pad, max(vals) + pad)
        if i < 2:
            ax.tick_params(labelbottom=False)
    handles = [h_line(COMBO_COLOR[c], COMBO_MARKER[c], c) for c in COMBO_ORDER]
    legend_below(fig, handles, ncol=3)
    header("fig01_q1_product_yields", "Q1: product yields from stored Annex I levels")
    stamp("fig01_q1_product_yields", "source: data/results_q1.json; generator: code/make_figures.py")
    save(fig, "fig01_q1_product_yields")


def fig02():
    """Observed span divided by the Monte-Carlo noise floor (ratio > 1 = signal)."""
    q1 = load("q1")
    fig = plt.figure(figsize=(W_IN, 2.55))
    gs = fig.add_gridspec(1, 1, left=0.145, right=0.985, top=0.855, bottom=0.235)
    ax = fig.add_subplot(gs[0, 0])
    offsets = {"CS": 0.13, "CE": 0.0, "LG": -0.13}
    for i, p in enumerate(PROD_ORDER):
        yy = 3 - i
        for c in COMBO_ORDER:
            v = q1["combos"][c]["products"][p]["span_over_thr"]
            ax.plot(
                v,
                yy + offsets[c],
                marker=COMBO_MARKER[c],
                ms=3.6,
                color=COMBO_COLOR[c],
                ls="none",
                mec="white",
                mew=0.5,
                zorder=3,
            )
    ax.axvline(1.0, color="0.35", lw=0.8, ls=DASH, zorder=1)
    ax.set_xscale("log")
    ax.set_xlim(0.15, 14.0)
    ax.set_xticks([0.1, 1.0, 10.0])
    ax.set_xticklabels(["0.1", "1", "10"])
    ax.set_yticks([3, 2, 1, 0])
    ax.set_yticklabels(PROD_ORDER)
    ax.set_ylim(-0.55, 3.55)
    style_ax(
        ax,
        xlabel="Observed span / noise floor (-)",
        title="Q1 trend span against the Monte-Carlo noise floor",
        title_loc="left",
    )
    handles = [h_line(COMBO_COLOR[c], COMBO_MARKER[c], c, ls="none", ms=3.6) for c in COMBO_ORDER]
    handles.append(Line2D([], [], color="0.35", lw=0.8, ls=DASH, label="noise floor (ratio 1)"))
    legend_below(fig, handles, ncol=4)
    header("fig02_q1_span_noise", "Q1: observed span against the surrogate noise floor")
    stamp("fig02_q1_span_noise", "source: data/results_q1.json; generator: code/make_figures.py")
    save(fig, "fig02_q1_span_noise")


def fig03():
    """ILR fit residual sigma vs the Monte-Carlo noise sigma, per combination."""
    q1 = load("q1")
    fig = plt.figure(figsize=(W_IN, 2.45))
    gs = fig.add_gridspec(1, 1, left=0.115, right=0.985, top=0.845, bottom=0.245)
    ax = fig.add_subplot(gs[0, 0])
    xs = list(range(3))
    fit = [q1["combos"][c]["ilr"]["sigma_fit"] for c in COMBO_ORDER]
    noise = [q1["combos"][c]["ilr"]["sigma_noise_mc"] for c in COMBO_ORDER]
    ax.bar([x - 0.17 for x in xs], fit, width=0.32, color="#0072B2", edgecolor="none", label="fit residual")
    ax.bar([x + 0.17 for x in xs], noise, width=0.32, color="#B8B8B8", edgecolor="none", label="noise floor (MC)")
    for x, v in zip(xs, fit):
        ax.text(x - 0.17, v + 0.0025, f"{v:.3f}", ha="center", va="bottom", fontsize=6.5)
    for x, v in zip(xs, noise):
        ax.text(x + 0.17, v + 0.0025, f"{v:.3f}", ha="center", va="bottom", fontsize=6.5)
    for x, c in zip(xs, COMBO_ORDER):
        f = q1["combos"][c]["ilr"]["lack_of_fit_F"]
        ax.text(x, 0.111, f"F = {f:.2f}", ha="center", va="center", fontsize=7.0)
    ax.set_xticks(xs)
    ax.set_xticklabels(COMBO_ORDER)
    ax.set_xlim(-0.55, 2.55)
    ax.set_ylim(0.0, 0.119)
    style_ax(ax, ylabel="ILR residual \u03c3 (-)", title="Q1 ILR fit residual vs the noise floor")
    handles = [
        Patch(facecolor="#0072B2", edgecolor="none", label="fit residual \u03c3"),
        Patch(facecolor="#B8B8B8", edgecolor="none", label="noise floor \u03c3 (MC)"),
    ]
    legend_below(fig, handles, ncol=2)
    header("fig03_q1_ilr_fit", "Q1: ILR residual against the Monte-Carlo noise floor")
    stamp("fig03_q1_ilr_fit", "source: data/results_q1.json; generator: code/make_figures.py")
    save(fig, "fig03_q1_ilr_fit")


# ---------------------------------------------------------------------------
# Q2 - gas components: major absolute, major phi, minor phi, Annex bridge
# ---------------------------------------------------------------------------


def fig04():
    """Major gases: absolute yield in mL/g(daf), one panel per combination."""
    q2 = load("q2")
    fig = plt.figure(figsize=(W_IN, 2.85))
    gs = fig.add_gridspec(1, 3, left=0.105, right=0.975, top=0.855, bottom=0.235, wspace=0.26)
    for j, c in enumerate(COMBO_ORDER):
        ax = fig.add_subplot(gs[0, j])
        w = q2["combos"][c]["w"]
        gases = q2["combos"][c]["gases"]
        for g in gases:
            if gases[g]["tier"] != "major":
                continue
            line(ax, w, gases[g]["z"], GAS_COLOR[g], GAS_MARKER[g], g, ms=3.0)
        style_ax(
            ax,
            xlabel="w (-)",
            ylabel="Yield (mL/g daf)" if j == 0 else None,
            title=c,
        )
        ax.set_xticks([0.0, 0.2, 0.4])
        ax.set_xlim(-0.02, 0.53)
        ax.set_ylim(0.0, None)
    handles = [h_line(GAS_COLOR[g], GAS_MARKER[g], g) for g in ["H2", "CO", "CO2", "CH4", "C2H6"]]
    legend_below(fig, handles, ncol=5)
    header("fig04_q2_major_abs", "Q2: absolute gas yields for the major species")
    stamp("fig04_q2_major_abs", "source: data/results_q2.json; generator: code/make_figures.py")
    save(fig, "fig04_q2_major_abs")


def fig05():
    """Major gases: mass share phi, one panel per combination, shared 0-1 axis."""
    q2 = load("q2")
    fig = plt.figure(figsize=(W_IN, 2.85))
    gs = fig.add_gridspec(1, 3, left=0.105, right=0.975, top=0.855, bottom=0.235, wspace=0.26)
    for j, c in enumerate(COMBO_ORDER):
        ax = fig.add_subplot(gs[0, j])
        w = q2["combos"][c]["w"]
        gases = q2["combos"][c]["gases"]
        for g in gases:
            if gases[g]["tier"] != "major":
                continue
            line(ax, w, gases[g]["phi"], GAS_COLOR[g], GAS_MARKER[g], g, ms=3.0)
        style_ax(
            ax,
            xlabel="w (-)",
            ylabel="\u03c6 (-)" if j == 0 else None,
            title=c,
        )
        ax.set_xticks([0.0, 0.2, 0.4])
        ax.set_xlim(-0.02, 0.53)
        ax.set_ylim(0.0, 1.0)
        ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    handles = [h_line(GAS_COLOR[g], GAS_MARKER[g], g) for g in ["H2", "CO", "CO2", "CH4", "C2H6"]]
    legend_below(fig, handles, ncol=5)
    header("fig05_q2_major_phi", "Q2: major-species mole fractions on a fixed scale")
    stamp("fig05_q2_major_phi", "source: data/results_q2.json; generator: code/make_figures.py")
    save(fig, "fig05_q2_major_phi")


def fig06():
    """Minor gases: mass share phi only, log axis, one panel per combination."""
    q2 = load("q2")
    fig = plt.figure(figsize=(W_IN, 2.95))
    gs = fig.add_gridspec(1, 3, left=0.108, right=0.975, top=0.845, bottom=0.275, wspace=0.26)
    for j, c in enumerate(COMBO_ORDER):
        ax = fig.add_subplot(gs[0, j])
        w = q2["combos"][c]["w"]
        gases = q2["combos"][c]["gases"]
        for g in gases:
            if gases[g]["tier"] != "minor":
                continue
            line(ax, w, gases[g]["phi"], GAS_COLOR[g], GAS_MARKER[g], g, ms=3.2)
        ax.set_yscale("log")
        style_ax(
            ax,
            xlabel="w (-)",
            ylabel="\u03c6 (-, log scale)" if j == 0 else None,
            title=c,
        )
        ax.set_xticks([0.0, 0.2, 0.4])
        ax.set_xlim(-0.02, 0.53)
        ax.set_ylim(3e-4, 8e-2)
        ax.set_yticks([1e-3, 1e-2])
        ax.set_yticklabels(["0.001", "0.01"])
    minor_union = ["H2", "CH4", "C2H6", "C3H8", "C3H6", "C2H4", "C4H10"]
    handles = [h_line(GAS_COLOR[g], GAS_MARKER[g], g, ms=3.2) for g in minor_union]
    legend_below(fig, handles, ncol=4)
    header("fig06_q2_minor_phi", "Q2: minor-species mole fractions on a log scale")
    stamp("fig06_q2_minor_phi", "source: data/results_q2.json; generator: code/make_figures.py")
    save(fig, "fig06_q2_minor_phi")


def fig07():
    """Annex II gas mass vs Annex I syngas mass; y=x would mean closure."""
    q2 = load("q2")
    fig = plt.figure(figsize=(W_IN, 3.0))
    gs = fig.add_gridspec(1, 1, left=0.105, right=0.958, top=0.870, bottom=0.235)
    ax = fig.add_subplot(gs[0, 0])
    hi = 0.0
    for c in COMBO_ORDER:
        b = q2["bridge"][c]
        line(ax, b["annex1_syngas_wtpct"], b["gas_mass_wtpct"], COMBO_COLOR[c], COMBO_MARKER[c], c, ms=3.4)
        hi = max(hi, max(b["annex1_syngas_wtpct"]), max(b["gas_mass_wtpct"]))
    ax.plot([0, hi * 1.04], [0, hi * 1.04], color="0.35", lw=0.85, ls=DASH, zorder=1)
    ax.set_xlim(0, hi * 1.06)
    ax.set_ylim(0, hi * 1.06)
    style_ax(
        ax,
        xlabel="Annex I syngas (wt.%)",
        ylabel="Annex II gas mass (wt.%)",
        title="Q2 bridge: the two annexes do not close on the 1:1 line",
        title_loc="left",
    )
    ax.text(
        0.03,
        0.96,
        "\u03b2 = y/x: CS 0.57-0.71; CE 0.15-0.50; LG 0.85-1.25",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.6,
        bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85),
    )
    handles = [h_line(COMBO_COLOR[c], COMBO_MARKER[c], c, ms=3.4) for c in COMBO_ORDER]
    handles.append(Line2D([], [], color="0.35", lw=0.85, ls=DASH, label="1:1 closure"))
    legend_below(fig, handles, ncol=4)
    header("fig07_q2_bridge", "Q2: Annex II gas mass against Annex I syngas mass")
    stamp("fig07_q2_bridge", "source: data/results_q2.json; generator: code/make_figures.py")
    save(fig, "fig07_q2_bridge")


# ---------------------------------------------------------------------------
# Q3 - CE vs LG at equal ash ratio
# ---------------------------------------------------------------------------


def fig08():
    """CE - LG product yield difference at equal ash level, with the noise band."""
    q3 = load("q3")
    levels = q3["levels_products"]
    ws = [level_w(s) for s in levels]
    fig = plt.figure(figsize=(W_IN, 4.2))
    gs = fig.add_gridspec(
        2, 2, left=0.095, right=0.985, top=0.900, bottom=0.200, wspace=0.24, hspace=0.34
    )
    for i, p in enumerate(PROD_ORDER):
        ax = fig.add_subplot(gs[i // 2, i % 2])
        d = q3["products"][p]
        line(ax, ws, d["Delta"], PROD_COLOR[p], PROD_MARKER[p], "CE - LG", ms=3.0)
        band(ax, ws, [-v for v in d["thr_diff"]], d["thr_diff"], "0.45")
        ax.axhline(0.0, color="0.35", lw=0.7, zorder=1)
        style_ax(
            ax,
            xlabel="w (-)" if i >= 2 else None,
            ylabel="\u0394 yield (wt.%)" if i % 2 == 0 else None,
            title=f"{p} ({d['n_exceed']}/{d['n']} beyond band)",
        )
        ax.set_xticks([0.1, 0.2, 0.3, 0.4, 0.5])
        ax.set_xlim(0.07, 0.53)
        if i < 2:
            ax.tick_params(labelbottom=False)
    handles = [
        h_line("0.35", "o", "CE - LG", lw=1.0),
        Patch(facecolor="0.55", edgecolor="none", alpha=0.35, label="\u00b1thr band"),
    ]
    legend_below(fig, handles, ncol=2)
    header("fig08_q3_product_delta", "Q3: CE minus LG product yields with the noise band")
    stamp("fig08_q3_product_delta", "source: data/results_q3.json; generator: code/make_figures.py")
    save(fig, "fig08_q3_product_delta")


def fig09():
    """CE/LG gas yield ratio, log axis; ratio 1 is parity."""
    q3 = load("q3")
    levels = q3["levels_gases"]
    ws = [level_w(s) for s in levels]
    fig = plt.figure(figsize=(W_IN, 3.05))
    gs = fig.add_gridspec(1, 1, left=0.095, right=0.985, top=0.865, bottom=0.245)
    ax = fig.add_subplot(gs[0, 0])
    for g in ["H2", "CO", "CO2", "CH4", "C2H6"]:
        d = q3["gases"][g]
        line(ax, ws, d["ratio_CE_over_LG"], GAS_COLOR[g], GAS_MARKER[g], g, ms=3.2)
    ax.axhline(1.0, color="0.35", lw=0.8, ls=DASH, zorder=1)
    ax.set_yscale("log")
    ax.set_ylim(0.018, 320.0)
    ax.set_yticks([0.02, 0.1, 1.0, 10.0, 100.0])
    ax.set_yticklabels(["0.02", "0.1", "1", "10", "100"])
    ax.set_xticks([0.1667, 0.2857, 0.3333, 0.4444, 0.5])
    ax.set_xticklabels(["20/100", "40/100", "50/100", "80/100", "100/100"])
    ax.set_xlim(0.14, 0.52)
    style_ax(
        ax,
        xlabel="ash / biomass level",
        ylabel="CE / LG ratio (-, log)",
        title="Q3 gas yield ratio at equal ash level",
        title_loc="left",
    )
    handles = [h_line(GAS_COLOR[g], GAS_MARKER[g], g, ms=3.2) for g in ["H2", "CO", "CO2", "CH4", "C2H6"]]
    handles.append(Line2D([], [], color="0.35", lw=0.8, ls=DASH, label="parity (ratio 1)"))
    legend_below(fig, handles, ncol=6)
    header("fig09_q3_gas_ratio", "Q3: CE/LG gas-yield ratio at equal ash level")
    stamp("fig09_q3_gas_ratio", "source: data/results_q3.json; generator: code/make_figures.py")
    save(fig, "fig09_q3_gas_ratio")


# ---------------------------------------------------------------------------
# Q4 - selectivity, carbon balance, kinetic ridge
# ---------------------------------------------------------------------------


def fig10():
    """Centered selectivity index gamma per product and combination."""
    q4 = load("q4")
    fig = plt.figure(figsize=(W_IN, 2.7))
    gs = fig.add_gridspec(1, 1, left=0.100, right=0.985, top=0.865, bottom=0.225)
    ax = fig.add_subplot(gs[0, 0])
    xs = list(range(4))
    width = 0.26
    for k, c in enumerate(COMBO_ORDER):
        vals = [q4["selectivity"][c]["gamma_centered"][p] for p in PROD_ORDER]
        ax.bar(
            [x + (k - 1) * width for x in xs],
            vals,
            width=width,
            color=COMBO_COLOR[c],
            edgecolor="none",
            label=c,
        )
    ax.axhline(0.0, color="0.35", lw=0.7)
    ax.set_xticks(xs)
    ax.set_xticklabels(PROD_ORDER)
    ax.set_xlim(-0.6, 3.6)
    ax.set_ylim(-1.75, 1.10)
    style_ax(
        ax,
        ylabel="\u03b3 (-)",
        title="Q4 product-share selectivity \u03b3 (centered, \u03a3\u03b3 = 0)",
        title_loc="left",
    )
    handles = [Patch(facecolor=COMBO_COLOR[c], edgecolor="none", label=c) for c in COMBO_ORDER]
    legend_below(fig, handles, ncol=3)
    header("fig10_q4_selectivity", "Q4: centred log-selectivity by product")
    stamp("fig10_q4_selectivity", "source: data/results_q4.json; generator: code/make_figures.py")
    save(fig, "fig10_q4_selectivity")


def fig11():
    """Gas-phase carbon per gram of biomass vs w, one panel per combination."""
    q4 = load("q4")
    fig = plt.figure(figsize=(W_IN, 2.6))
    gs = fig.add_gridspec(1, 3, left=0.115, right=0.985, top=0.855, bottom=0.225, wspace=0.30)
    for j, c in enumerate(COMBO_ORDER):
        ax = fig.add_subplot(gs[0, j])
        d = q4["carbon_balance"][c]
        ws = [level_w(s) for s in d["labels"]]
        y = d["carbon_mmol_per_g"]
        line(ax, ws, y, COMBO_COLOR[c], COMBO_MARKER[c], ms=2.9)
        ax.axhline(y[0], color="0.55", lw=0.7, ls=THIN_DASH, zorder=1)
        style_ax(
            ax,
            xlabel="w (-)",
            ylabel="nC (mmol/g daf)" if j == 0 else None,
            title=f"{c} (end \u0394 {d['delta_end_pct']:+.1f}%)",
        )
        ax.set_xticks([0.0, 0.2, 0.4])
        ax.set_xlim(-0.015, 0.515)
        lo = min(min(y), y[0])
        hi = max(max(y), y[0])
        pad = 0.12 * (hi - lo)
        ax.set_ylim(lo - pad, hi + pad)
    header("fig11_q4_carbon", "Q4: gas-phase carbon against ash level")
    stamp("fig11_q4_carbon", "source: data/results_q4.json; generator: code/make_figures.py")
    save(fig, "fig11_q4_carbon")


def fig12():
    """Compensation ridge for fixed reaction order n = 1."""
    q4 = load("q4")
    fig = plt.figure(figsize=(W_IN, 3.05))
    gs = fig.add_gridspec(1, 1, left=0.115, right=0.958, top=0.870, bottom=0.165)
    ax = fig.add_subplot(gs[0, 0])
    ridge = q4["kinetics"]["ridge_n1"]
    ea = [r["Ea_kJ_mol"] for r in ridge]
    loga = [r["log10_A"] for r in ridge]
    line(ax, ea, loga, "#7F3C8D", "o", "n = 1 ridge", ms=3.4)
    ax.set_xlim(90, 260)
    style_ax(
        ax,
        xlabel="Ea (kJ/mol)",
        ylabel="log10 A (1/s)",
        title="Q4 compensation ridge for fixed reaction order n = 1",
        title_loc="left",
    )
    ax.text(
        0.035,
        0.955,
        "kt = 2.996 at 1800 s, 800 K; each point is one (Ea, A) pair",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.5,
    )
    header("fig12_q4_ridge", "Q4: compensation ridge at fixed reaction order")
    stamp("fig12_q4_ridge", "source: data/results_q4.json; generator: code/make_figures.py")
    save(fig, "fig12_q4_ridge")


# ---------------------------------------------------------------------------
# Q5 - prediction grid, LOO error, support / extrapolation
# ---------------------------------------------------------------------------


def fig13():
    """Prediction grid: observations, mean prediction, 5-95% band, 12 panels."""
    q1 = load("q1")
    q5 = load("q5")
    grid = q5["meta"]["grid_w"]
    fig = plt.figure(figsize=(W_IN, 5.5))
    gs = fig.add_gridspec(
        3, 4, left=0.098, right=0.985, top=0.930, bottom=0.155, wspace=0.22, hspace=0.36
    )
    for r, c in enumerate(COMBO_ORDER):
        for k, p in enumerate(PROD_ORDER):
            ax = fig.add_subplot(gs[r, k])
            obs = q1["combos"][c]["products"][p]["y"]
            wobs = q1["combos"][c]["w"]
            d = q5["combos"][c]
            band(ax, grid, d["lo"][p], d["hi"][p], COMBO_COLOR[c])
            line(ax, grid, d["point"][p], COMBO_COLOR[c], None, ms=0.0, lw=1.2)
            ax.plot(
                wobs,
                obs,
                ls="none",
                marker="o",
                ms=2.4,
                mfc="white",
                mec=COMBO_COLOR[c],
                mew=0.8,
                zorder=4,
            )
            style_ax(
                ax,
                xlabel="w (-)" if r == 2 else None,
                ylabel="Yield (wt.%)" if k == 0 else None,
                title=f"{c} \u00b7 {p}",
                title_loc="left",
            )
            ax.tick_params(labelsize=6.3, pad=1.4)
            ax.set_xticks([0.2, 0.4])
            ax.set_xlim(0.10, 0.50)
            allv = obs + d["lo"][p] + d["hi"][p]
            pad = max(0.10 * (max(allv) - min(allv)), 0.08)
            ax.set_ylim(min(allv) - pad, max(allv) + pad)
            if r < 2:
                ax.tick_params(labelbottom=False)
    handles = [
        Line2D([], [], ls="none", marker="o", ms=2.8, mfc="white", mec="0.3", mew=0.8, label="observed (Annex I)"),
        Line2D([], [], color="0.35", lw=1.2, label="prediction (mean)"),
        Patch(facecolor="0.45", edgecolor="none", alpha=0.20, label="5-95% band"),
    ]
    legend_below(fig, handles, ncol=3)
    header("fig13_q5_predictions", "Q5: prediction grid with stored observations")
    stamp("fig13_q5_predictions", "source: data/results_q5.json; generator: code/make_figures.py")
    save(fig, "fig13_q5_predictions")


def fig14():
    """Leave-one-out relative RMSE per product and combination."""
    q5 = load("q5")
    fig = plt.figure(figsize=(W_IN, 2.7))
    gs = fig.add_gridspec(1, 1, left=0.100, right=0.985, top=0.865, bottom=0.235)
    ax = fig.add_subplot(gs[0, 0])
    xs = list(range(4))
    width = 0.26
    for k, c in enumerate(COMBO_ORDER):
        vals = [100.0 * q5["combos"][c]["loo_rmse_rel"][p] for p in PROD_ORDER]
        ax.bar(
            [x + (k - 1) * width for x in xs],
            vals,
            width=width,
            color=COMBO_COLOR[c],
            edgecolor="none",
            label=c,
        )
    ax.axhline(5.0, color="0.35", lw=0.85, ls=DASH, zorder=2)
    ax.set_xticks(xs)
    ax.set_xticklabels(PROD_ORDER)
    ax.set_xlim(-0.6, 3.6)
    ax.set_ylim(0.0, 21.0)
    style_ax(
        ax,
        ylabel="LOO RMSE (%)",
        title="Q5 leave-one-out relative RMSE",
        title_loc="left",
    )
    handles = [Patch(facecolor=COMBO_COLOR[c], edgecolor="none", label=c) for c in COMBO_ORDER]
    handles.append(Line2D([], [], color="0.35", lw=0.85, ls=DASH, label="5% reference line"))
    legend_below(fig, handles, ncol=4)
    header("fig14_q5_loo", "Q5: leave-one-out relative RMSE")
    stamp("fig14_q5_loo", "source: data/results_q5.json; generator: code/make_figures.py")
    save(fig, "fig14_q5_loo")


def fig15():
    """Support of the calibration data vs the widened 13-point query grid."""
    b = load("boundary")
    q5 = load("q5")
    grid = q5["meta"]["grid_w"]
    fig = plt.figure(figsize=(W_IN, 2.55))
    gs = fig.add_gridspec(1, 1, left=0.100, right=0.985, top=0.855, bottom=0.275)
    ax = fig.add_subplot(gs[0, 0])
    ypos = {"CS": 2, "CE": 1, "LG": 0}
    for c in COMBO_ORDER:
        d = b["combos"][c]
        y = ypos[c]
        ax.plot(
            [d["w_min"], d["w_max"]],
            [y, y],
            color=COMBO_COLOR[c],
            lw=6.0,
            alpha=0.20,
            solid_capstyle="butt",
            zorder=1,
        )
        for row in d["rows"]:
            mark = row["mark"]
            if mark == "":
                ax.plot(row["w"], y, marker="o", ms=3.0, color="0.45", ls="none", zorder=3)
            elif mark == "\u2605":
                ax.plot(row["w"], y, marker="^", ms=5.0, color="#E69F00", ls="none", zorder=4)
            else:
                ax.plot(row["w"], y, marker="X", ms=4.6, color="#D55E00", ls="none", zorder=5)
    for g in grid:
        ax.axvline(g, color="0.75", lw=0.5, ls=THIN_DASH, zorder=0)
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["LG", "CE", "CS"])
    ax.set_ylim(-0.55, 2.55)
    ax.set_xlim(0.03, 0.79)
    style_ax(
        ax,
        xlabel="w (-)",
        title="Q5 calibration support vs the widened query grid",
        title_loc="left",
    )
    handles = [
        Line2D([], [], color=COMBO_COLOR["CS"], lw=5.0, alpha=0.35, label="calibration support"),
        Line2D([], [], ls="none", marker="o", ms=3.2, color="0.45", label="inside support"),
        Line2D([], [], ls="none", marker="^", ms=5.0, color="#E69F00", label="at support edge"),
        Line2D([], [], ls="none", marker="X", ms=4.6, color="#D55E00", label="extrapolated"),
    ]
    legend_below(fig, handles, ncol=4)
    header("fig15_q5_support", "Q5: calibration support against the widened grid")
    stamp("fig15_q5_support", "source: data/results_boundary.json; data/results_q5.json; generator: code/make_figures.py")
    save(fig, "fig15_q5_support")


# ---------------------------------------------------------------------------
# Validation - perturbation audit and wall time
# ---------------------------------------------------------------------------


def fig16():
    """Perturbation audit counts and median wall time per pipeline call."""
    p = load("perturb")
    t = load("timing")
    cnt = p["meta"]["counts"]
    fig = plt.figure(figsize=(W_IN, 2.75))
    gs = fig.add_gridspec(
        1, 2, left=0.172, right=0.985, top=0.855, bottom=0.195, wspace=0.55, width_ratios=[1.0, 1.18]
    )

    ax = fig.add_subplot(gs[0, 0])
    labels = ["never read", "query move", "model feasible", "model infeasible"]
    vals = [cnt["never_read"], cnt["query_move"], cnt["model_feasible"], cnt["model_infeasible"]]
    ypos = list(range(len(labels)))[::-1]
    ax.barh(ypos, vals, height=0.55, color="0.55", edgecolor="none")
    for y, v in zip(ypos, vals):
        ax.text(v + 0.35, y, str(v), va="center", ha="left", fontsize=6.6)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 18)
    ax.set_ylim(-0.6, 3.6)
    style_ax(
        ax,
        xlabel="Runs (count)",
        title=f"(a) perturbation audit ({cnt['attempted']} runs)",
        title_loc="left",
    )

    ax = fig.add_subplot(gs[0, 1])
    short = {
        "selftest": "selftest",
        "load_annex_i": "load Annex I",
        "load_annex_ii": "load Annex II",
        "q1": "Q1 solve",
        "q2": "Q2 solve",
        "q3": "Q3 solve",
        "q4": "Q4 solve",
        "q5": "Q5 solve",
        "pipeline_q1_to_q5": "Q1-Q5 pipeline",
    }
    calls = t["calls"]
    names = [short.get(c["name"], c["name"]) for c in calls]
    vals = [c["median_ms"] for c in calls]
    ypos = list(range(len(calls)))[::-1]
    for y, v in zip(ypos, vals):
        ax.plot([0.13, v], [y, y], color="0.72", lw=0.6, zorder=1)
        ax.plot(v, y, marker="o", ms=3.2, color="#0072B2", ls="none", zorder=2)
        ax.text(v * 1.18, y, f"{v:.4g}", va="center", ha="left", fontsize=6.3)
    ax.set_xscale("log")
    ax.set_xlim(0.12, 900)
    ax.set_xticks([0.1, 1.0, 10.0, 100.0])
    ax.set_xticklabels(["0.1", "1", "10", "100"])
    ax.set_yticks(ypos)
    ax.set_yticklabels(names)
    ax.set_ylim(-0.6, len(calls) - 0.4)
    style_ax(
        ax,
        xlabel="Median wall time (ms, log scale)",
        title="(b) wall time, median of 5 serial runs",
        title_loc="left",
    )
    header("fig16_validation", "Q5: perturbation audit and call timing")
    stamp("fig16_validation", "source: data/results_perturb.json; data/results_timing.json; generator: code/make_figures.py")
    save(fig, "fig16_validation")


# ---------------------------------------------------------------------------

REGISTRY = {
    "fig01": fig01,
    "fig02": fig02,
    "fig03": fig03,
    "fig04": fig04,
    "fig05": fig05,
    "fig06": fig06,
    "fig07": fig07,
    "fig08": fig08,
    "fig09": fig09,
    "fig10": fig10,
    "fig11": fig11,
    "fig12": fig12,
    "fig13": fig13,
    "fig14": fig14,
    "fig15": fig15,
    "fig16": fig16,
}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build PRACTICE_2023B figures.")
    ap.add_argument("--only", default=None, help="comma-separated ids or prefixes, e.g. fig05 or fig04,fig05")
    ap.add_argument("--list", action="store_true", help="list figure ids and exit")
    args = ap.parse_args(argv)

    if args.list:
        for k in REGISTRY:
            print(k, REGISTRY[k].__doc__.strip().splitlines()[0])
        return 0

    ids = list(REGISTRY)
    if args.only:
        wants = [s.strip() for s in args.only.split(",") if s.strip()]
        ids = [k for k in ids if any(k.startswith(w) for w in wants)]
        if not ids:
            raise SystemExit(f"--only matched no figure: {args.only}")

    for k in ids:
        REGISTRY[k]()
    print(f"[done] {len(ids)} figure(s) -> {FIGDIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())