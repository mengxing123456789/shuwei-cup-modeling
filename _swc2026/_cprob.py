import fitz,glob,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
fs=glob.glob(r"E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题\C题\*.pdf")
for f in fs:
    d=fitz.open(f); t="".join(p.get_text() for p in d)
    print("====",f.split("\\")[-1],"pages",len(d),"chars",len(t))
    print(t[:6000])
