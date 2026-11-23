p=r"E:\数学建模\_swc2026\SWC2026_A\code\make_paper_figures.py"
s=open(p,encoding="utf-8").read()
s=s.replace('"font.size": 12','"font.size": 14.5').replace('"axes.titlesize": 12','"axes.titlesize": 14.5').replace('"axes.labelsize": 12','"axes.labelsize": 14.5').replace('"legend.fontsize": 9.5','"legend.fontsize": 11.5').replace('"xtick.labelsize": 10.5','"xtick.labelsize": 12.5').replace('"ytick.labelsize": 10.5','"ytick.labelsize": 12.5')
s=s.replace('fontsize=10)','fontsize=12)').replace('fontsize=10,','fontsize=12,').replace('fontsize=9)','fontsize=11)').replace('fontsize=9,','fontsize=11,')
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
