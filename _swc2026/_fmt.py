import fitz,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
p=r"E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）论文格式规范.pdf"
d=fitz.open(p); print("pages",len(d))
t="".join(x.get_text() for x in d); print("chars",len(t)); print(t[:3000])
