import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()
A = "tables/app_n.tex"
a = io.open(A, encoding="utf-8").read()

i = t.find(r"\label{fig:twoviews}")
if i < 0:
    raise SystemExit("twoviews not in body")
b = t.rfind(r"\begin{figure}", 0, i)
e = t.find(r"\end{figure}", i) + len(r"\end{figure}")
if "% numerals-ok: begin" in t[max(0, b - 30):b]:
    b = t.rfind("% numerals-ok: begin", 0, b)
if "% numerals-ok: end" in t[e:e + 30]:
    e = t.find("% numerals-ok: end", e) + len("% numerals-ok: end")
block = t[b:e]
t = t[:b] + t[e:]
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("removed twoviews from body")

if r"\label{fig:twoviews}" not in a:
    a = a.rstrip() + "\n\n" + block + "\n"
    io.open(A, "w", encoding="utf-8", newline="").write(a)
    print("appended twoviews to app_n")
else:
    print("twoviews already in app_n")

print("phase in body:", t.count(r"\label{fig:phase}"))
