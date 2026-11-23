import io, re

P = r"SWC2026_C_ALT_BACKUP\main.tex"
t = io.open(P, encoding="utf-8").read()

def sec(a, b):
    i = t.find(a); j = t.find(b)
    if i < 0 or j < 0:
        print("MISSING", a, b); return
    print("\n" + "=" * 70 + "\n" + a)
    print(t[i:j])

sec(r"\subsection{Data Insight}", r"\section{Question 2:")
