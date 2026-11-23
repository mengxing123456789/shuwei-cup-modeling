p=r"E:\数学建模\_swc2026\SWC2026_A\tables\tab_bep.tex"
s=open(p,encoding="utf-8").read()
s=s.replace(r"\mathrm{EUR}_{obs}",r"\mathrm{EUR}_{o}").replace(r"P_{oil,0}",r"P_{o,0}").replace(r"C_{frac,0}",r"C_{F,0}")
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
