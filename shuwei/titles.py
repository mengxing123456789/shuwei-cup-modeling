# -*- coding: utf-8 -*-
import os, io, zipfile, glob, re
from pypdf import PdfReader

ROOT = r"C:\Users\29900\Downloads\AsterLink"

def dec(info):
    n = info.filename
    if info.flag_bits & 0x800:
        return n
    return n.encode("cp437").decode("gbk", "replace")

def title_from(pdf_bytes_or_path):
    r = PdfReader(pdf_bytes_or_path)
    txt = "\n".join((p.extract_text() or "") for p in r.pages[:2])
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    # 找 Summary 之后的标题行（英文题目通常为较长一行）
    cand = []
    for l in lines:
        if re.search(r"(Problem|Question) Chosen", l):
            continue
        if len(l) > 25 and re.search(r"[A-Za-z]{3,}", l):
            cand.append(l)
    return len(r.pages), (cand[1] if len(cand) > 1 else (cand[0] if cand else ""))

for name in ["2023", "2025"]:
    zp = [f for f in glob.glob(os.path.join(ROOT, "*.zip")) if os.path.basename(f).startswith(name) and "优秀论文" in os.path.basename(f)]
    zp = [f for f in zp if "(1)" not in os.path.basename(f)]
    if not zp:
        continue
    z = zipfile.ZipFile(zp[0])
    print("=== %s ===" % os.path.basename(zp[0]))
    for info in z.infolist():
        nm = dec(info)
        if not nm.lower().endswith(".pdf"):
            continue
        try:
            n, t = title_from(io.BytesIO(z.read(info)))
            print("  %-28s %2dp  %s" % (nm.split("/")[-1][:28], n, t[:95]))
        except Exception as e:
            print("  %-28s ERR %s" % (nm.split("/")[-1][:28], e))