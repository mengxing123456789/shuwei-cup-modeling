import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

A = "tables/app_n.tex"
a = io.open(A, encoding="utf-8").read()

# pull the twoviews block back out of Appendix N
i = a.find(r"\label{fig:twoviews}")
if i < 0:
    raise SystemExit("twoviews not in app_n")
b = a.rfind(r"\begin{figure}", 0, i)
e = a.find(r"\end{figure}", i) + len(r"\end{figure}")
if "% numerals-ok: begin" in a[max(0, b - 30):b]:
    b = a.rfind("% numerals-ok: begin", 0, b)
if "% numerals-ok: end" in a[e:e + 30]:
    e = a.find("% numerals-ok: end", e) + len("% numerals-ok: end")
block = a[b:e]
a = a[:b] + a[e:]
io.open(A, "w", encoding="utf-8", newline="").write(a)
print("pulled twoviews out of app_n:", len(block), "chars")

# re-insert it after the segmentation table in the body
j = t.find(r"\label{tab:seg}")
k = t.find(r"\end{table}", j) + len(r"\end{table}")
t = t[:k] + "\n" + block + t[k:]
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("re-inserted twoviews into body after tab:seg")
