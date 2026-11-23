import glob
files=[r"E:\数学建模\_swc2026\SWC2026_A\main.tex"]+glob.glob(r"E:\数学建模\_swc2026\SWC2026_A\tables\*.tex")
pairs=[(r"T_{prod}",r"T_{p}"),(r"A_{face}",r"A_{f}"),(r"t_{soak}",r"t_{s}")]
for f in files:
    s=open(f,encoding="utf-8").read(); o=s
    for a,b in pairs: s=s.replace(a,b)
    if s!=o: open(f,"w",encoding="utf-8",newline="\n").write(s); print("patched",f)
