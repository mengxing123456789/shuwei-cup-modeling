# -*- coding: utf-8 -*-
"""Regenerate every paper figure in English (competition format forbids Chinese
inside figures). All curves are read from data/*.json so the figures and the
tables share one source of truth.

Run:  python make_paper_figures.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
FIG = os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "font.size": 16,
    "axes.titlesize": 16,
    "axes.labelsize": 16,
    "legend.fontsize": 12.5,
    "xtick.labelsize": 13.5,
    "ytick.labelsize": 13.5,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.4,
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
})

CASES = ["Case1", "Case2", "Case3"]
COL = {"Case1": "#2b6cb0", "Case2": "#c05621", "Case3": "#2f855a"}
LS = {"Case1": "-", "Case2": "--", "Case3": "-."}


def load(name):
    with open(os.path.join(DATA, name), "r", encoding="utf-8") as f:
        return json.load(f)


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIG, f"{name}.{ext}"))
    plt.close(fig)
    print("saved", name)


p1 = load("p1_mechanistic.json")
p2 = load("p2_shape.json")
p3 = load("p3_decline.json")
p4 = load("p4_econ.json")
p5 = load("p5_sobol.json")

# ----------------------------------------------------------------- 1. schematic
fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.9), gridspec_kw={"width_ratios": [1.15, 1]})
ax = axes[0]
# matrix block
ax.add_patch(Rectangle((0, 0), 3.0, 1.8, facecolor="#f7fafc", edgecolor="k", lw=1.0))
# fracture plane (vertical, centre)
ax.plot([1.5, 1.5], [0.05, 1.75], color="#c53030", lw=2.2)
# half block width
ax.annotate("", xy=(1.5, 0.16), xytext=(2.95, 0.16), arrowprops=dict(arrowstyle="<->", lw=0.7))
ax.text(2.22, 0.26, "$L=h/2$", ha="center", fontsize=13)
# injection arrows
for y in (0.55, 0.95, 1.35):
    ax.add_patch(FancyArrowPatch((0.35, y), (1.42, y), arrowstyle="-|>", mutation_scale=8,
                                 lw=1.0, color="#2b6cb0"))
ax.text(0.06, 1.58, "CO$_2$ + nanofluid\ninjection", fontsize=13, color="#2b6cb0")
# pressure / damage fronts
ax.plot([2.35, 2.35], [0.05, 1.75], color="#2b6cb0", lw=1.0, ls="--")
ax.plot([2.52, 2.52], [0.05, 1.75], color="#2f855a", lw=1.0, ls=":")
ax.text(2.30, 0.62, "$R_p(t)$", fontsize=13, color="#2b6cb0", rotation=90, ha="right")
ax.text(2.56, 0.62, "$R_d$", fontsize=13, color="#2f855a", rotation=90, ha="left")
ax.set_xlim(0, 3.25); ax.set_ylim(0, 2.0); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(a) Fracture-matrix domain and moving fronts")

ax2 = axes[1]
ax2.set_xlim(0, 100); ax2.set_ylim(0, 3)
stages = [(0, 15, "Injection\n(10 d)", "#bee3f8"), (15, 46, "Soak $t_s$\n(5-60 d)", "#fefcbf"),
          (46, 100, "Production (360 d)", "#c6f6d5")]
for x0, x1, lab, col in stages:
    ax2.add_patch(Rectangle((x0, 1.0), x1 - x0, 0.9, facecolor=col, edgecolor="k", lw=0.8))
    ax2.text((x0 + x1) / 2, 1.45, lab, ha="center", va="center", fontsize=13)
ax2.annotate("$p=p_{max}$\n$q=q_{inj}$", xy=(5, 1.0), xytext=(7, 0.25), ha="center",
             fontsize=12, arrowprops=dict(arrowstyle="->", lw=0.6))
ax2.annotate("$p$ relaxes,\nnano attaches", xy=(25, 1.9), xytext=(30, 2.45), ha="center",
             fontsize=12, arrowprops=dict(arrowstyle="->", lw=0.6))
ax2.annotate("$p_{wf}=35$ MPa\nNPV discount", xy=(70, 1.0), xytext=(72, 0.25), ha="center",
             fontsize=12, arrowprops=dict(arrowstyle="->", lw=0.6))
ax2.axis("off")
ax2.set_title("(b) Three-stage operating protocol")
save(fig, "fig_schematic")

# ----------------------------------------------------------------- 2. scaling
fig, ax = plt.subplots(figsize=(4.6, 3.2))
for c in CASES:
    r = p1["radii"][c]
    t = r["t_d"]; rp = r["Rp"]
    ax.loglog(t, rp, LS[c], color=COL[c], label=f"{c.replace('Case','Case ')} (numerical)")
# reference slope 1/2 anchored at Case1 t=10
import math
t0, r0 = 10.0, None
for i, tt in enumerate(p1["radii"]["Case1"]["t_d"]):
    if abs(tt - t0) < 1e-9:
        r0 = p1["radii"]["Case1"]["Rp"][i]
ax.loglog([1, 60], [r0 * math.sqrt(1 / t0), r0 * math.sqrt(60 / t0)], "k:", lw=0.9,
          label=r"reference $t^{1/2}$")
ax.set_xlabel("Soak time $t$ (d)")
ax.set_ylabel("Stimulated radius $R_p$ (m)")
ax.grid(True, which="both", ls=":", lw=0.4, alpha=0.5)
ax.legend(loc="upper left", frameon=False)
save(fig, "fig_scaling")

# ----------------------------------------------------------------- 3. shape discrimination
row = [x for x in p2["rows"] if x["case"] == "Case1" and abs(x["cn"] - 1.0) < 1e-9][0]
ts = row["ts"]; eur = row["EUR"]
sh = row["shapes"]
fig, axes = plt.subplots(2, 1, figsize=(4.6, 3.6), sharex=True,
                         gridspec_kw={"height_ratios": [2.1, 1], "hspace": 0.08})
ax = axes[0]
ax.plot(ts, eur, "o", ms=4, color="k", label="measured")
ax.plot(ts, sh["S2_exp"]["fit"], "-", color="#2b6cb0",
        label=f"exponential saturation ($R^2$={sh['S2_exp']['r2']:.4f})")
ax.plot(ts, sh["S1_sqrt"]["fit"], "--", color="#c05621",
        label=f"square-root ($R^2$={sh['S1_sqrt']['r2']:.4f})")
ax.set_ylabel("Cumulative oil (m$^3$)")
ax.legend(frameon=False, loc="lower right")
ax2 = axes[1]
ax2.axhline(0, color="k", lw=0.6)
ax2.plot(ts, sh["S2_exp"]["resid"], "o-", ms=3, lw=1.0, color="#2b6cb0", label="exp. residual")
ax2.plot(ts, sh["S1_sqrt"]["resid"], "s--", ms=3, lw=1.0, color="#c05621", label="sqrt residual")
ax2.set_xlabel("Soak time $t_s$ (d)")
ax2.set_ylabel("Residual (m$^3$)")
ax2.legend(frameon=False, loc="lower left", ncol=2)
save(fig, "fig_shape")

# ----------------------------------------------------------------- 4. soak saturation
fig, ax = plt.subplots(figsize=(4.6, 3.2))
CN = [0.5, 1.0, 1.5]
alphas = {0.5: 0.45, 1.0: 0.75, 1.5: 1.0}
for c in CASES:
    for cn in CN:
        rr = [x for x in p2["rows"] if x["case"] == c and abs(x["cn"] - cn) < 1e-9][0]
        ax.plot(rr["ts"], rr["EUR"], LS[c], color=COL[c], alpha=alphas[cn],
                label=f"{c.replace('Case','Case ')} $c_n$={cn}")
ax.set_xlabel("Soak time $t_s$ (d)")
ax.set_ylabel("Cumulative oil at 360 d (m$^3$)")
ax.grid(True, ls=":", lw=0.4, alpha=0.5)
ax.legend(frameon=False, ncol=3, fontsize=12, loc="upper left")
save(fig, "fig_soak")

# ----------------------------------------------------------------- 5. NPV
fig, ax = plt.subplots(figsize=(4.6, 3.2))
for c in CASES:
    cur = p4["npv_curves"][f"{c}|cn1.0"]
    ts = [p["ts"] for p in cur]; npv = [p["npv"] for p in cur]
    ax.plot(ts, [v / 1e4 for v in npv], LS[c], color=COL[c], label=c.replace("Case", "Case "))
ax.axhline(0, color="k", lw=0.7)
ax.set_xlabel("Soak time $t_s$ (d)")
ax.set_ylabel("NPV ($10^4$ CNY)")
ax.grid(True, ls=":", lw=0.4, alpha=0.5)
ax.legend(frameon=False)
save(fig, "fig_npv")

# ----------------------------------------------------------------- 6. Pareto
fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.6), sharey=False)
for j, c in enumerate(CASES):
    ax = axes[j]
    for cal, mk, alpha in [("geo", "o", 0.55), ("emp", "^", 0.55)]:
        front = p4["pareto"][f"{c}|{cal}"]
        ax.scatter([p["cost_nom"] / 1e4 for p in front], [p["EUR_m3"] for p in front],
                   s=7, marker=mk, alpha=alpha, label=f"$V_0$ {cal}")
    kn = p4["pareto_meta"][f"{c}|geo"]["knee"]
    ax.scatter([kn["cost_nom"] / 1e4], [kn["EUR_m3"]], marker="*", s=90, color="k",
               zorder=5, label="knee")
    ax.set_title(c.replace("Case", "Case "))
    ax.set_xlabel("Nominal cost ($10^4$ CNY)")
    if j == 0:
        ax.set_ylabel("EUR (m$^3$)")
    ax.grid(True, ls=":", lw=0.4, alpha=0.5)
    ax.legend(frameon=False, fontsize=12, loc="lower right")
save(fig, "fig_pareto")

# ----------------------------------------------------------------- 7. Sobol
fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7))
FACTORS = ["Ainf", "tau", "D", "Poil", "cprod", "csoak", "Cfrac", "a"]
LBL = ["$A_{inf}$", "$\\tau$", "$D$", "$P_{oil}$", "$c_{prod}$", "$c_{soak}$", "$C_{frac}$", "$a$"]
for ax, key, title in [(axes[0], "npv", "(a) Maximum NPV"), (axes[1], "ts", "(b) Optimal soak time")]:
    w = 0.26
    x = range(len(FACTORS))
    for k, c in enumerate(CASES):
        vals = [p5["sobol"][c][key]["S1"][f] for f in FACTORS]
        ax.bar([i + (k - 1) * w for i in x], vals, width=w, color=COL[c],
               label=c.replace("Case", "Case "))
    ax.set_xticks(list(x)); ax.set_xticklabels(LBL, fontsize=13)
    ax.set_ylabel("First-order Sobol index")
    ax.set_title(title)
    ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.5)
    ax.legend(frameon=False, fontsize=12)
save(fig, "fig_sobol")

# ----------------------------------------------------------------- 8. robustness
fig, ax = plt.subplots(figsize=(4.8, 3.0))
names = None
for c in CASES:
    rob = p4["robustness"][c]
    if names is None:
        names = list(rob["cases"].keys())
    d = [(rob["cases"][n]["npv"] - rob["base_npv"]) / 1e4 for n in names]
    ax.plot(range(len(names)), d, LS[c], marker="o", ms=2.5, color=COL[c],
            label=c.replace("Case", "Case "))
ax.axhline(0, color="k", lw=0.7)
ax.set_xticks(range(len(names)))
ax.set_xticklabels(names, rotation=45, ha="right", fontsize=12)
ax.set_ylabel("$\\Delta$NPV vs. base ($10^4$ CNY)")
ax.grid(True, ls=":", lw=0.4, alpha=0.5)
ax.legend(frameon=False)
save(fig, "fig_robust")

print("ALL FIGURES OK")
