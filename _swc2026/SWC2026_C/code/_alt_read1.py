import io, re

P = r"SWC2026_C_ALT_BACKUP\main.tex"
t = io.open(P, encoding="utf-8").read()
print("display math styles:")
for k in [r"\[", r"\]", r"$$", r"\begin{equation*}", r"\begin{gather}", r"\begin{aligned}", r"\begin{cases}"]:
    print(" ", k, t.count(k))

def sec(a, b=None):
    i = t.find(a)
    if i < 0:
        print("MISSING", a); return
    j = t.find(b) if b else len(t)
    if b and j < 0:
        print("MISSING b", b); return
    print("\n" + "=" * 70)
    print(t[i:j])

sec(r"\section{A Unified View: Events, Observability, Decisions}", r"\section{Assumptions and Justifications}")
