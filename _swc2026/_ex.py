import fitz, io, sys, os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题"
files=[("A",os.path.join(base,"A题","2026_“ShuWei Cup”A_Problem.pdf")),
       ("B",os.path.join(base,"B题","2026_“ShuWei Cup”B_Problem.pdf")),
       ("C",os.path.join(base,"C题","2026_“ShuWei Cup”C_Problem.pdf")),
       ("D",os.path.join(base,"D题","2026_“ShuWei Cup”D_Problem.pdf"))]
for k,p in files:
    d=fitz.open(p); t="".join(x.get_text() for x in d)
    print("=====",k,"pages",len(d),"chars",len(t))
    open(rf"E:\数学建模\_swc2026\_prob_{k}.txt","w",encoding="utf-8").write(t)
print("done")
