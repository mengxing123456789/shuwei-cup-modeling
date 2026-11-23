import io, re

P = r"SWC2026_C_ALT_BACKUP\main.tex"
t = io.open(P, encoding="utf-8").read()

def sec(a, b, out):
    i = t.find(a); j = t.find(b)
    if i < 0 or j < 0:
        print("MISSING", a, b); return
    io.open(out, "w", encoding="utf-8", newline="").write(t[i:j])
    print(out, "ok", len(t[i:j]))

sec(r"\section{Question 2:", r"\section{Question 3:", r"_alt_q2.txt")
sec(r"\section{Question 3:", r"\section{Sensitivity Analysis and Error Analysis}", r"_alt_q3.txt")
sec(r"\section{Sensitivity Analysis and Error Analysis}", r"\section{Appendix A: Code}", r"_alt_tail.txt")
