import io

P = "code/make_appendix_k.py"
t = io.open(P, encoding="utf-8").read()

old = r'''lines.append(r"\begin{figure}[H]")
lines.append(r"\centering")
lines.append(r"\includegraphics[width=\linewidth]{figures/fig9_phase.png}")
lines.append(r"\caption{Phase diagram of the reservation. Rows are the service multiplier, columns")
lines.append(r"the residual quantile; the top row is the weighted on-time rate and the bottom row the")
lines.append(r"mean cost. The horizontal gradient is small and one-signed, the vertical gradient is")
lines.append(r"large: the service law moves the rate, the reservation only spends it.}")
lines.append(r"\label{fig:phase}")
lines.append(r"\end{figure}")
lines.append(r"\clearpage")'''

new = r'''lines.append(r"\clearpage")'''

if old not in t:
    raise SystemExit("figure block anchor missing in make_appendix_k.py")
t = t.replace(old, new)

# the in-text reference now points at the body figure, so drop the png from the manifest sources
old2 = '''        "figures/fig9_phase.png": sha(C / "figures" / "fig9_phase.png"),\n'''
if old2 in t:
    t = t.replace(old2, "")
    print("dropped fig9 from manifest sources")

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("generator patched: phase figure now lives only in the body")
