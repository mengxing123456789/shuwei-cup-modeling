p=r"E:\数学建模\_swc2026\SWC2026_A\code\make_paper_figures.py"
s=open(p,encoding="utf-8").read()
s=s.replace('fontsize=7)','fontsize=10)').replace('fontsize=7,','fontsize=10,')
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
