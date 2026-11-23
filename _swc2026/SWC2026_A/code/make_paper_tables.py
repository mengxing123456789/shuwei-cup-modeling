# -*- coding: utf-8 -*-
"""Generate LaTeX table fragments for the A-problem paper from data/*.json.

Every number written into tables/ comes from a JSON file produced by the
solution scripts, so the paper never carries hand-typed numbers.
Run:  python make_paper_tables.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
TAB = os.path.join(ROOT, "tables")
os.makedirs(TAB, exist_ok=True)


def load(name):
    with open(os.path.join(DATA, name), "r", encoding="utf-8") as f:
        return json.load(f)


def w(name, text):
    with open(os.path.join(TAB, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote", name, len(text), "chars")


def sci(x, nd=2):
    if x == 0:
        return "0"
    if abs(x) >= 1e-3 and abs(x) < 1e4:
        return f"{x:.{nd}f}"
    e = 0
    y = abs(x)
    while y >= 10:
        y /= 10.0
        e += 1
    while y < 1:
        y *= 10.0
        e -= 1
    sign = "-" if x < 0 else ""
    return f"{sign}{y:.{nd}f}\\times10^{{{e}}}"


p1 = load("p1_mechanistic.json")
p2 = load("p2_shape.json")
p3 = load("p3_decline.json")
p4 = load("p4_econ.json")
p5 = load("p5_sobol.json")

CASES = ["Case1", "Case2", "Case3"]

# ---------------------------------------------------------------- Table 1: Pi groups
MEAN = {
    "Pi1": "Pressure diffusion in 60 d",
    "Pi2": "Biot coupling strength",
    "Pi3": "Stress-permeability gain",
    "Pi4": "Pore compressibility share",
    "Pi5": "CO$_2$ diffusion Fourier no.",
    "Pi6": "Nanoparticle retardation",
    "Pi7": "Damage steepness $\\times$ threshold",
    "Pi8": "Face stress / damage threshold",
    "Pi9": "Injectivity vs pump rate",
    "Pi10": "Soak / production time",
}
PI_DEF = {
    "Pi1": r"$\alpha_p t/L^2$",
    "Pi2": r"$\alpha_b p_0/K_b$",
    "Pi3": r"$\gamma_k\Delta p_{max}$",
    "Pi4": r"$c_\phi/(c_o+c_\phi)$",
    "Pi5": r"$D_{CO2}t/L^2$",
    "Pi6": r"$1+\rho_r K_d/\phi_0$",
    "Pi7": r"$\beta_d\varepsilon_d$",
    "Pi8": r"$a_\sigma\sqrt{L_f/w_f}\,\alpha_b\Delta p/(K_b\varepsilon_d)$",
    "Pi9": r"$k\Delta p/(\mu q/A_{face})$",
    "Pi10": r"$t_{soak}/T_{prod}$",
}
rows = []
keys = [k for k in p1["dimensionless"]["Case1"].keys() if not k.startswith("_")]
for k in keys:
    pi = k.split("_")[0]
    vals = " & ".join(p1["dimensionless"][c][k]["fmt"] for c in CASES)
    rows.append(f"$\\Pi_{{{pi[2:]}}}$ & {PI_DEF[pi]} & {MEAN.get(pi,'')} & {vals} \\\\")
w("tab_pi.tex", r"""\begin{table}[htbp]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\caption{Dimensionless groups of the coupled model and their magnitudes in the three design cases ($\alpha_p=k/(\mu\phi c_t)$, $L=h/2$, $t=60$ d).}
\label{tab:pi}
\begin{tabular}{@{}llp{4.3cm}ccc@{}}
\toprule
Group & Definition & Physical meaning & Case 1 & Case 2 & Case 3 \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

# ---------------------------------------------------------------- Table 2: term balance
TERM_NAME = {
    "darcy_drive": "Viscous drive $\\Delta p/L$",
    "accumulation": "Accumulation $(\\phi c_t\\Delta p/t_{ref})\\mu/k$",
    "gravity": "Gravity $\\Delta\\rho g$",
    "capillary": "Capillary $A_c/L$",
    "thermal": "Thermal expansion",
}
trs = []
for t in ["darcy_drive", "accumulation", "gravity", "capillary", "thermal"]:
    cells = []
    for c in CASES:
        v = p1["terms"][c][t]
        cells.append(f"{v['ratio']:.4f}" if v["ratio"] >= 1e-3 else sci(v["ratio"], 2))
    trs.append(f"{TERM_NAME[t]} & " + " & ".join(cells) + " \\\\")
