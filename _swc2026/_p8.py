p=r"E:\数学建模\_swc2026\SWC2026_A\main.tex"
s=open(p,encoding="utf-8").read()
s=s.replace(r"\DeclareMathSizes{12}{12}{8.5}{6.5}", r"\AtBeginDocument{\DeclareMathSizes{12}{12}{9}{7}\DeclareMathSizes{10}{10}{8}{6}\DeclareMathSizes{11}{11}{8.5}{6.5}}")
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
