import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()
A = "tables/app_n.tex"
a = io.open(A, encoding="utf-8").read()

# --- 1) pull twoviews out of Appendix N and put it back in the body ---
i = a.find(r"\label{fig:twoviews}")
if i >= 0:
    b = a.rfind(r"\begin{figure}", 0, i)
    e = a.find(r"\end{figure}", i) + len(r"\end{figure}")
    if "% numerals-ok: begin" in a[max(0, b - 30):b]:
        b = a.rfind("% numerals-ok: begin", 0, b)
    if "% numerals-ok: end" in a[e:e + 30]:
        e = a.find("% numerals-ok: end", e) + len("% numerals-ok: end")
    block = a[b:e]
    a = a[:b] + a[e:]
    io.open(A, "w", encoding="utf-8", newline="").write(a)
    if r"\label{fig:twoviews}" not in t:
        j = t.find(r"\label{tab:seg}")
        k = t.find(r"\end{table}", j) + len(r"\end{table}")
        t = t[:k] + "\n" + block + t[k:]
    print("twoviews moved into body")

# --- 2) free space: compress three verbose passages in the results sections ---
cuts = []

cuts.append((
r"""The cause is a distribution shift in the reference annotation: validation records have
at most seven stages, test records reach the low twenties, and the training split holds almost
no long records above the eighth cap. Stratifying by true stage count resolves the
contradiction --- the narrow cap wins at or below it, the wide cap far above it --- and on
the long training records the ARI moves from \slotPKLongEight{} to \slotPKLongSixteen{} as
the cap widens, with a stratified bound of \slotPKStratSixteen{}. One test record has two
true stages: the information criterion picks a count in the twenties and its ARI collapses,
while silhouette recovers the correct count.""",
r"""The cause is a distribution shift in the reference annotation: validation records hold at most
seven stages, test records reach the low twenties, and the training split holds almost no long
records above the eighth cap. Stratifying by true stage count resolves the contradiction ---
the narrow cap wins at or below it, the wide cap far above it --- and on the long records the
ARI moves from \slotPKLongEight{} to \slotPKLongSixteen{} as the cap widens. One test record
holds two true stages: the information criterion picks a count in the twenties and collapses,
while silhouette recovers the correct count."""))

cuts.append((
r"""Three failures are structural and are reported as such. The reliability weight
does not transfer across environments: the gap between \slotPEnvOneAUC{} and
\slotPEnvTwoAUC{} means a target environment needs on the order of
\slotCtx{} to twice that many calibration frames before the calibrated route is
usable, and without them only the rank of the weight should be trusted.""",
r"""Three failures are structural. The reliability weight does not transfer across
environments: the gap between \slotPEnvOneAUC{} and \slotPEnvTwoAUC{} means a target
environment needs on the order of \slotCtx{} to twice that many calibration frames before the
calibrated route is usable, and without them only the rank of the weight should be trusted."""))

for old, new in cuts:
    if old not in t:
        print("MISS:", old[:60].replace("\n", " "))
    else:
        t = t.replace(old, new)

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("trims applied")
