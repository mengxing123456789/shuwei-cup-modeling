# -*- coding: utf-8 -*-
"""Part B: sensitivity/evaluation/references/assumptions sections + page budgets."""
import sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pymupdf as fitz

DIR = r"E:\数学建模\_swc2026\award_corpus_2025"

def find_pages(doc, pats, start=0):
    out=[]
    for i in range(start, len(doc)):
        t = doc[i].get_text("text")
        for p in pats:
            if p.search(t):
                out.append((i, p.pattern)); break
    return out

targets = {
 "C1760": ("CSHUWEICUP2551760.pdf", [
    re.compile(r"Sensitivity|sensitivity"), re.compile(r"Strengths and Weakness"),
    re.compile(r"^References|References\b"), re.compile(r"Model Assumptions|Model assumptions"),
    re.compile(r"Conclusion"), re.compile(r"^Appendix", re.M)]),
 "C6711": ("CSHUWEICUP2556711.pdf", [
    re.compile(r"5\.Test the Models"), re.compile(r"6\. Sensitivity"), re.compile(r"Strengths and Weakness"),
    re.compile(r"^References", re.M), re.compile(r"Fundamental assumptions"), re.compile(r"8\.Conclusion|8\. Conclusion")]),
 "C6821": ("CSHUWEICUP2556821.pdf", [
    re.compile(r"sensitivity analysis", re.I), re.compile(r"Strengths and Weakness"),
    re.compile(r"^References", re.M), re.compile(r"Fundamental assumptions"), re.compile(r"6\.Conclusion")]),
 "C9001": ("CSHUWEICUP2559001.pdf", [
    re.compile(r"[Ss]ensitivity"), re.compile(r"Strengths and Weakness"),
    re.compile(r"^References", re.M), re.compile(r"Fundamental assumptions")]),
 "C1635": ("CSHUWEICUP2561635.pdf", [
    re.compile(r"[Ss]ensitivity"), re.compile(r"Strengths and Weakness"),
    re.compile(r"^References", re.M), re.compile(r"Model Assumptions"),
    re.compile(r"Conclusion"), re.compile(r"^Appendix", re.M)]),
}

for key,(fn,pats) in targets.items():
    doc = fitz.open(os.path.join(DIR, fn))
    print("#"*90)
    print(f"###### {key} {fn} total={len(doc)}")
    hits = {}
    for i in range(len(doc)):
        t = doc[i].get_text("text")
        for p in pats:
            if p.search(t) and p.pattern not in hits:
                hits[p.pattern] = i
    print("first-hit pages:", {k: v+1 for k,v in hits.items()})
    # dump: assumptions page, sensitivity, strengths/weakness, references
    want = []
    for pat, pg in hits.items():
        if ("sensitivity" in pat.lower() or "Strengths" in pat or "References" in pat
            or "assumptions" in pat or "Assumptions" in pat or "Conclusion" in pat):
            want.append(pg)
    want = sorted(set(want))
    for pg in want[:8]:
        t = doc[pg].get_text("text")
        t = re.sub(r"\n{3,}", "\n\n", t)
        print(f"----- [{key}] p{pg+1} -----")
        print(t[:2800])
    doc.close()
print("END-PART-B")
