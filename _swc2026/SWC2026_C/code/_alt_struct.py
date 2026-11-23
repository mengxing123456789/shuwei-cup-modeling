import io, re, sys

P = r"SWC2026_C_ALT_BACKUP\main.tex"
t = io.open(P, encoding="utf-8").read()
print("bytes", len(t.encode()), "lines", t.count("\n") + 1)
pat = re.compile(r"^\\(section|subsection|subsubsection)\*?\{([^}]*)\}", re.M)
for m in pat.finditer(t):
    print(m.start(), m.group(1), "|", m.group(2))

print("--- counts ---")
for k in [r"\begin{equation}", r"\begin{align}", r"\begin{table}", r"\begin{figure}", r"\includegraphics", r"\begin{itemize}", r"\begin{enumerate}", r"\begin{algorithm}"]:
    print(k, t.count(k))
print("words", len(re.findall(r"[A-Za-z][A-Za-z'-]+", t)))
