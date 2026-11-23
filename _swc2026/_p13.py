import glob
files=[r"E:\数学建模\_swc2026\SWC2026_A\main.tex"]+glob.glob(r"E:\数学建模\_swc2026\SWC2026_A\tables\*.tex")
pairs=[(r"C_{frac}",r"C_{F}"),(r"EUR_{obs}",r"EUR_{o}"),(r"P_{oil}",r"P_{o}")]
for f in files:
    s=open(f,encoding="utf-8").read(); o=s
    for a,b in pairs: s=s.replace(a,b)
    if s!=o: open(f,"w",encoding="utf-8",newline="\n").write(s); print("patched",f)
