import fitz,io,sys,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
p=r"E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题\C题\2026_“ShuWei Cup”C_Problem.pdf"
t="".join(x.get_text() for x in fitz.open(p))
i=t.find("Problem 2.")
print(t[i:i+2600].replace("\n"," "))
