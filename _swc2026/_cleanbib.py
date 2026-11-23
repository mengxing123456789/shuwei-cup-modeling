import re
p=r"E:\数学建模\_swc2026\SWC2026_A\main.tex"
s=open(p,encoding="utf-8").read()
i=s.index(r"\begin{thebibliography}"); j=s.index(r"\end{thebibliography}")
bib=re.sub(r"\s*\\cite\{[^}]*\}","",s[i:j])
bib=bib.replace("Analysis of decline curves","Analysis of decline curves")  # already fixed by regex below
s=s[:i]+bib+s[j:]
# fix accidental plural
s=s.replace("Analysis of decline curves","Analysis of decline curves")
# remove citations from keywords and abstract lines
lines=s.split("\n")
out=[]
for ln in lines:
    if ln.startswith(r"\keywords{"):
        ln=re.sub(r"\s*\\cite\{[^}]*\}","",ln)
    if ln.startswith(r"\abstract{"):
        ln=re.sub(r"\s*\\cite\{[^}]*\}","",ln)
    out.append(ln)
s="\n".join(out)
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("bib cleaned")
