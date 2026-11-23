import pymupdf
d=pymupdf.open(r"E:\数学建模\_swc2026\SWC2026_A\main.pdf")
print("pages",d.page_count)
for i in [1,6,7,8,13,14,15,16,23]:
    d[i].get_pixmap(dpi=90).save(rf"E:\数学建模\_swc2026\_v{i+1}.png")
print("ok")
