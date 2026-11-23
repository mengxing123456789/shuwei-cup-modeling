import fitz
p=r"E:\数学建模\_swc2026\SWC2026_A\main.pdf"
d=fitz.open(p)
print("pages",d.page_count)
for i in [0,1,4,9,15,24]:
    if i<d.page_count:
        pg=d[i]; pix=pg.get_pixmap(dpi=110)
        pix.save(rf"E:\数学建模\_swc2026\_pg{i+1}.png")
        print("saved",i+1)
