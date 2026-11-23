p=r"E:\数学建模\_swc2026\SWC2026_A\code\make_paper_figures.py"
s=open(p,encoding="utf-8").read()
s=s.replace('"font.size": 9','"font.size": 12').replace('"axes.titlesize": 9','"axes.titlesize": 12').replace('"axes.labelsize": 9','"axes.labelsize": 12').replace('"legend.fontsize": 7.5','"legend.fontsize": 9.5').replace('"xtick.labelsize": 8','"xtick.labelsize": 10.5').replace('"ytick.labelsize": 8','"ytick.labelsize": 10.5')
for old in ['6.2','6.5','6.6']:
    s=s.replace('fontsize='+old,'fontsize=9')
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("patched")
