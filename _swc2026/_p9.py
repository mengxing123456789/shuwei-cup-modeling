p=r"E:\数学建模\_swc2026\SWC2026_A\main.tex"
s=open(p,encoding="utf-8").read()
s=s.replace(r"\begin{document}", r"\begin{document}"+"\n"+r"\fontsize{12.2}{15}\selectfont",1)
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
