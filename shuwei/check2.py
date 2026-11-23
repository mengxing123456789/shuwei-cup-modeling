# -*- coding: utf-8 -*-
import os, io, zipfile, subprocess, glob
from pypdf import PdfReader

ROOT = r"C:\Users\29900\Downloads\AsterLink"
TMP = r"E:\数学建模\shuwei\_tmp2022"

def probe(p):
    try:
        r = PdfReader(p)
        t = ""
        for pg in r.pages[:2]:
            t += pg.extract_text() or ""
        t = " ".join(t.split())
        return len(r.pages), len(t), t[:100]
    except Exception as e:
        return -1, 0, "ERR %s" % e

print("--- 2022 RAR ---")
rar = [f for f in glob.glob(os.path.join(ROOT, "*.rar"))][0]
os.makedirs(TMP, exist_ok=True)
p7 = r"C:\Users\29900\AppData\Local\Microsoft\WindowsApps\7z.exe"
subprocess.run([p7, "x", "-y", "-o" + TMP, rar], capture_output=True)
pdfs = glob.glob(os.path.join(TMP, "**", "*.pdf"), recursive=True)
txts = glob.glob(os.path.join(TMP, "**", "*.txt"), recursive=True)
xlss = glob.glob(os.path.join(TMP, "**", "*.xlsx"), recursive=True)
print("extracted pdf=%d txt=%d xlsx=%d" % (len(pdfs), len(txts), len(xlss)))
for p in pdfs:
    n, c, h = probe(p)
    print("  ", os.path.basename(p), n, "p", c, "chars |", h[:70])

print("--- 2024 nested problem PDFs ---")
z24 = [f for f in glob.glob(os.path.join(ROOT, "*Problem.zip"))][0]
z = zipfile.ZipFile(z24)
for info in z.infolist():
    if info.filename.lower().endswith(".zip"):
        nz = zipfile.ZipFile(io.BytesIO(z.read(info)))
        for i2 in nz.infolist():
            if i2.filename.lower().endswith(".pdf"):
                try:
                    nm = i2.filename
                    if not (i2.flag_bits & 0x800):
                        nm = nm.encode("cp437").decode("gbk", "replace")
                except Exception:
                    nm = i2.filename
                n, c, h = probe(io.BytesIO(nz.read(i2)))
                print("  ", nm.split("/")[-1], n, "p", c, "chars |", h[:70])