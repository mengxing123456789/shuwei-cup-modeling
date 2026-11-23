import glob,os
files=[r"E:\数学建模\_swc2026\SWC2026_A\main.tex"]+glob.glob(r"E:\数学建模\_swc2026\SWC2026_A\tables\*.tex")
pairs=[(r"p_{max}",r"p_{M}"),(r"p_{face}",r"p_{f}"),(r"c_{prod}",r"c_{p}"),(r"c_{soak}",r"c_{s}"),(r"c_{frac}",r"c_{F}"),(r"R_{num}",r"R_{n}")]
for f in files:
    s=open(f,encoding="utf-8").read(); o=s
    for a,b in pairs: s=s.replace(a,b)
    if s!=o: open(f,"w",encoding="utf-8",newline="\n").write(s); print("patched",os.path.basename(f))
