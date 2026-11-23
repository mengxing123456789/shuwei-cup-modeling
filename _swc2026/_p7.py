p=r"E:\数学建模\_swc2026\SWC2026_A\main.tex"
s=open(p,encoding="utf-8").read()
s=s.replace(r"\tableofcontents"+"\n"+r"\newpage", r"\tableofcontents"+"\n"+r"\thispagestyle{fancy}"+"\n"+r"\newpage",1)
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
