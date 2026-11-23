p=r"E:\数学建模\_swc2026\SWC2026_A\main.tex"
s=open(p,encoding="utf-8").read()
s=s.replace(r"\renewcommand\tableofcontents{%"+"\n"+r"\thispagestyle{empty}%", r"\renewcommand\tableofcontents{%"+"\n"+r"\thispagestyle{fancy}%")
open(p,"w",encoding="utf-8",newline="\n").write(s)
f=r"E:\数学建模\_swc2026\SWC2026_A\code\make_paper_figures.py"
t=open(f,encoding="utf-8").read()
t=t.replace('"font.size": 14.5','"font.size": 16').replace('"axes.titlesize": 14.5','"axes.titlesize": 16').replace('"axes.labelsize": 14.5','"axes.labelsize": 16').replace('"legend.fontsize": 11.5','"legend.fontsize": 12.5').replace('"xtick.labelsize": 12.5','"xtick.labelsize": 13.5').replace('"ytick.labelsize": 12.5','"ytick.labelsize": 13.5')
t=t.replace('fontsize=12)','fontsize=13)').replace('fontsize=12,','fontsize=13,').replace('fontsize=11)','fontsize=12)').replace('fontsize=11,','fontsize=12,')
open(f,"w",encoding="utf-8",newline="\n").write(t)
print("ok")
