import fitz, os
doc = fitz.open("main.pdf")
for i in [0,1,2,8,21]:
    p = doc[i]
    pix = p.get_pixmap(dpi=110)
    out = f"../02_figures/_page{i+1:02d}.png"
    pix.save(out)
    print(out, p.rect, len(p.get_text()))
