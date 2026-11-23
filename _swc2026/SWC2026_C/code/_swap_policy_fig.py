import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()
A = "tables/app_n.tex"
a = io.open(A, encoding="utf-8").read()

# --- 1) take the two-panel figure back out of the body ---
i = t.find(r"\label{fig:twoviews}")
if i >= 0:
    b = t.rfind(r"\begin{figure}", 0, i)
    e = t.find(r"\end{figure}", i) + len(r"\end{figure}")
    if "% numerals-ok: begin" in t[max(0, b - 30):b]:
        b = t.rfind("% numerals-ok: begin", 0, b)
    if "% numerals-ok: end" in t[e:e + 30]:
        e = t.find("% numerals-ok: end", e) + len("% numerals-ok: end")
    block = t[b:e]
    t = t[:b] + t[e:]
    io.open(P, "w", encoding="utf-8", newline="").write(t)
    if r"\label{fig:twoviews}" not in a:
        a = a.rstrip() + "\n\n" + block + "\n"
        io.open(A, "w", encoding="utf-8", newline="").write(a)
    print("twoviews returned to Appendix N")

# --- 2) put the compact policy figure into the body instead ---
if r"\label{fig:policy}" not in t:
    anchor = (r"The full table, one row per policy and one column per measure, is "
              r"Table~\ref{tab:p3score} in Appendix~\ref{app:ablation}.")
    if anchor not in t:
        raise SystemExit("scorecard pointer missing")
    fig = r"""

% numerals-ok: begin
\begin{figure}[htbp]
\centering
\includegraphics[width=0.74\linewidth]{figures/fig6_p3_policy.png}
\caption{Corrected protocol, weighted on-time rate of the incumbent policies on the same
seeds. Each group holds S1, S2 and S3; the dashed line is the statement's 0.50 floor. The
scheduling rule moves the two informative cases by more than twenty points.}
\label{fig:policy}
\end{figure}
% numerals-ok: end"""
    t = t.replace(anchor, anchor + fig)
    io.open(P, "w", encoding="utf-8", newline="").write(t)
    print("policy figure inserted into body")

# --- 3) the same figure must leave Appendix K to avoid a duplicate label ---
k = io.open("tables/app_k.tex", encoding="utf-8").read()
if r"\label{fig:policy}" in k:
    i2 = k.find(r"\label{fig:policy}")
    b2 = k.rfind(r"\begin{figure}", 0, i2)
    e2 = k.find(r"\end{figure}", i2) + len(r"\end{figure}")
    k = k[:b2] + k[e2:]
    io.open("tables/app_k.tex", "w", encoding="utf-8", newline="").write(k)
    print("policy figure removed from Appendix K")

g = io.open("code/make_appendix_k.py", encoding="utf-8").read()
blk = '''lines.append(r"\\begin{figure}[H]")
lines.append(r"\\centering")
lines.append(r"\\includegraphics[width=0.86\\linewidth]{figures/fig6_p3_policy.png}")
lines.append(r"\\caption{Corrected protocol, weighted on-time rate for the incumbent policies. The three")
lines.append(r"bars in each group are S1, S2 and S3; the dashed line is the statement's 0.50 floor. The")
lines.append(r"rule moves the two informative cases by more than twenty points; the reservation does not.}")
lines.append(r"\\label{fig:policy}")
lines.append(r"\\end{figure}")
'''
if blk in g:
    g = g.replace(blk, "")
    g = g.replace('        "figures/fig6_p3_policy.png": sha(C / "figures" / "fig6_p3_policy.png"),\n', "")
    io.open("code/make_appendix_k.py", "w", encoding="utf-8", newline="").write(g)
    print("generator patched to drop the policy figure")
else:
    print("generator block MISS (check manually)")
