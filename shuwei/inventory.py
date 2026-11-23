# -*- coding: utf-8 -*-
import os, sys, zipfile, json, io
from pypdf import PdfReader

ROOT = r"C:\Users\29900\Downloads\AsterLink"

def fixname(info):
    n = info.filename
    if info.flag_bits & 0x800:
        return n
    try:
        return n.encode('cp437').decode('gbk')
    except Exception:
        try:
            return n.encode('cp437').decode('utf-8')
        except Exception:
            return n

def probe_pdf(fp):
    try:
        r = PdfReader(fp)
        n = len(r.pages)
        txt = ""
        for p in r.pages[:2]:
            try:
                txt += (p.extract_text() or "")
            except Exception:
                pass
        txt = " ".join(txt.split())
        return {"pages": n, "chars": len(txt), "head": txt[:90]}
    except Exception as e:
        return {"pages": -1, "chars": 0, "head": "ERR: %s" % e}

res = {}
for f in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, f)
    if not os.path.isfile(p):
        continue
    ext = os.path.splitext(f)[1].lower()
    if ext == ".pdf":
        res.setdefault("__loose_pdf__", []).append({"name": f, **probe_pdf(p)})
        continue
    if ext != ".zip":
        continue
    try:
        z = zipfile.ZipFile(p)
    except Exception as e:
        res[f] = {"error": str(e)}
        continue
    items = []
    for info in z.infolist():
        if info.is_dir():
            continue
        items.append({"name": fixname(info), "size": info.file_size})
    pdfs = [i for i in items if i["name"].lower().endswith(".pdf")]
    docx = [i for i in items if i["name"].lower().endswith((".docx", ".doc"))]
    others = [i for i in items if not i["name"].lower().endswith((".pdf", ".docx", ".doc"))]
    samples = []
    for info in z.infolist():
        if info.is_dir():
            continue
        nm = fixname(info)
        if not nm.lower().endswith(".pdf"):
            continue
        if len(samples) >= 3:
            break
        try:
            with z.open(info) as fh:
                data = io.BytesIO(fh.read())
            r = probe_pdf(data)
        except Exception as e:
            r = {"pages": -1, "chars": 0, "head": "ERR: %s" % e}
        samples.append({"name": nm.split("\\")[-1].split("/")[-1], **r})
    res[f] = {"n_pdf": len(pdfs), "n_doc": len(docx), "n_other": len(others),
              "pdf_names": [x["name"] for x in pdfs][:60],
              "doc_names": [x["name"] for x in docx][:20],
              "samples": samples}
    # nested zip detection
    for info in z.infolist():
        if info.is_dir():
            continue
        nm = fixname(info)
        if nm.lower().endswith(".zip"):
            try:
                nz = zipfile.ZipFile(io.BytesIO(z.read(info)))
                nin = []
                for i2 in nz.infolist():
                    if not i2.is_dir():
                        nin.append(fixname(i2))
                res[f].setdefault("nested", []).append({"zip": nm, "entries": nin[:40], "count": len(nin)})
            except Exception as e:
                res[f].setdefault("nested", []).append({"zip": nm, "error": str(e)})

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)
print("WROTE", out)
for k, v in res.items():
    if k == "__loose_pdf__":
        print("[loose pdfs]", len(v))
        for x in v:
            print("   ", x["name"], x["pages"], "p", x["chars"], "chars")
        continue
    print("==", k)
    if "error" in v:
        print("   ERR", v["error"]); continue
    print("   pdf=%d doc=%d other=%d" % (v["n_pdf"], v["n_doc"], v["n_other"]))
    for s in v["samples"]:
        print("   sample:", s["name"], s["pages"], "p", s["chars"], "chars |", s["head"][:60])
    for ne in v.get("nested", []):
        print("   nested:", ne.get("zip"), ne.get("count"), ne.get("error", ""))
        for e in ne.get("entries", [])[:12]:
            print("      -", e)