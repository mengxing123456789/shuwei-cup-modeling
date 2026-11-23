# -*- coding: utf-8 -*-
"""Scan award-paper PDFs: structure digest per paper."""
import sys, re, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import fitz

DIR = r"E:\数学建模\_swc2026\award_corpus_2025"
C_PDFS = ["CSHUWEICUP2551760.pdf","CSHUWEICUP2556711.pdf","CSHUWEICUP2556821.pdf",
          "CSHUWEICUP2559001.pdf","CSHUWEICUP2561635.pdf"]

HEADING_PAT = [
    re.compile(r"^摘\s*要"), re.compile(r"^Abstract", re.I), re.compile(r"^关键词|^Key\s?words", re.I),
    re.compile(r"^目\s*录|^Contents", re.I),
    re.compile(r"^[一二三四五六七八九十]+[、\.．]\s*\S+"),
    re.compile(r"^\d+(\.\d+){0,2}[、\.\s]\s*\S+"),
    re.compile(r"^第\s*[一二三四五六七八九十\d]+\s*[章节部分]\s*\S*"),
    re.compile(r"^问题[一二三四五六\d]|^Question\s*\d", re.I),
    re.compile(r"^附录|^Appendix|参考文献|^References", re.I),
]
FIG_PAT = re.compile(r"图\s*\d+[-\.\d]*|Figure\s*\d+", re.I)
TAB_PAT = re.compile(r"表\s*\d+[-\.\d]*|Table\s*\d+", re.I)
PAGEOF_PAT = re.compile(r"Page\s+(\d+)\s+of\s+(\d+)")

for name in C_PDFS:
    path = os.path.join(DIR, name)
    doc = fitz.open(path)
    n = len(doc)
    texts = []
    for i in range(n):
        t = doc[i].get_text("text")
        texts.append(t)
    alltext = "\n".join(texts)
    print("="*90)
    print(f"### {name}  pages={n}")
    # page-of-N footer sample
    po = []
    for i,t in enumerate(texts):
        m = PAGEOF_PAT.search(t)
        if m: po.append((i+1, m.group(1), m.group(2)))
    if po:
        print("PageOfN samples (pdfpage, n, N):", po[:3], "...", po[-3:] if len(po)>3 else "")
    # headings collected
    print("--- HEADING LINES ---")
    seen=set()
    for i,t in enumerate(texts):
        for ln in t.splitlines():
            s = ln.strip()
            if 3 < len(s) < 60:
                for p in HEADING_PAT:
                    if p.match(s):
                        key=(i//2, s)
                        if s not in seen:
                            seen.add(s)
                            print(f"  p{i+1:03d} | {s[:58]}")
                        break
    figs = set(FIG_PAT.findall(alltext)); tabs = set(TAB_PAT.findall(alltext))
    print(f"FIG captions unique={len(figs)}  TAB captions unique={len(tabs)}")
    # keyword counts
    kws = ["灵敏度","敏感性","蒙特卡洛","Bootstrap","交叉验证","残差","缺失","插值","可信","不确定",
           "聚类","随机森林","XGBoost","LSTM","回归","TOPSIS","熵权","层次分析","遗传","模拟退火",
           "粒子群","灰色","马尔可夫","鲁棒","稳健","优缺点","模型评价","局限","改进","优度","RMSE","MAE","R²","拟合"]
    cnt = {k: alltext.count(k) for k in kws if alltext.count(k)>0}
    print("KW counts:", json.dumps(cnt, ensure_ascii=False))
    doc.close()
print("END")
