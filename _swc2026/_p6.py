p=r"E:\数学建模\_swc2026\SWC2026_A\main.tex"
s=open(p,encoding="utf-8").read()
if "DeclareMathSizes" not in s:
    s=s.replace(r"\begin{document}", r"\DeclareMathSizes{12}{12}{8.5}{6.5}"+"\n"+r"\begin{document}",1)
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
