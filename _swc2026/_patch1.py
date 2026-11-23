import io,re
p=r"E:\数学建模\_swc2026\SWC2026_A\code\make_paper_tables.py"
s=open(p,encoding="utf-8").read()
start=s.index("PI_DEF = {")
end=s.index("# ---------------------------------------------------------------- Table 2")
new = r'''PI_DEF = {
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

'''
s = s[:start] + new + s[end:]
# tighten MEAN texts
s = s.replace('"Pi1": "Pressure diffusion across half block width in 60 d"','"Pi1": "Pressure diffusion in 60 d"')
s = s.replace('"Pi2": "Biot coupling strength (pore pressure to skeleton strain)"','"Pi2": "Biot coupling strength"')
s = s.replace('"Pi3": "Stress-sensitive permeability gain, $k/k_0=e^{\\\\Pi_3}$"','"Pi3": "Stress-permeability gain"')
s = s.replace('"Pi4": "Pore compressibility share of total storage"','"Pi4": "Pore compressibility share"')
s = s.replace('"Pi5": "CO$_2$ molecular diffusion Fourier number"','"Pi5": "CO$_2$ diffusion Fourier no."')
s = s.replace('"Pi6": "Nanoparticle retardation factor $R_n$"','"Pi6": "Nanoparticle retardation"')
s = s.replace('"Pi7": "Damage curve steepness $\\\\times$ threshold"','"Pi7": "Damage steepness $\\\\times$ threshold"')
s = s.replace('"Pi8": "Stress concentration at fracture face / damage threshold"','"Pi8": "Face stress / damage threshold"')
s = s.replace('"Pi9": "Injectivity: formation intake vs pump rate"','"Pi9": "Injectivity vs pump rate"')
s = s.replace('"Pi10": "Soak time as fraction of production period"','"Pi10": "Soak / production time"')
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("patched pi block")
