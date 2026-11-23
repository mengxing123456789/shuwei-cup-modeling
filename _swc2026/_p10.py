p=r"E:\数学建模\_swc2026\SWC2026_A\main.tex"
s=open(p,encoding="utf-8").read().replace(r"\fontsize{12.2}{15}\selectfont"+"\n","")
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("reverted")
