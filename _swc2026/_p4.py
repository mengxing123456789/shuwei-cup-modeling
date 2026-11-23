p=r"E:\数学建模\_swc2026\SWC2026_A\swmcmthesis.cls"
s=open(p,encoding="utf-8").read()
s=s.replace(r"\thispagestyle{empty}",r"\thispagestyle{fancy}")
open(p,"w",encoding="utf-8",newline="\n").write(s)
q=r"E:\数学建模\_swc2026\SWC2026_A\main.tex"
t=open(q,encoding="utf-8").read()
t=t.replace("Oxford University Press","Clarendon Press")
open(q,"w",encoding="utf-8",newline="\n").write(t)
v=r"E:\数学建模\_swc2026\SWC2026_A\code\verify_numbers.py"
u=open(v,encoding="utf-8").read()
u=u.replace('print(f"{n_pass} passed, {len(fails)} failed")','print(f"{n_pass} claims passed, {len(fails)} failed")')
open(v,"w",encoding="utf-8",newline="\n").write(u)
print("patched cls/tex/verify")
