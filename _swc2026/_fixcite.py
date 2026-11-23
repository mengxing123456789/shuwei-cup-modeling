import re
p=r"E:\数学建模\_swc2026\SWC2026_A\main.tex"
s=open(p,encoding="utf-8").read()
i=s.index(r"\begin{thebibliography}"); j=s.index(r"\end{thebibliography}")
bib=s[i:j]
lines=bib.split("\n")
out=[]
for ln in lines:
    if r"\bibitem" in ln and r"\emph{" in ln:
        if "Mathematics of Diffusion" in ln or "Introduction to the Bootstrap" in ln:
            ln=re.sub(r"(\\emph\{[^}]*\})", r"\1 [M]", ln, count=1)
        else:
            ln=re.sub(r"(\\emph\{)", r"[J] \1", ln, count=1)
    out.append(ln)
s=s[:i]+"\n".join(out)+s[j:]
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("done")
