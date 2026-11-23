import io, os

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

# --- 1) remove the two-panel figure from the body, move it to Appendix N ---
i = t.find(r"\label{fig:twoviews}")
if i < 0:
    raise SystemExit("twoviews label missing")
b = t.rfind(r"\begin{figure}", 0, i)
e = t.find(r"\end{figure}", i) + len(r"\end{figure}")
if b < 0 or e < len(r"\end{figure}"):
    raise SystemExit("twoviews bounds not found")
# swallow the numerals-ok guard lines around it
if "% numerals-ok: begin" in t[b-30:b]:
    b = t.rfind("% numerals-ok: begin", 0, b)
if "% numerals-ok: end" in t[e:e+30]:
    e = t.find("% numerals-ok: end", e) + len("% numerals-ok: end")
block = t[b:e]
t = t[:b] + t[e:]
print("removed twoviews from body:", len(block), "chars")

# --- 2) put the phase figure back into the body where the scorecard pointer sits ---
anchor = (r"The full table, one row per policy and one column per measure, is "
          r"Table~\ref{tab:p3score} in Appendix~\ref{app:ablation}.")
if anchor not in t:
    raise SystemExit("scorecard pointer missing")
if r"\label{fig:phase}" in t:
    raise SystemExit("phase already in body")
phase = io.open("_fig_phase_block.tex", encoding="utf-8").read()
t = t.replace(anchor, anchor + "\n" + phase)
print("re-inserted phase figure into body")

io.open(P, "w", encoding="utf-8", newline="").write(t)

# --- 3) append the two-panel figure to Appendix N ---
A = "tables/app_n.tex"
a = io.open(A, encoding="utf-8").read()
if r"\label{fig:twoviews}" not in a:
    a = a.rstrip() + "\n\n" + block + "\n"
    io.open(A, "w", encoding="utf-8", newline="").write(a)
    print("appended twoviews to app_n")
else:
    print("twoviews already in app_n")
