p=r"E:\数学建模\_swc2026\SWC2026_A\code\make_paper_tables.py"
s=open(p,encoding="utf-8").read()
s=s.replace('''w("tab_bep.tex", r"""\\begin{table}[htbp]
\\centering
\\caption{Break-even analysis at the economic optimum. A negative required fracturing cost means no cost reduction can make the case profitable: the shortfall is structural, not a parameter error.}
\\label{tab:bep}
\\small
\\begin{tabular}{@{}lcccccc@{}}
\\toprule
Case & NPV ($10^4$) & EUR observed (m$^3$) & EUR for zero NPV & Ratio & Oil price for zero NPV & Required $C_{frac}$ ($10^4$) \\\\''','''w("tab_bep.tex", r"""\\begin{table}[htbp]
\\centering
\\scriptsize
\\setlength{\\tabcolsep}{3pt}
\\caption{Break-even analysis at the economic optimum. A negative required fracturing cost means no cost reduction can make the case profitable: the shortfall is structural, not a parameter error. $\\mathrm{NPV}$, $\\mathrm{EUR}_{obs}$ and required $C_{frac}$ are in $10^4$ CNY; $\\mathrm{EUR}_0$ and the oil price are in m$^3$ and CNY m$^{-3}$.}
\\label{tab:bep}
\\begin{tabular}{@{}lcccccc@{}}
\\toprule
Case & NPV & $\\mathrm{EUR}_{obs}$ & $\\mathrm{EUR}_0$ & Ratio & $P_{oil,0}$ & $C_{frac,0}$ \\\\''')
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