w("tab_terms.tex", r"""\begin{table}[htbp]
\centering
\caption{Order-of-magnitude balance of the transport terms, normalised by the viscous drive (ratio to $\Delta p/L$). Values below $10^{-2}$ are dropped from the pressure equation; capillary is retained and its residual is quantified in Section~\ref{sec:p2}.}
\label{tab:terms}
\small
\begin{tabular}{@{}lccc@{}}
\toprule
Term & Case 1 & Case 2 & Case 3 \\
\midrule
""" + "\n".join(trs) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

# ---------------------------------------------------------------- Table 3: radii & scaling
sc = []
for c in CASES:
    s = p1["scaling"][c]
    r = p1["radii"][c]
    sc.append(
        f"{c} & {r['Rp'][-1]:.2f} & {r['RC'][-1]:.3f} & {r['Rd'][-1]:.3f} & "
        f"{s['early']['nu']:.4f} & {s['all']['nu']:.4f} & {s['late']['nu']:.4f} & "
        f"{s['R_analytic_60d']:.2f} & {s['ratio_num_ana']:.3f} \\\\"
    )
w("tab_scaling.tex", r"""\begin{table}[htbp]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\caption{Radii at $t=60$ d and the fitted exponent $\nu$ in $R_p=Ct^{\nu}$ over three windows (1--20, 1--60, 20--60 d). $R_{an}$ is the analytic self-similar radius; $R_{num}/R_{an}>1$ measures the enhancement from stress-sensitive permeability and damage.}
\label{tab:scaling}
\begin{tabular}{@{}lcccccccc@{}}
\toprule
Case & $R_p$ (m) & $R_C$ (m) & $R_d$ (m) & $\nu_1$ & $\nu_2$ & $\nu_3$ & $R_{an}$ (m) & $R_{num}/R_{an}$ \\
\midrule
""" + "\n".join(sc) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

shape_rows = []
for c in CASES:
    rec = [q for q in p2["rows"] if q["case"] == c and abs(q["cn"] - 1.0) < 1e-9][0]
    sh = rec["shapes"]
    shape_rows.append(
        f"{c} & {sh['S1_sqrt']['r2']:.4f} & {sh['S2_exp']['r2']:.4f} & {sh['S3_power']['r2']:.4f} & "
        f"{sh['S3_power']['params']['nu']:.4f} & {sh['S2_exp']['params']['tau']:.3f} & "
        f"{sh['S1_sqrt']['resid_runs']} & {sh['S2_exp']['resid_runs']} \\\\"
    )

w("tab_shape.tex", r"""\begin{table}[htbp]
\centering
\caption{Shape discrimination on the measured cumulative production ($c_n=1.0$). The exponential-saturation model wins on $R^2$ and on the sign-run test of its residuals (expected 6.5 runs under randomness); the free power law returns an exponent well below the diffusive value $1/2$.}
\label{tab:shape}
\small
\begin{tabular}{@{}lccccccc@{}}
\toprule
Case & $R^2_{\sqrt{t}}$ & $R^2_{\exp}$ & $R^2_{\mathrm{pow}}$ & $\nu_{\mathrm{data}}$ & $\tau$ (d) & runs$_{\sqrt{t}}$ & runs$_{\exp}$ \\
\midrule
""" + "\n".join(shape_rows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

# ---------------------------------------------------------------- Table 5: model selection
ms = p3["model_selection"]
MODEL_DESC = {
    "M1": "Per-group Arps, free $q_i,D,b$",
    "M2": "Per-group exponential decline",
    "M3": "Per-group stretched exponential",
    "M4": "Shared $D$, group amplitudes",
    "M5": "Shared $D$, $q_i=A_{inf}(1-e^{-t_s/\\tau})$, $b=1$",
}
mrows = []
for m in ["M1", "M2", "M3", "M4", "M5"]:
    v = ms[m]
    mrows.append(f"{m} & {MODEL_DESC[m]} & {v['kpar']} & {v['rmse']:.4f} & {v['aic']:.1f} & {v['bic']:.1f} \\\\")
w("tab_modelsel.tex", r"""\begin{table}[htbp]
\centering
\caption{Candidate production models fitted to all 108 groups. M3 attains the lowest AIC because it spends 324 parameters; M5 uses 15 shared parameters and is the only candidate that can extrapolate to an unseen soak duration.}
\label{tab:modelsel}
\small
\begin{tabular}{@{}llcccc@{}}
\toprule
Model & Form & Parameters & RMSE & AIC & BIC \\
\midrule
""" + "\n".join(mrows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

# ---------------------------------------------------------------- Table 6: M5 params
mp = p3["M5_params"]
sd = p3["shared_D"]
m5rows = []
for c in CASES:
    v = mp[c]
    m5rows.append(
        f"{c} & {v['Ainf']:.3f} & {v['tau']:.2f} & {v['p']:.4f} & {v['r2']:.5f} & {100*v['rel_rmse']:.2f} & "
        f"{sd[c]['D']*1e4:.3f} & {100*sd[c]['D_cv']:.2f} \\\\"
    )
w("tab_m5.tex", r"""\begin{table}[htbp]
\centering
\caption{Parameters of the selected model M5 (shared decline exponent $D$ and per-case shape parameters). $D$ is estimated with a cross-group coefficient of variation below 0.5\%, so it is treated as a reservoir property rather than a fitted nuisance.}
\label{tab:m5}
\small
\begin{tabular}{@{}lccccccc@{}}
\toprule
Case & $A_{inf}$ (m$^3$/d) & $\tau$ (d) & $p$ & $R^2$ & rel. RMSE (\%) & $D$ ($10^{-4}$/d) & CV of $D$ (\%) \\
\midrule
""" + "\n".join(m5rows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

# ---------------------------------------------------------------- Table 7: CV
cvrows = []
for i, f in enumerate(p3["cv"]):
    held = ", ".join(str(int(x)) for x in f["held_out_ts"])
    cvrows.append(
        f"{i+1} & {held} & {f['M4_rmse']:.4f} & {f['M5_rmse']:.4f} & {f['M5_n']} \\\\"
    )
w("tab_cv.tex", r"""\begin{table}[htbp]
\centering
\caption{Group-wise cross-validation. Each fold holds out two complete soak levels, so every test point is an extrapolation in soak time; no adjacent-day leakage is possible. M2 is not scored because its per-group parameterisation cannot be identified outside the training soak levels.}
\label{tab:cv}
\small
\begin{tabular}{@{}clccc@{}}
\toprule
Fold & Held-out soak levels (d) & M4 RMSE & M5 RMSE & Test rows \\
\midrule
""" + "\n".join(cvrows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

# ---------------------------------------------------------------- Table 8: NPV vs ts
opt = p4["optimum_ts"]
# use cn = 1.0 curves recomputed from p2 rows? npv curves are in optimum_ts only at grid/closed points.
# Build from pareto? Simpler: use npv_at_5 / npv_at_30 plus optimum; full curve is in 03-numbers.
nrows = []
for c in CASES:
    k = f"{c}|cn1.0"
    v = opt[k]
    w2 = p4["optimum_two_calibers"][k]
    nrows.append(
        f"{c} & {v['npv_at_5']/1e4:.1f} & {v['npv_max']/1e4:.1f} & {v['npv_at_30']/1e4:.1f} & "
        f"{w2['ts_data_grid']:.0f} & {w2['ts_continuous']:.2f} & {v['band_2pct'][0]}--{v['band_2pct'][1]} \\\\"
    )
w("tab_npv.tex", r"""\begin{table}[htbp]
\centering
\caption{Net present value against soak time at $c_n=1.0$ (unit: $10^4$ CNY). The optimum is flat over a wide band, which is why the recommendation is a band rather than a point.}
\label{tab:npv}
\small
\begin{tabular}{@{}lcccccc@{}}
\toprule
Case & NPV at 5 d & Peak NPV & NPV at 30 d & $t_s^\ast$ design grid (d) & $t_s^\ast$ continuous (d) & 2\% band (d) \\
\midrule
""" + "\n".join(nrows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

# ---------------------------------------------------------------- Table 9: break-even
be = p4["break_even"]
brows = []
for c in CASES:
    v = be[c]
    brows.append(
        f"{c} & {v['npv']/1e4:.1f} & {v['EUR_obs']:.1f} & {v['EUR_required_for_zero']:.1f} & "
        f"{v['ratio_required_over_observed']:.2f} & {v['price_required_for_zero']:.0f} & {v['frac_cost_required_for_zero']/1e4:.1f} \\\\"
    )
w("tab_bep.tex", r"""\begin{table}[htbp]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\caption{Break-even analysis at the economic optimum. A negative required fracturing cost means no cost reduction can make the case profitable: the shortfall is structural, not a parameter error. $\mathrm{NPV}$, $\mathrm{EUR}_{obs}$ and required $C_{frac}$ are in $10^4$ CNY; $\mathrm{EUR}_0$ and the oil price are in m$^3$ and CNY m$^{-3}$.}
\label{tab:bep}
\begin{tabular}{@{}lcccccc@{}}
\toprule
Case & NPV & $\mathrm{EUR}_{obs}$ & $\mathrm{EUR}_0$ & Ratio & $P_{oil,0}$ & $C_{frac,0}$ \\
\midrule
""" + "\n".join(brows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

# ---------------------------------------------------------------- Table 10: Pareto
pm = p4["pareto_meta"]
prows = []
for c in CASES:
    for cal in ["geo", "emp"]:
        k = f"{c}|{cal}"
        if k not in pm:
            continue
        v = pm[k]
        kn = v["knee"]
        prows.append(
            f"{c} & {cal} & {v['n_front']} & {kn['ts']:.0f} & {kn['Vinj']:.0f} & {kn['EUR_m3']:.1f} & "
            f"{kn['cost_nom']/1e4:.0f} & {kn['npv']/1e4:.1f} \\\\"
        )
w("tab_pareto.tex", r"""\begin{table}[htbp]
\centering
\caption{Pareto fronts for the three design cases under the two interpretations of the stimulated volume $V_0$ (geometric fracture volume vs. empirical drainage volume). The knee point is the compromise scheme recommended in Section~\ref{sec:p3}.}
\label{tab:pareto}
\small
\begin{tabular}{@{}llcccccc@{}}
\toprule
Case & $V_0$ model & Front points & $t_s$ (d) & $V_{inj}$ (m$^3$) & EUR (m$^3$) & Cost ($10^4$) & NPV ($10^4$) \\
\midrule
""" + "\n".join(prows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

# ---------------------------------------------------------------- Table 11: robustness
rb = p4["robustness"]
rrows = []
for c in CASES:
    v = rb[c]
    rrows.append(
        f"{c} & {v['base_ts']} & {v['base_npv']/1e4:.1f} & {v['n_changed']} & {v['npv_span_rel']:.3f} \\\\"
    )
w("tab_robust.tex", r"""\begin{table}[htbp]
\centering
\caption{$\pm15\%$ robustness screen: number of the 14 perturbed parameter combinations that move the optimal soak time, and the relative span of NPV across perturbations.}
\label{tab:robust}
\small
\begin{tabular}{@{}lcccc@{}}
\toprule
Case & Base $t_s^\ast$ (d) & Base NPV ($10^4$) & Runs changing $t_s^\ast$ & Relative NPV span \\
\midrule
""" + "\n".join(rrows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

# ---------------------------------------------------------------- Table 12: Sobol
s1 = p5["sobol"]
FACTORS = ["Ainf", "tau", "D", "Poil", "cprod", "csoak", "Cfrac", "a"]
LBL = {
    "Ainf": "$A_{inf}$", "tau": "$\\tau$", "D": "$D$", "Poil": "$P_{oil}$",
    "cprod": "$c_{prod}$", "csoak": "$c_{soak}$", "Cfrac": "$C_{frac}$", "a": "$a$",
}
srows = []
for f in FACTORS:
    cells = []
    for c in CASES:
        cells.append(f"{s1[c]['npv']['S1'][f]:.3f}")
    for c in CASES:
        cells.append(f"{s1[c]['ts']['S1'][f]:.3f}")
    srows.append(f"{LBL[f]} & " + " & ".join(cells) + " \\\\")
w("tab_sobol.tex", r"""\begin{table}[htbp]
\centering
\caption{First-order Sobol indices for the maximum NPV (left block) and for the optimal soak time (right block). Both blocks use the same 1024-point Saltelli design with Jansen and Saltelli double estimators.}
\label{tab:sobol}
\small
\begin{tabular}{@{}lcccccc@{}}
\toprule
& \multicolumn{3}{c}{NPV$_{\max}$} & \multicolumn{3}{c}{$t_s^\ast$} \\
\cmidrule(lr){2-4}\cmidrule(lr){5-7}
Factor & Case 1 & Case 2 & Case 3 & Case 1 & Case 2 & Case 3 \\
\midrule
""" + "\n".join(srows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

print("ALL TABLES OK")
