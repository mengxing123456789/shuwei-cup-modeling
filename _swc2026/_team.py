import fitz,io,sys,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
p=r"E:\数学建模\_swc2026\SWC2026_A\main.pdf"
d=fitz.open(p)
t=d[0].get_text(); print("=== PAGE1 ==="); print(t[:900])
print("header p3:", repr(d[2].get_text()[:90]))
for f in [r"E:\数学建模\_swc2026\SWC2026_C\out\00-problem.md"]:
    s=open(f,encoding="utf-8").read()
    print("C00 team mentions:", set(re.findall(r"[A-Z]{0,2}SWBMCM\d+", s)))
