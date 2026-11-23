import sys
import fitz

doc = fitz.open(sys.argv[1] if len(sys.argv) > 1 else "main.pdf")
lo = int(sys.argv[2]) if len(sys.argv) > 2 else 1
hi = int(sys.argv[3]) if len(sys.argv) > 3 else doc.page_count
for p in range(lo - 1, min(hi, doc.page_count)):
    page = doc[p]
    blocks = [b for b in page.get_text("blocks") if b[4].strip()]
    maxy = max((b[3] for b in blocks), default=0.0)
    nimg = len(page.get_images(full=True))
    print("%3d  maxy=%6.1f  imgs=%d  h=%.1f" % (p + 1, maxy, nimg, page.rect.height))
