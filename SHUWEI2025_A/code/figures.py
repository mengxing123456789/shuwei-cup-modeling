# -*- coding: utf-8 -*-
"""All figures for the paper, drawn from data/*.json only (no recomputation).

House rules that keep the figures out of the "6 pt" trap and out of the
"caption promises what the axes do not show" trap:
  * one font size family (8 pt base, 7 pt ticks) and an explicit figure width in
    inches, so nothing is scaled down by the including document;
  * TrueType embedding (pdf.fonttype 42), because Type 3 text loses its size;
  * every caption number appears on the plot it belongs to.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt      # noqa: E402
import numpy as np                   # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGS = ROOT / "figures"
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 10,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.linewidth": 0.6,
    "lines.linewidth": 0.9,
    "grid.linewidth": 0.4,
    "grid.alpha": 0.35,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})
W = 5.786         # inches, exactly \\textwidth of apmcmthesis at 12 pt


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def amp_spectrum(x, dt, f_max=20.0):
    x = np.asarray(x)
    n = len(x)
    w = np.hanning(n)
    X = np.abs(np.fft.rfft((x - x.mean()) * w)) * 2 / (w.sum())
    f = np.fft.rfftfreq(n, dt)
    m = f <= f_max
    return f[m], X[m]


def fig1(q1: dict) -> None:
    """Fig 1: the two disturbances and why 8 Hz matters."""
    t = np.array(q1["t"])
    f1 = np.array(q1["f1"])
    f2 = load("q2.json")
    q2 = f2
    d = np.array([h for h in (3.0, 5.0, 8.0)])
    lines = q2["lines"]

    fig, ax = plt.subplots(1, 3, figsize=(W, 1.75))
    ax[0].plot(t, f1 / 1e3, "k-", lw=0.6)
    ax[0].set_xlabel("$t$ / s"); ax[0].set_ylabel("$F_1$ / kN")
    ax[0].set_title("(a) scenario 1 disturbance", loc="left")
    ax[0].grid(True)

    f_s, a_s = amp_spectrum(f1, 0.01)
    axb = ax[1]
    axb.semilogy(f_s, a_s / 1e3, "k-", lw=0.7)
    for hz in (5.0, 9.0):
        p = q1["scenario1_lines"][f"{hz}"]
        axb.plot([hz], [p["amp"] / 1e3], "o", ms=2.6, mfc="none", mec="k")
    axb.axvline(8.0847, color="0.45", ls="--", lw=0.7)
    axb.annotate("$\\omega_n/2\\pi$ = 8.085 Hz", xy=(8.0847, a_s.max() / 1e3 * 0.5),
                 xytext=(9.8, a_s.max() / 1e3 * 0.35), fontsize=8,
                 arrowprops=dict(arrowstyle="-", lw=0.5, color="0.45"))
    axb.set_xlabel("frequency / Hz"); axb.set_ylabel("$|\\hat{F}_1|$ / kN")
    axb.set_title("(b) its spectrum: 5.0 and 9.0 Hz", loc="left")
    axb.set_xlim(0, 16); axb.grid(True)

    axc = ax[2]
    hs = [float(h) for h in lines]
    for hz in d:
        p = lines[str(int(hz))] if str(int(hz)) in lines else lines[f"{hz}"]
        axc.bar(hz, p["amp"] / 1e3, width=0.7, color="0.75", edgecolor="k", lw=0.5)
        axc.text(hz, p["amp"] / 1e3 + 0.4, f"{p['amp']/1e3:.2f}", ha="center", fontsize=8)
    axc.set_xticks(d); axc.set_xlabel("frequency / Hz"); axc.set_ylabel("amplitude / kN")
    axc.set_title("(c) scenario 2 lines (16.79 kN at 8 Hz)", loc="left")
    axc.grid(True, axis="y")
    fig.tight_layout()
    fig.savefig(FIGS / "fig1-disturbance.pdf")
    fig.savefig(FIGS / "fig1-disturbance.png", dpi=300)
    plt.close(fig)


def fig2(q1: dict) -> None:
    """Fig 2: Q1 curves and the index."""
    t = np.array(q1["t"])
    fig, ax = plt.subplots(1, 3, figsize=(W, 1.85))
    ax[0].plot(t, np.array(q1["y_off"]) * 1e3, "k-", lw=0.7)
    ax[0].set_xlabel("$t$ / s"); ax[0].set_ylabel("$y$ / mm")
    ax[0].set_title(f"(a) off, {q1['y_pp_off_mm']:.2f} mm pp", loc="left")
    ax[0].grid(True)

    ax[1].plot(t, np.array(q1["a_on"]), "0.45", lw=0.7, label="with given angles")
    ax[1].plot(t, np.array(q1["a_off"]), "k-", lw=0.7, label="actuator off")
    ax[1].set_xlabel("$t$ / s"); ax[1].set_ylabel("$a_y$ / (m/s$^2$)")
    ax[1].set_title(f"(b) $a_{{pp}}$: {q1['a_pp_off']:.1f} / {q1['a_pp_on']:.1f}", loc="left")
    ax[1].legend(frameon=False, loc="upper right", fontsize=7); ax[1].grid(True)

    ax[2].bar([0], [q1["I_off"]], width=0.55, color="0.8", edgecolor="k", lw=0.5)
    ax[2].bar([1], [q1["I_on"]], width=0.55, color="0.45", edgecolor="k", lw=0.5)
    ax[2].text(0, q1["I_off"] + 6, f"{q1['I_off']:.2f}", ha="center", fontsize=8)
    ax[2].text(1, q1["I_on"] + 6, f"{q1['I_on']:.2f}", ha="center", fontsize=8)
    ax[2].set_xticks([0, 1]); ax[2].set_xticklabels(["off", "given\nangles"])
    ax[2].set_ylabel("$I_h$"); ax[2].set_ylim(0, q1["I_on"] * 1.2)
    ax[2].set_title(f"(c) {q1['worse_by']:.2f}$\\times$ worse", loc="left")
    ax[2].grid(True, axis="y")
    fig.tight_layout()
    fig.savefig(FIGS / "fig2-q1.pdf")
    fig.savefig(FIGS / "fig2-q1.png", dpi=300)
    plt.close(fig)


def fig3(q2: dict) -> None:
    """Fig 3: Q2 designs — time histories, command, window sweep, sensitivity."""
    t = np.array(q2.get("t", np.arange(len(q2["D"]["y"])) * 0.01))
    fig, ax = plt.subplots(2, 2, figsize=(W, 3.4))
    a0 = np.array(q2["a_uncontrolled"])
    ad = np.array(q2["D"]["a"])
    ax[0, 0].plot(t, a0, "0.6", lw=0.6, label="uncontrolled")
    ax[0, 0].plot(t, ad, "k-", lw=0.7, label="design D")
    ax[0, 0].set_xlabel("$t$ / s"); ax[0, 0].set_ylabel("$a_y$ / (m/s$^2$)")
    ax[0, 0].set_title(f"(a) peak $a$: {q2['a_pp_uncontrolled']:.1f} $\\rightarrow$ {q2['D']['a_pp']:.1f}",
                       loc="left")
    ax[0, 0].legend(frameon=False, loc="upper right"); ax[0, 0].grid(True)

    # theta_1 = W0 t + kappa + psi + pi and theta_2 = -W0 t + kappa - psi - pi, so
    # the pair sum isolates kappa exactly and the difference removes the carrier.
    th = np.array(q2["D"]["theta"])
    w0 = 2.0 * np.pi * 8.0
    kappa = 0.5 * (th[:, 0] + th[:, 1])
    psi = 0.5 * (th[:, 0] - th[:, 1]) - w0 * t - np.pi
    ax[0, 1].plot(t, np.degrees(kappa), "k-", lw=0.8, label="$\\kappa$ (depth)")
    ax[0, 1].plot(t, np.degrees(np.unwrap(psi)), "0.5", lw=0.7, label="$\\psi$ (phase)")
    ax[0, 1].set_xlabel("$t$ / s"); ax[0, 1].set_ylabel("modulation / deg")
    ax[0, 1].set_title(f"(b) modulation, peak $\\omega$ = {q2['D']['omega_max']:.1f} rad/s",
                       loc="left")
    ax[0, 1].legend(frameon=False, loc="best"); ax[0, 1].grid(True)

    sw = q2["window_sweep"]
    ax[1, 0].plot([s["win_s"] for s in sw], [s["I"] for s in sw], "ko-", ms=3, lw=0.8)
    best = min(sw, key=lambda s: s["I"])
    ax[1, 0].plot([best["win_s"]], [best["I"]], "o", ms=5, mfc="none", mec="k")
    ax[1, 0].annotate(f"{best['win_s']:.2f} s, $I$={best['I']:.1f}",
                      xy=(best["win_s"], best["I"]), xytext=(best["win_s"] + 0.18, best["I"] + 120),
                      fontsize=8, arrowprops=dict(arrowstyle="-", lw=0.5, color="0.3"))
    ax[1, 0].set_xlabel("causal window / s"); ax[1, 0].set_ylabel("$I_h$")
    ax[1, 0].set_title("(c) the window is a genuine optimum", loc="left"); ax[1, 0].grid(True)

    sens = [s for s in q2["sensitivity"] if abs(s["scale"] - 1.0) < 1e-9]
    ax[1, 1].semilogy([s["dphi_deg"] for s in sens], [s["I"] for s in sens], "ko-", ms=3, lw=0.8)
    ax[1, 1].axvline(0, color="0.5", ls="--", lw=0.6)
    ax[1, 1].set_xlabel("phase error / deg"); ax[1, 1].set_ylabel("$I_h$")
    ax[1, 1].set_title("(d) $\\pm$6$^\\circ$ costs an order of magnitude", loc="left")
    ax[1, 1].grid(True, which="both")
    fig.tight_layout()
    fig.savefig(FIGS / "fig3-q2.pdf")
    fig.savefig(FIGS / "fig3-q2.png", dpi=300)
    plt.close(fig)


def fig4(q1: dict, q2: dict, q3: dict) -> None:
    """Fig 4: Q3 and the design comparison."""
    t = np.array(q1["t"])
    fig, ax = plt.subplots(1, 3, figsize=(W, 1.85))
    # a 1.5 s slice: plotting the whole 10 s at 410 m/s^2 turns into a grey block
    sl = (t >= 4.0) & (t <= 5.5)
    ax[0].plot(t[sl], np.array(q3["Q3"]["a"])[sl], "k-", lw=0.8, label="Q3 feedback")
    ax[0].plot(t[sl], np.array(q2["a_uncontrolled"])[sl], "0.65", lw=0.7, label="uncontrolled")
    ax[0].set_xlabel("$t$ / s (steady slice)"); ax[0].set_ylabel("$a_y$ / (m/s$^2$)")
    ax[0].set_title(f"(a) $I$={q3['Q3']['I_steady']:.0f} vs {q2['I_uncontrolled']:.0f}", loc="left")
    ax[0].legend(frameon=False, loc="upper right"); ax[0].grid(True)

    names = ["uncontrolled", "A static", "D tracked", "Q3 fbk"]
    vals = [q2["I_uncontrolled"], q2["A"]["I"], q2["D"]["I"], q3["Q3"]["I_steady"]]
    # bottom must be the axis floor: bars from zero on a log axis produce
    # degenerate rectangles that run off the page (the PDF carries them).
    ax[1].bar(range(4), vals, bottom=5.0, color=["0.8", "0.6", "0.35", "0.55"],
              edgecolor="k", lw=0.5, width=0.62)
    ax[1].set_yscale("log")
    for i, v in enumerate(vals):
        ax[1].text(i, v * 1.35, f"{v:.0f}" if v >= 100 else f"{v:.1f}",
                   ha="center", fontsize=8)
    # rotated single-line labels: two-line labels in a one-third panel collide
    ax[1].set_xticks(range(4))
    ax[1].set_xticklabels(names, fontsize=7.5, rotation=22, ha="right",
                          rotation_mode="anchor")
    ax[1].tick_params(axis="x", pad=1.5, length=2.5)
    ax[1].set_ylabel("$I_h$ (log)"); ax[1].set_ylim(5, q2["I_uncontrolled"] * 12)
    ax[1].set_title("(b) indices, logarithmic", loc="left"); ax[1].grid(True, axis="y")

    pe = q3["param_error"]
    base = 100.0                       # a bar starting at 0 on a log axis is degenerate
    vals = [p["I_steady"] for p in pe]
    ax[2].barh(range(len(pe)), [v - base for v in vals], left=base, color="0.6",
               edgecolor="k", lw=0.5, height=0.55)
    ax[2].set_xscale("log")
    ax[2].set_xlim(base * 0.85, max(vals) * 3)
    ax[2].set_yticks(range(len(pe)))
    ax[2].set_yticklabels([p["case"] for p in pe], fontsize=8)
    ax[2].axvline(q3["Q3"]["I_steady"], color="k", ls="--", lw=0.6)
    for i, v in enumerate(vals):
        ax[2].text(v * 1.12, i, f"{v:.0f}", va="center", fontsize=8)
    ax[2].set_xlabel("$I_h$"); ax[2].set_title("(c) $\\pm$10% parameter error", loc="left")
    ax[2].grid(True, axis="x")
    fig.tight_layout()
    fig.savefig(FIGS / "fig4-q3.pdf")
    fig.savefig(FIGS / "fig4-q3.png", dpi=300)
    plt.close(fig)


def fig5(q2: dict) -> None:
    """Fig 5: what the actuator force actually contains."""
    t = np.array(np.arange(len(q2["D"]["fa"])) * 0.01)
    fig, ax = plt.subplots(1, 2, figsize=(W, 1.8))
    fa = np.array(q2["D"]["fa"])
    ax[0].plot(t, fa / 1e3, "k-", lw=0.6)
    ax[0].set_xlabel("$t$ / s"); ax[0].set_ylabel("$F$ / kN")
    ax[0].set_title(f"(a) peak {np.abs(fa).max()/1e3:.1f} kN of 404 kN", loc="left")
    ax[0].grid(True)

    f_s, a_s = amp_spectrum(np.array(fa)[100:], 0.01)
    lines = q2["lines"]
    for hz, style in ((3.0, "0.7"), (5.0, "0.45"), (8.0, "k")):
        ax[1].axvline(hz, color=style, ls=":", lw=0.6)
    ax[1].semilogy(f_s, a_s / 1e3, "k-", lw=0.7)
    ax[1].set_xlim(0, 14); ax[1].set_xlabel("frequency / Hz"); ax[1].set_ylabel("$|\\hat{F}|$ / kN")
    ax[1].set_title("(b) steady spectrum: 8 Hz line only, $<$0.7 kN elsewhere", loc="left")
    ax[1].grid(True, which="both")
    fig.tight_layout()
    fig.savefig(FIGS / "fig5-force.pdf")
    fig.savefig(FIGS / "fig5-force.png", dpi=300)
    plt.close(fig)


def fig6(q1: dict, conv: dict, alt: dict) -> None:
    """The two conventions, side by side: Q1 under four readings, Q2 under two bodies."""
    fig, ax = plt.subplots(1, 2, figsize=(W, 1.85))

    base = q1["I_off"]
    labels = ["$\\cos\\theta$\nthis paper", "$\\sin\\theta$", "$\\sin\\theta$\n$M$=2000",
              "$\\sin\\theta$\npublished"]
    vals = [q1["I_on"], alt["ours_2800_3600"]["Q1_on_sin"],
            alt["theirs_2000_3600"]["Q1_on_sin"], alt["theirs_2000_3500"]["Q1_on_sin"]]
    bases = [base, base, alt["theirs_2000_3600"]["Q1_off"], alt["theirs_2000_3500"]["Q1_off"]]
    x = np.arange(len(vals))
    ax[0].bar(x - 0.19, bases, width=0.36, color="0.75", label="given angles off")
    ax[0].bar(x + 0.19, vals, width=0.36, color="C0", label="given angles on")
    for i, (b, v) in enumerate(zip(bases, vals)):
        ax[0].text(i, max(b, v) * 1.06, f"{(v/b-1)*100:+.0f}%", ha="center", fontsize=7.5)
    ax[0].set_xticks(x)
    ax[0].set_xticklabels(labels, fontsize=7)
    ax[0].set_ylabel("$I_h$, scenario 1")
    ax[0].set_title("(a) one table, four readings", loc="left")
    ax[0].legend(fontsize=6.5, loc="upper right")
    ax[0].set_ylim(0, max(max(vals), max(bases)) * 1.34)
    ax[0].grid(True, axis="y")
    ax[0].set_xlim(-0.6, len(vals) - 0.4)

    rows = conv["rows"]
    tags = ["$M$=2800\n$c_0$", "$M$=2000\n$c_0$"]
    base2 = [rows[0]["I_scen2"], rows[3]["I_scen2"]]
    d = [conv["replay"]["D"]["M2800"], conv["replay"]["D"]["M2000"]]
    x2 = np.arange(2)
    ax[1].bar(x2 - 0.19, base2, width=0.36, color="0.75", label="actuator off")
    ax[1].bar(x2 + 0.19, d, width=0.36, color="C0", label="design D on")
    ax[1].set_yscale("symlog", linthresh=10)
    for i, (b, v) in enumerate(zip(base2, d)):
        ax[1].text(i, b * 1.25, f"{b:.0f}", ha="center", fontsize=7)
        ax[1].text(i + 0.19, max(v, 1.0) * 1.5, f"{v:.1f}", ha="center", fontsize=7)
    ax[1].set_xticks(x2)
    ax[1].set_xticklabels(tags, fontsize=7)
    ax[1].set_ylabel("$I_h$, scenario 2")
    ax[1].set_title("(b) the body the actuator pushes", loc="left")
    ax[1].legend(fontsize=6.5, loc="upper right")
    ax[1].grid(True, axis="y")

    fig.tight_layout()
    fig.savefig(FIGS / "fig6-conventions.pdf")
    fig.savefig(FIGS / "fig6-conventions.png", dpi=300)
    plt.close(fig)


def fig7(q2: dict) -> None:
    """The command-error surface: phase error is the expensive axis, not gain."""
    sens = q2["sensitivity"]
    scales = sorted({round(s["scale"], 3) for s in sens})
    dphis = sorted({round(s["dphi_deg"], 3) for s in sens})
    z = np.full((len(scales), len(dphis)), np.nan)
    for s in sens:
        i = scales.index(round(s["scale"], 3))
        j = dphis.index(round(s["dphi_deg"], 3))
        z[i, j] = s["I"]

    fig, ax = plt.subplots(1, 1, figsize=(W * 0.62, 2.0))
    im = ax.imshow(np.log10(z), aspect="auto", origin="lower", cmap="viridis")
    ax.set_xticks(range(len(dphis)))
    ax.set_xticklabels([f"{d:+.0f}" for d in dphis], fontsize=7)
    ax.set_yticks(range(len(scales)))
    ax.set_yticklabels([f"{s:.1f}" for s in scales], fontsize=7)
    ax.set_xlabel("command phase error (deg)")
    ax.set_ylabel("gain scale")
    for i in range(len(scales)):
        for j in range(len(dphis)):
            v = z[i, j]
            if not np.isfinite(v):
                continue
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6,
                    color="white" if np.log10(v) > 2.4 else "black")
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("$\\log_{10} I_h$", fontsize=8)
    ax.set_title("$I_h$ against the two command errors; the nominal point is the dark cell",
                 loc="left", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGS / "fig7-sensitivity.pdf")
    fig.savefig(FIGS / "fig7-sensitivity.png", dpi=300)
    plt.close(fig)


def fig8(lead: dict, q3: dict) -> None:
    """The trained model: learning curve, the lead that matters, DAgger, robustness.

    Four panels at 5.8 in wide means each axis is only ~2.6 in: the 10 pt house
    default does not fit (titles ran into the neighbouring panel and the tick
    labels under (d) sat behind its legend), so this one figure drops to 8 pt
    body / 6.5 pt legend and carries its numbers inside the axes instead of in
    the title.
    """
    fig, ax = plt.subplots(2, 2, figsize=(W, 2.75), layout="constrained")
    for a in ax.ravel():
        a.tick_params(labelsize=7)
        a.set_title(a.get_title(), fontsize=8)
    fig.get_layout_engine().set(w_pad=0.02, h_pad=0.02, wspace=0.02, hspace=0.02)

    # (a) learning curve, standardised MSE
    h = lead["history"]
    ep = np.arange(len(h["train"]))
    a0 = ax[0, 0]
    a0.semilogy(ep, h["train"], lw=0.8, label="train")
    a0.semilogy(ep, h["val"], lw=0.8, label="held-out")
    a0.axvline(h["best_epoch"], ls=":", c="0.4", lw=0.7)
    a0.set_xlabel("epoch", fontsize=8)
    a0.set_ylabel("MSE (std.)", fontsize=8)
    a0.set_title("(a) learning curve", fontsize=8)
    a0.legend(loc="upper right", fontsize=6.5)
    a0.grid(True, which="both", alpha=0.25)
    a0.text(0.03, 0.06, f"best ep {h['best_epoch']}", transform=a0.transAxes, fontsize=6.5)

    # (b) the lead: sweep with the anti-phase trap
    a1 = ax[0, 1]
    ks = sorted(lead["lead_sweep"], key=lambda k: int(k))
    ms = [lead["lead_sweep"][k]["fs_ms"] for k in ks]
    Is = [lead["lead_sweep"][k]["I"] for k in ks]
    a1.semilogy(ms, Is, "o-", ms=2.5, lw=0.8)
    a1.axhline(lead["I_ref_line8"], ls="--", c="0.55", lw=0.7)
    a1.annotate("anti-phase", (60, max(Is)), fontsize=6.5,
                textcoords="offset points", xytext=(3, -10))
    a1.set_xlabel("forecast lead / ms", fontsize=8)
    a1.set_ylabel("$I_h$", fontsize=8)
    a1.set_title("(b) lead = demodulator delay", fontsize=8)
    a1.grid(True, which="both", alpha=0.25)

    # (c) DAgger rounds
    a2 = ax[1, 0]
    d = lead["L3"]["dagger"]
    rk = sorted(d, key=int)
    a2.semilogy([int(k) for k in rk], [d[k]["I"] for k in rk], "s-", ms=2.5, lw=0.8)
    a2.set_xlabel("DAgger round", fontsize=8)
    a2.set_ylabel("$I_h$ from $a_y$", fontsize=8)
    a2.set_title("(c) own-state aggregation", fontsize=8)
    a2.grid(True, which="both", alpha=0.25)
    a2.text(0.35, 0.86, f"deploy round {lead['L3']['best_round']}",
            transform=a2.transAxes, fontsize=6.5)

    # (d) robustness: learned FF vs hybrid vs Newton
    a3 = ax[1, 1]
    cases = ["nominal", "k+10%", "k-10%", "c+50%", "c-50%", "M+10%", "M-10%"]
    newt = {row["case"]: row["I_steady"] for row in q3["param_error"]}
    newt["nominal"] = q3["Q3"]["I_steady"]
    ff = [lead["L3"]["robustness"][c]["I"] for c in cases]
    hy = [lead["L3"]["hybrid"][c]["I"] for c in cases]
    nw = [newt[c] for c in cases]
    x = np.arange(len(cases))
    a3.bar(x - 0.26, ff, 0.24, label="learned FF")
    a3.bar(x, hy, 0.24, label="FF + trim")
    a3.bar(x + 0.26, nw, 0.24, label="Newton")
    a3.set_yscale("log")
    a3.set_ylim(20, 4e5)
    a3.set_xticks(x)
    a3.set_xticklabels(["nom", "+k", "-k", "+c", "-c", "+M", "-M"], fontsize=6.5)
    a3.set_ylabel("$I_h$", fontsize=8)
    a3.set_title("(d) robustness to model error", fontsize=8)
    a3.legend(loc="upper center", fontsize=7, ncol=3, frameon=False, framealpha=0.0,
              bbox_to_anchor=(0.5, 1.02), handlelength=1.0, columnspacing=0.8)
    a3.grid(True, axis="y", which="both", alpha=0.25)
    fig.savefig(FIGS / "fig8-learning.pdf")
    fig.savefig(FIGS / "fig8-learning.png", dpi=300)
    plt.close(fig)


def fig9(lead: dict) -> None:
    """Fig 9: the whole paper in one picture --- a vector in the (a,b) plane.

    The disturbance's 8 Hz line is a point that walks around a circle.  A causal
    window reports where it *was*; the network reports where it *will be*.  Panel
    (a) draws the three trajectories, panel (b) the phase error over time, which
    is the quantity every design in the paper actually competes on.
    """
    ph = lead["phasor"]
    ta, tb = np.array(ph["true_a"]), np.array(ph["true_b"])
    ca, cb = np.array(ph["causal_a"]), np.array(ph["causal_b"])
    la, lb = np.array(ph["learned_a"]), np.array(ph["learned_b"])
    ga, gb = np.array(ph["l3_a"]), np.array(ph["l3_b"])
    pe = lead["phase_error"]
    t = np.arange(len(ta)) * 0.01
    sl = (t >= 2.0) & (t <= 2.75)      # a short slice: the full record fills the plane

    fig, ax = plt.subplots(1, 2, figsize=(W, 2.1))

    ax[0].plot(ta[sl] / 1e3, tb[sl] / 1e3, "-", color="0.82", lw=6.0, solid_capstyle="round",
               label="true, walked by the line", zorder=1)
    ax[0].plot(ca[sl] / 1e3, cb[sl] / 1e3, "--", color="0.45", lw=1.0,
               label="causal window", zorder=2)
    ax[0].plot(la[sl] / 1e3, lb[sl] / 1e3, "-", color="C0", lw=1.0,
               label="network, $+0.12$ s", zorder=3)
    i0 = int(np.argmax(sl))
    ax[0].annotate("", xy=(la[i0] / 1e3, lb[i0] / 1e3), xytext=(ca[i0] / 1e3, cb[i0] / 1e3),
                   arrowprops=dict(arrowstyle="->", lw=0.9, color="k", shrinkA=0, shrinkB=0))
    ax[0].plot(ta[i0] / 1e3, tb[i0] / 1e3, "k*", ms=7, zorder=4)
    ax[0].set_xlabel("$a$ / kN"); ax[0].set_ylabel("$b$ / kN")
    ax[0].set_title("(a) the line as a point that walks", loc="left")
    ax[0].legend(frameon=True, framealpha=1.0, edgecolor="none", facecolor="white",
                 loc="lower left", fontsize=6.2, handlelength=1.6,
                 borderpad=0.25, labelspacing=0.25)
    ax[0].grid(True, alpha=0.25); ax[0].set_aspect("equal", adjustable="datalim")

    # phase in RADIANS: wrapping with exp(1j*deg) silently treats degrees as radians
    def phase(xa, xb):
        return np.arctan2(-xa, xb)

    pt = np.unwrap(phase(ta, tb))
    d_c = np.degrees(np.angle(np.exp(1j * (phase(ca, cb) - pt))))
    d_l = np.degrees(np.angle(np.exp(1j * (phase(la, lb) - pt))))
    d_g = np.degrees(np.angle(np.exp(1j * (phase(ga, gb) - pt))))
    ax[1].plot(t, d_c, color="0.45", lw=0.7, label=f"causal window, {pe['official_causal_median_deg']:.0f}$^\\circ$")
    ax[1].plot(t, d_g, color="C1", lw=0.7, label=f"from $a_y$ only, {pe['official_l3_median_deg']:.1f}$^\\circ$")
    ax[1].plot(t, d_l, color="C0", lw=0.9, label=f"network, {pe['official_learned_median_deg']:.1f}$^\\circ$")
    ax[1].axhline(0, color="k", lw=0.5)
    ax[1].set_ylim(-30, 46)
    ax[1].set_xlabel("$t$ / s"); ax[1].set_ylabel("phase error / deg")
    ax[1].set_title("(b) median error on the official record", loc="left")
    ax[1].legend(frameon=True, framealpha=1.0, edgecolor="none", loc="upper right",
                 fontsize=6.2, ncol=1, handlelength=1.3, borderpad=0.25, labelspacing=0.25)
    ax[1].grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGS / "fig9-phasor.pdf")
    fig.savefig(FIGS / "fig9-phasor.png", dpi=300)
    plt.close(fig)


def main() -> int:
    FIGS.mkdir(exist_ok=True)
    q1, q2, q3 = load("q1.json"), load("q2.json"), load("q3.json")
    conv = load("convention.json")
    alt = load("q1_alt.json")
    lead = load("lead.json")
    fig1(q1)
    fig2(q1)
    fig3(q2)
    fig4(q1, q2, q3)
    fig5(q2)
    fig6(q1, conv, alt)
    fig7(q2)
    fig8(lead, q3)
    fig9(lead)
    for p in sorted(FIGS.glob("*.pdf")):
        print(f"  {p.name}: {p.stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
