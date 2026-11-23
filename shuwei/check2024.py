# -*- coding: utf-8 -*-
import os, io, zipfile, glob
from pypdf import PdfReader

ROOT = r"C:\Users\29900\Downloads\AsterLink"
z24 = [f for f in glob.glob(os.path.join(ROOT, "*.zip")) if os.path.basename(f).startswith("2024")][0]
print("outer:", os.path.basename(z24))
z = zipfile.ZipFile(z24)

def dec(info):
    n = info.filename
    if info.flag_bits & 0x800:
        return n
    return n.encode("cp437").decode("gbk", "replace")

for info in z.infolist():
    if dec(info).lower().endswith(".zip") and "Problem" in dec(info) and "LaTeX" not in dec(info):
        nz = zipfile.ZipFile(io.BytesIO(z.read(info)))
        print("inner:", dec(info))
        for i2 in nz.infolist():
            nm = i2.filename
            if not (i2.flag_bits & 0x800):
                nm = nm.encode("cp437").decode("gbk", "replace")
            if nm.lower().endswith(".pdf"):
                r = PdfReader(io.BytesIO(nz.read(i2)))
                t = " ".join(((r.pages[0].extract_text() or "")).split())
                print("   %-40s %2d p  %s" % (nm.split("/")[-1][:40], len(r.pages), t[:70]))
        print("   entries:", len(nz.infolist()))