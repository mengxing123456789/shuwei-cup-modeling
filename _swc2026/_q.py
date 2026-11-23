import fitz
d=fitz.open(r"E:\数学建模\_swc2026\SWC2026_A\main.pdf")
print("pages",d.page_count)
for i in [0,1,2,3]:
    d[i].get_pixmap(dpi=100).save(rf"E:\数学建模\_swc2026\_q{i+1}.png")
